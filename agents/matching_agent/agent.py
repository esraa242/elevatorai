"""
MatchingAgent: Uses Gemini Embeddings 2.0 to match interior styles with cabin designs
Implements semantic image-to-image and text-to-image search
"""
import json
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from google.adk.agents import Agent
import os
from google import genai
from google.genai import types

def get_client():
    """Initialize the new unified Google GenAI client"""
    return genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

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
        client = get_client()
        result = await client.aio.models.embed_content(
            model=MatchingAgentConfig.EMBEDDING_MODEL,
            contents=content,
            config=types.EmbedContentConfig(task_type=task_type)
        )
        return result.embeddings[0].values

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
        limit: int = 5
    ) -> List[Tuple[str, float]]:
        """Search Redis for similar cabin designs using cosine similarity"""
        # Note: In a production environment, use RedisVL or RediSearch Vector Similarity
        # This is a simplified implementation for demonstration
        results = []
        keys = await self.redis.keys("cabin:*")
        
        for key in keys:
            cabin_id = key.decode().split(":")[1]
            data = await self.redis.hgetall(key)
            if not data: continue
            
            stored_embedding = json.loads(data[b"image_embedding"].decode())
            
            # Cosine similarity
            sim = np.dot(query_embedding, stored_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(stored_embedding)
            )
            results.append((cabin_id, float(sim)))
            
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    async def get_mock_cabins(self) -> List[CabinDesign]:
        """Generate mock cabins if database is empty"""
        cabins = [
            CabinDesign(
                id="classic-001",
                name="Imperial Gold",
                style_tags=["Luxury Classic", "Art Deco"],
                materials=["Polished Gold", "White Marble", "Mirror"],
                color_palette=["#FFD700", "#FFFFFF", "#333333"],
                price_usd=45000.0,
                dimensions={"width": 1.4, "depth": 1.6, "height": 2.5},
                capacity=8,
                image_embedding=[],
                text_embedding=[],
                thumbnail_url="static/thumbnails/imperial_gold.jpg",
                features=["Handcrafted Gold Leaf", "Marble Flooring", "Smart Lighting"]
            ),
            CabinDesign(
                id="modern-001",
                name="Skyline Minimalist",
                style_tags=["Modern Minimalist", "High-Tech"],
                materials=["Brushed Steel", "Clear Glass", "Concrete"],
                color_palette=["#727375", "#F5F5F7", "#000000"],
                price_usd=32000.0,
                dimensions={"width": 1.2, "depth": 1.4, "height": 2.4},
                capacity=6,
                image_embedding=[],
                text_embedding=[],
                thumbnail_url="static/thumbnails/skyline_min.jpg",
                features=["Panoramic Glass", "Integrated LED", "Touch Control"]
            ),
            CabinDesign(
                id="nature-001",
                name="Biophilic Sanctuary",
                style_tags=["Biophilic", "Scandinavian"],
                materials=["Oak Wood", "Linen", "Matte Black"],
                color_palette=["#655035", "#F5F5DC", "#2D5A27"],
                price_usd=38000.0,
                dimensions={"width": 1.5, "depth": 1.7, "height": 2.5},
                capacity=10,
                image_embedding=[],
                text_embedding=[],
                thumbnail_url="static/thumbnails/biophilic.jpg",
                features=["Living Wall Option", "Natural Wood Finishes", "Soft Acoustic Panels"]
            )
        ]
        
        # Populate mock embeddings
        for cabin in cabins:
            cabin.image_embedding = await self.generate_image_embedding(" ".join(cabin.style_tags + cabin.materials))
            cabin.text_embedding = await self.generate_image_embedding(cabin.name)

        return cabins


async def match_cabins(
    vision_analysis: Dict,
    customer_budget: Optional[float] = None,
    top_k: int = 3
) -> List[Dict]:
    """
    Match interior analysis with cabin designs using semantic search
    """
    store = EmbeddingStore()
    
    # 1. Generate query embedding from vision analysis
    style_desc = f"{vision_analysis.get('primary_style', {}).get('name', '')} {vision_analysis.get('mood', {}).get('atmosphere', '')}"
    query_embedding = await store.generate_image_embedding(style_desc)
    
    # 2. Get candidates (mock or from DB)
    candidates = await store.get_mock_cabins()
    
    # 3. Calculate scores
    scored_cabins = []
    for cabin in candidates:
        # Semantic score
        sim = np.dot(query_embedding, cabin.image_embedding) / (
            np.linalg.norm(query_embedding) * np.linalg.norm(cabin.image_embedding)
        )
        
        # Budget penalty
        budget_score = 1.0
        if customer_budget and cabin.price_usd > customer_budget:
            budget_score = max(0, 1.0 - (cabin.price_usd - customer_budget) / customer_budget)
            
        final_score = (sim * 0.8) + (budget_score * 0.2)
        cabin.match_score = round(final_score * 100, 1)
        scored_cabins.append(cabin)
        
    scored_cabins.sort(key=lambda x: x.match_score, reverse=True)
    
    return [
        {
            "id": c.id,
            "name": c.name,
            "style_tags": c.style_tags,
            "materials": c.materials,
            "price_usd": c.price_usd,
            "match_score": c.match_score,
            "thumbnail_url": c.thumbnail_url,
            "features": c.features,
            "dimensions": c.dimensions,
            "capacity": c.capacity
        } for c in scored_cabins[:top_k]
    ]


async def get_cabin_details(cabin_id: str) -> Dict:
    """Get full details for a specific cabin design"""
    store = EmbeddingStore()
    cabins = await store.get_mock_cabins()
    for c in cabins:
        if c.id == cabin_id:
            return {
                "id": c.id,
                "name": c.name,
                "style_tags": c.style_tags,
                "materials": c.materials,
                "price_usd": c.price_usd,
                "dimensions": c.dimensions,
                "capacity": c.capacity,
                "thumbnail_url": c.thumbnail_url,
                "features": c.features
            }
    return {"error": "Cabin not found"}

# ADK Agent Definition
matching_agent_def = Agent(
    name="cabin_matcher",
    description="Matches interior design styles with elevator cabin designs using Gemini Embeddings 2.0",
    model="gemini-1.5-pro",
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
