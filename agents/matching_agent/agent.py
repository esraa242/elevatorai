"""
MatchingAgent: Uses Gemini Embeddings 2.0 to match interior styles with cabin designs
Implements semantic image-to-image and text-to-image search
"""
import json
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from google.adk.agents import Agent
from google.adk.tools import tool
import os
import google.generativeai as genai

if "GEMINI_API_KEY" in os.environ:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
import redis.asyncio as redis
import asyncpg

@dataclass
class CabinDesign:
    id: str
    name: str
    style_tags: List[str]
    materials: List[str]
    color_palette: List[str]
    price_usd: float
    dimensions: Dict[str, float]
    capacity: int
    image_embedding: List[float]
    text_embedding: List[float]
    thumbnail_url: str
    features: List[str]
    match_score: float = 0.0

class MatchingAgentConfig:
    EMBEDDING_MODEL = "text-embedding-004"  # Gemini Embeddings 2.0
    EMBEDDING_DIMENSION = 768
    REDIS_INDEX_NAME = "cabin_embeddings"
    TOP_K_DEFAULT = 5

    # Matching weights
    STYLE_WEIGHT = 0.35
    COLOR_WEIGHT = 0.25
    MATERIAL_WEIGHT = 0.20
    MOOD_WEIGHT = 0.15
    PRICE_WEIGHT = 0.05

class EmbeddingStore:
    """Redis-based vector store for cabin embeddings using Gemini 2.0"""

    def __init__(self, redis_url: str = None):
        if redis_url is None:
            redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        self.redis = redis.from_url(redis_url)

    async def generate_embedding(self, content: str, task_type: str = "RETRIEVAL_DOCUMENT") -> List[float]:
        """Generate Gemini 2.0 embedding for text or image description"""
        result = genai.embed_content(
            model=f"models/{MatchingAgentConfig.EMBEDDING_MODEL}",
            content=content,
            task_type=task_type
        )
        return result['embedding']

    async def generate_image_embedding(self, image_description: str) -> List[float]:
        """Generate embedding from image description (Gemini Vision output)"""
        return await self.generate_embedding(
            image_description,
            task_type="RETRIEVAL_DOCUMENT"
        )

    async def index_cabin(self, cabin: CabinDesign):
        """Store cabin with its embeddings in Redis"""
        # Store metadata
        await self.redis.hset(
            f"cabin:{cabin.id}",
            mapping={
                "name": cabin.name,
                "style_tags": json.dumps(cabin.style_tags),
                "materials": json.dumps(cabin.materials),
                "color_palette": json.dumps(cabin.color_palette),
                "price_usd": str(cabin.price_usd),
                "dimensions": json.dumps(cabin.dimensions),
                "capacity": str(cabin.capacity),
                "thumbnail_url": cabin.thumbnail_url,
                "features": json.dumps(cabin.features),
                "image_embedding": json.dumps(cabin.image_embedding),
                "text_embedding": json.dumps(cabin.text_embedding)
            }
        )

        # Add to search index
        await self.redis.execute_command(
            "FT.ADD", MatchingAgentConfig.REDIS_INDEX_NAME, cabin.id,
            "1.0", "FIELDS",
            "embedding", json.dumps(cabin.image_embedding)
        )

    async def search_similar(
        self, 
        query_embedding: List[float], 
        top_k: int = 5,
        filters: Optional[Dict] = None
    ) -> List[CabinDesign]:
        """Search for similar cabins using vector similarity"""
        # Use Redis Vector Similarity Search
        results = await self.redis.execute_command(
            "FT.SEARCH", MatchingAgentConfig.REDIS_INDEX_NAME,
            f"*=>[KNN {top_k} @embedding $vec AS score]",
            "PARAMS", "2", "vec", json.dumps(query_embedding),
            "SORTBY", "score", "ASC",
            "RETURN", "1", "score"
        )

        cabins = []
        for i in range(1, len(results), 2):
            cabin_id = results[i].decode()
            score = float(results[i+1][1])

            cabin_data = await self.redis.hgetall(f"cabin:{cabin_id}")
            cabin = CabinDesign(
                id=cabin_id,
                name=cabin_data[b"name"].decode(),
                style_tags=json.loads(cabin_data[b"style_tags"]),
                materials=json.loads(cabin_data[b"materials"]),
                color_palette=json.loads(cabin_data[b"color_palette"]),
                price_usd=float(cabin_data[b"price_usd"]),
                dimensions=json.loads(cabin_data[b"dimensions"]),
                capacity=int(cabin_data[b"capacity"]),
                image_embedding=json.loads(cabin_data[b"image_embedding"]),
                text_embedding=json.loads(cabin_data[b"text_embedding"]),
                thumbnail_url=cabin_data[b"thumbnail_url"].decode(),
                features=json.loads(cabin_data[b"features"]),
                match_score=score
            )
            cabins.append(cabin)

        return cabins

