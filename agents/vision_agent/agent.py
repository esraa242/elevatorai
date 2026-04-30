"""
VisionAgent: Analyzes villa interior images using Gemini Pro Vision
Detects design style, color palette, materials, and mood
"""
import base64
import json
from io import BytesIO
from typing import Dict, List, Optional
from PIL import Image
import os
import google.generativeai as genai

if "GEMINI_API_KEY" in os.environ:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])

from google.adk.agents import Agent

class VisionAgentConfig:
    MODEL_NAME = "gemini-1.5-pro-vision-002"
    TEMPERATURE = 0.2
    MAX_OUTPUT_TOKENS = 2048

    STYLE_TAXONOMY = [
        "Modern Minimalist", "Luxury Classic", "Industrial Loft", "Scandinavian",
        "Art Deco", "Contemporary", "Traditional", "Mid-Century Modern",
        "Biophilic", "High-Tech", "Rustic", "Japanese Zen",
        "Mediterranean", "Bohemian", "Coastal", "Transitional"
    ]

    MATERIAL_TAXONOMY = [
        "Stainless Steel", "Brushed Gold", "Chrome", "Matte Black", "Glass",
        "Mirror", "Marble", "Granite", "White Oak", "Walnut", "Teak",
        "Leather", "Fabric", "Concrete", "Brass", "Copper", "Bronze",
        "Terrazzo", "Onyx", "Linen", "Velvet", "Suede"
    ]


async def analyze_interior_image(image_bytes: bytes, image_format: str = "jpeg") -> Dict:
    """
    Analyze villa interior image using Gemini Pro Vision

    Args:
        image_bytes: Raw image bytes
        image_format: Image format (jpeg, png, webp)

    Returns:
        Comprehensive style analysis with colors, materials, mood
    """
    try:
        # Initialize Gemini Pro Vision
        model = genai.GenerativeModel(VisionAgentConfig.MODEL_NAME)

        # Create image part
        image_part = {"mime_type": f"image/{image_format}", "data": image_bytes}

        # Structured prompt for consistent JSON output
        prompt = f"""You are an expert interior design analyst specializing in luxury residential spaces.

Analyze this villa interior image and provide a structured assessment for elevator cabin design matching.

STYLES (select from: {', '.join(VisionAgentConfig.STYLE_TAXONOMY)}):
- Identify the top 3 design styles with confidence scores (0-100)
- Note any hybrid or transitional elements

MATERIALS (select from: {', '.join(VisionAgentConfig.MATERIAL_TAXONOMY)}):
- List dominant materials visible in the space
- Note finishes (matte, glossy, brushed, polished)

COLOR PALETTE:
- Extract 5 dominant hex colors
- Identify accent colors vs neutral base

MOOD & ATMOSPHERE:
- Describe the overall feeling (warm, cool, energetic, calm, luxurious, etc.)
- Lighting quality assessment

SPATIAL CHARACTERISTICS:
- Ceiling height impression
- Open plan vs compartmentalized
- Natural light availability

Return ONLY a valid JSON object with this exact structure:
{{
    "primary_style": {{
        "name": "StyleName",
        "confidence": 95,
        "description": "Brief description of style characteristics"
    }},
    "secondary_styles": [
        {{"name": "StyleName2", "confidence": 78, "description": "..."}}
    ],
    "color_palette": {{
        "dominant": ["#HEX1", "#HEX2", "#HEX3"],
        "accent": ["#HEX4", "#HEX5"],
        "mood_temperature": "warm|cool|neutral"
    }},
    "materials": [
        {{"name": "MaterialName", "finish": "brushed", "prominence": "high|medium|low"}}
    ],
    "mood": {{
        "primary": "luxurious",
        "lighting": "natural|artificial|mixed",
        "atmosphere": "Detailed atmosphere description"
    }},
    "spatial_analysis": {{
        "ceiling_height": "high|standard|low",
        "openness": "open|semi-open|compartmentalized",
        "natural_light": "abundant|moderate|limited"
    }},
    "confidence": 0.94,
    "recommendations": [
        "Specific recommendation for elevator cabin design"
    ]
}}"""

        # Generate analysis
        response = model.generate_content(
            [image_part, prompt],
            generation_config={
                "temperature": VisionAgentConfig.TEMPERATURE,
                "max_output_tokens": VisionAgentConfig.MAX_OUTPUT_TOKENS,
                "response_mime_type": "application/json"
            }
        )

        # Parse JSON response
        analysis = json.loads(response.text)

        # Enhance with computer vision metrics
        analysis["_metadata"] = {
            "model": VisionAgentConfig.MODEL_NAME,
            "image_size": len(image_bytes),
            "analysis_timestamp": __import__('datetime').datetime.utcnow().isoformat()
        }

        return analysis

    except Exception as e:
        return {
            "error": str(e),
            "primary_style": {"name": "Modern Minimalist", "confidence": 70, "description": "Fallback analysis"},
            "color_palette": {"dominant": ["#F5F5F5", "#333333"], "accent": ["#C0C0C0"], "mood_temperature": "neutral"},
            "materials": [{"name": "Stainless Steel", "finish": "brushed", "prominence": "high"}],
            "confidence": 0.5
        }


async def extract_color_palette(image_bytes: bytes, n_colors: int = 5) -> List[str]:
    """Extract dominant colors using Gemini + PIL validation"""
    from sklearn.cluster import KMeans
    import numpy as np

    img = Image.open(BytesIO(image_bytes))
    img = img.convert('RGB')
    img.thumbnail((200, 200))

    pixels = np.array(img).reshape(-1, 3)
    kmeans = KMeans(n_clusters=n_colors, random_state=42, n_init=10)
    kmeans.fit(pixels)
    colors = kmeans.cluster_centers_.astype(int)

    return [f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}" for c in colors]


async def detect_room_type(image_bytes: bytes) -> str:
    """Detect which room type (living, bedroom, kitchen, etc.) for context"""
    model = genai.GenerativeModel(VisionAgentConfig.MODEL_NAME)
    image_part = {"mime_type": "image/jpeg", "data": image_bytes}

    prompt = "What type of room is this? Return ONLY one word: living_room, bedroom, kitchen, bathroom, hallway, dining_room, foyer, or other."

    response = model.generate_content([image_part, prompt])
    return response.text.strip().lower()

# ADK Agent Definition
vision_agent_def = Agent(
    name="vision_analyst",
    description="Analyzes interior design images to extract style, colors, materials, and spatial characteristics",
    model=VisionAgentConfig.MODEL_NAME,
    tools=[analyze_interior_image, extract_color_palette, detect_room_type],
    instruction="""You are VisionAgent, an expert interior design analyst.

Your role is to analyze uploaded villa interior photos and extract:
1. Design styles (with confidence scores)
2. Color palettes (dominant + accent)
3. Materials and finishes
4. Mood and atmosphere
5. Spatial characteristics

Always return structured JSON data. Be precise with confidence scores.
If image quality is poor, note it in your analysis."""
)