@tool
async def match_cabins(
    vision_analysis: Dict,
    customer_budget: Optional[float] = None,
    top_k: int = 5
) -> List[Dict]:
    """
    Match interior style with cabin designs using Gemini Embeddings 2.0

    Args:
        vision_analysis: Output from VisionAgent
        customer_budget: Optional budget constraint
        top_k: Number of matches to return

    Returns:
        Ranked list of matching cabin designs with scores
    """
    store = EmbeddingStore()

    # Build rich query description from vision analysis
    query_parts = [
        f"Interior design style: {vision_analysis['primary_style']['name']}",
        f"Colors: {', '.join(vision_analysis['color_palette']['dominant'])}",
        f"Mood: {vision_analysis['mood']['primary']}",
        f"Materials: {', '.join([m['name'] for m in vision_analysis['materials']])}",
        f"Atmosphere: {vision_analysis['mood']['atmosphere']}"
    ]
    query_text = ". ".join(query_parts)

    # Generate query embedding using Gemini 2.0
    query_embedding = await store.generate_embedding(query_text, task_type="RETRIEVAL_QUERY")

    # Search vector store
    candidates = await store.search_similar(query_embedding, top_k=top_k*2)

    # Multi-factor re-ranking
    ranked = []
    for cabin in candidates:
        score = await _calculate_match_score(cabin, vision_analysis, customer_budget)
        if score > 0.5:  # Minimum relevance threshold
            cabin.match_score = score
            ranked.append(cabin)

    # Sort by final score
    ranked.sort(key=lambda x: x.match_score, reverse=True)

    # Convert to serializable format
    return [_cabin_to_dict(c) for c in ranked[:top_k]]

async def _calculate_match_score(
    cabin: CabinDesign, 
    vision: Dict,
    budget: Optional[float]
) -> float:
    """Calculate weighted multi-factor match score"""

    # Style match
    style_score = _jaccard_similarity(
        set(cabin.style_tags),
        set([vision["primary_style"]["name"]] + [s["name"] for s in vision.get("secondary_styles", [])])
    )

    # Color similarity (using hex color distance)
    color_score = _color_palette_similarity(
        cabin.color_palette,
        vision["color_palette"]["dominant"] + vision["color_palette"].get("accent", [])
    )

    # Material overlap
    cabin_materials = set(m.lower() for m in cabin.materials)
    vision_materials = set(m["name"].lower() for m in vision["materials"])
    material_score = _jaccard_similarity(cabin_materials, vision_materials)

    # Mood alignment (using text embedding similarity)
    mood_score = await _mood_similarity(cabin, vision["mood"]["atmosphere"])

    # Budget fit (1.0 if within budget, decreasing if over)
    price_score = 1.0
    if budget and cabin.price_usd > budget:
        price_score = max(0, 1.0 - (cabin.price_usd - budget) / budget)

    # Weighted combination
    final_score = (
        MatchingAgentConfig.STYLE_WEIGHT * style_score +
        MatchingAgentConfig.COLOR_WEIGHT * color_score +
        MatchingAgentConfig.MATERIAL_WEIGHT * material_score +
        MatchingAgentConfig.MOOD_WEIGHT * mood_score +
        MatchingAgentConfig.PRICE_WEIGHT * price_score
    )

    return round(final_score, 3)

def _jaccard_similarity(set_a: set, set_b: set) -> float:
    """Calculate Jaccard similarity between two sets"""
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0

def _color_palette_similarity(palette_a: List[str], palette_b: List[str]) -> float:
    """Calculate similarity between two color palettes using LAB color space"""
    from skimage.color import rgb2lab, deltaE_ciede2000
    import numpy as np

    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip('#')
        return np.array([int(hex_color[i:i+2], 16) for i in (0, 2, 4)])

    try:
        lab_a = np.array([rgb2lab(hex_to_rgb(c).reshape(1,1,3)/255.0).flatten() for c in palette_a])
        lab_b = np.array([rgb2lab(hex_to_rgb(c).reshape(1,1,3)/255.0).flatten() for c in palette_b])

        # Calculate minimum distance for each color in A to any color in B
        distances = []
        for color_a in lab_a:
            min_dist = min(deltaE_ciede2000(color_a, color_b) for color_b in lab_b)
            distances.append(min_dist)

        # Convert to similarity (lower distance = higher similarity)
        avg_dist = np.mean(distances)
        similarity = max(0, 1 - avg_dist / 100)  # Normalize
        return similarity
    except:
        return 0.5

async def _mood_similarity(cabin: CabinDesign, mood_text: str) -> float:
    """Calculate semantic similarity between cabin description and mood text"""
    store = EmbeddingStore()
    cabin_desc = f"{cabin.name} style: {', '.join(cabin.style_tags)}. Materials: {', '.join(cabin.materials)}"

    cabin_emb = await store.generate_embedding(cabin_desc)
    mood_emb = await store.generate_embedding(mood_text)

    # Cosine similarity
    dot = np.dot(cabin_emb, mood_emb)
    norm = np.linalg.norm(cabin_emb) * np.linalg.norm(mood_emb)
    return float(dot / norm) if norm > 0 else 0.0

def _cabin_to_dict(cabin: CabinDesign) -> Dict:
    return {
        "id": cabin.id,
        "name": cabin.name,
        "style_tags": cabin.style_tags,
        "materials": cabin.materials,
        "color_palette": cabin.color_palette,
        "price_usd": cabin.price_usd,
        "dimensions": cabin.dimensions,
        "capacity": cabin.capacity,
        "thumbnail_url": cabin.thumbnail_url,
        "features": cabin.features,
        "match_score": cabin.match_score,
        "match_breakdown": {
            "style": MatchingAgentConfig.STYLE_WEIGHT,
            "color": MatchingAgentConfig.COLOR_WEIGHT,
            "material": MatchingAgentConfig.MATERIAL_WEIGHT,
            "mood": MatchingAgentConfig.MOOD_WEIGHT,
            "price": MatchingAgentConfig.PRICE_WEIGHT
        }
    }

@tool
async def get_cabin_details(cabin_id: str) -> Dict:
    """Get full details for a specific cabin design"""
    store = EmbeddingStore()
    cabin_data = await store.redis.hgetall(f"cabin:{cabin_id}")
    if not cabin_data:
        return {"error": "Cabin not found"}

    return {
        "id": cabin_id,
        "name": cabin_data[b"name"].decode(),
        "style_tags": json.loads(cabin_data[b"style_tags"]),
        "materials": json.loads(cabin_data[b"materials"]),
        "color_palette": json.loads(cabin_data[b"color_palette"]),
        "price_usd": float(cabin_data[b"price_usd"]),
        "dimensions": json.loads(cabin_data[b"dimensions"]),
        "capacity": int(cabin_data[b"capacity"]),
        "thumbnail_url": cabin_data[b"thumbnail_url"].decode(),
        "features": json.loads(cabin_data[b"features"]),
        "full_description": cabin_data.get(b"full_description", b"").decode()
    }

# ADK Agent Definition
matching_agent_def = Agent(
    name="cabin_matcher",
    description="Matches interior design styles with elevator cabin designs using Gemini Embeddings 2.0",
    model="gemini-1.5-pro-002",
    tools=[match_cabins, get_cabin_details],
    instruction="""You are MatchingAgent, an expert design matcher.

Your role is to find the best elevator cabin designs that complement a customer's villa interior.

You use Gemini Embeddings 2.0 for semantic understanding of:
- Design styles
- Color palettes  
- Material preferences
- Mood and atmosphere

Always explain WHY a cabin matches the interior style.
Provide match scores with breakdowns.
Respect budget constraints if provided."""
)
