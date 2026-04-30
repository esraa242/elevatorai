"""
ModelingAgent: Converts 2D cabin images into interactive 3D models
Uses Gemini for understanding + procedural generation for mesh creation
"""
import json
import base64
import numpy as np
from typing import Dict, List, Optional
from io import BytesIO
from PIL import Image
from google.adk.agents import Agent
import trimesh
import os
from google import genai
from google.genai import types

def get_client():
    """Initialize the new unified Google GenAI client"""
    return genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

class ModelingAgentConfig:
    MODEL_NAME = "gemini-1.5-pro"
    OUTPUT_FORMATS = ["glb", "gltf", "usdz", "obj"]
    DEFAULT_DIMENSIONS = {"width": 1.4, "depth": 1.6, "height": 2.5}

    MATERIAL_PRESETS = {
        "brushed_steel": {
            "baseColorFactor": [0.72, 0.73, 0.75, 1.0],
            "metallicFactor": 1.0,
            "roughnessFactor": 0.3,
        },
        "polished_gold": {
            "baseColorFactor": [0.83, 0.68, 0.21, 1.0],
            "metallicFactor": 1.0,
            "roughnessFactor": 0.15,
        },
        "matte_black": {
            "baseColorFactor": [0.05, 0.05, 0.05, 1.0],
            "metallicFactor": 0.1,
            "roughnessFactor": 0.8,
        },
        "clear_glass": {
            "baseColorFactor": [0.95, 0.95, 0.97, 0.3],
            "metallicFactor": 0.0,
            "roughnessFactor": 0.0,
            "alphaMode": "BLEND",
        },
        "white_marble": {
            "baseColorFactor": [0.95, 0.95, 0.93, 1.0],
            "metallicFactor": 0.0,
            "roughnessFactor": 0.1,
        },
        "oak_wood": {
            "baseColorFactor": [0.65, 0.5, 0.35, 1.0],
            "metallicFactor": 0.0,
            "roughnessFactor": 0.6,
        },
        "mirror": {
            "baseColorFactor": [0.98, 0.98, 0.98, 1.0],
            "metallicFactor": 1.0,
            "roughnessFactor": 0.0,
        }
    }


async def analyze_cabin_image(image_bytes: bytes) -> Dict:
    """Analyze cabin design image to extract 3D construction parameters"""
    client = get_client()

    prompt = """Analyze this elevator cabin design image and extract 3D modeling parameters.

    Return JSON with: cabin_type, shape, dimensions, wall_configuration, ceiling, floor, 
    handrails, control_panel, materials, complexity."""

    response = await client.aio.models.generate_content(
        model=ModelingAgentConfig.MODEL_NAME,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
            prompt
        ],
        config=types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json"
        )
    )
    return json.loads(response.text)


async def generate_3d_model(
    cabin_params: Dict,
    style_params: Optional[Dict] = None,
    output_format: str = "glb"
) -> Dict:
    """Generate 3D model from cabin parameters using procedural mesh generation"""
    dims = cabin_params.get("dimensions", ModelingAgentConfig.DEFAULT_DIMENSIONS)
    w, d, h = dims["width"], dims["depth"], dims["height"]

    scene = trimesh.Scene()

    # Floor
    floor = trimesh.creation.box(extents=[w, 0.05, d])
    floor.apply_translation([0, 0.025, 0])
    scene.add_geometry(floor, node_name="floor")

    # Ceiling
    ceiling = trimesh.creation.box(extents=[w, 0.03, d])
    ceiling.apply_translation([0, h - 0.015, 0])
    scene.add_geometry(ceiling, node_name="ceiling")

    # Walls
    w2, d2 = w / 2, d / 2

    back = trimesh.creation.box(extents=[w, h, 0.03])
    back.apply_translation([0, h / 2, -d2 + 0.015])
    scene.add_geometry(back, node_name="back_wall")

    left = trimesh.creation.box(extents=[0.03, h, d])
    left.apply_translation([-w2 + 0.015, h / 2, 0])
    scene.add_geometry(left, node_name="left_wall")

    right = trimesh.creation.box(extents=[0.03, h, d])
    right.apply_translation([w2 - 0.015, h / 2, 0])
    scene.add_geometry(right, node_name="right_wall")

    # Front wall with door gap
    door_w = w * 0.35
    fl = trimesh.creation.box(extents=[(w - door_w) / 2, h, 0.03])
    fl.apply_translation([-(w + door_w) / 4, h / 2, d2 - 0.015])
    scene.add_geometry(fl, node_name="front_left")

    fr = trimesh.creation.box(extents=[(w - door_w) / 2, h, 0.03])
    fr.apply_translation([(w + door_w) / 4, h / 2, d2 - 0.015])
    scene.add_geometry(fr, node_name="front_right")

    # Handrail
    rail = trimesh.creation.cylinder(radius=0.015, height=w * 0.85)
    rail.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
    rail.apply_translation([0, h * 0.42, -d2 + 0.12])
    scene.add_geometry(rail, node_name="handrail")

    # Control panel
    cp = trimesh.creation.box(extents=[0.12, 0.35, 0.04])
    cp.apply_translation([w2 - 0.08, h * 0.55, d2 - 0.04])
    scene.add_geometry(cp, node_name="control_panel")

    # Export
    output_dir = "./static/models/"
    os.makedirs(output_dir, exist_ok=True)
    base_name = f"cabin_{int(__import__('time').time())}"

    glb_path = f"{output_dir}{base_name}.glb"
    scene.export(glb_path)

    return {
        "model_files": {"glb": glb_path},
        "preview_images": [f"{output_dir}{base_name}_preview.png"],
        "specifications": {
            "poly_count": sum(len(g.faces) for g in scene.geometry.values()),
            "vertex_count": sum(len(g.vertices) for g in scene.geometry.values()),
            "dimensions": dims,
            "format": output_format
        }
    }


async def customize_materials(model_path: str, material_overrides: Dict[str, str]) -> str:
    """Customize materials on existing 3D model"""
    scene = trimesh.load(model_path)

    for node_name, material_name in material_overrides.items():
        if material_name in ModelingAgentConfig.MATERIAL_PRESETS:
            preset = ModelingAgentConfig.MATERIAL_PRESETS[material_name]
            for name, geom in scene.geometry.items():
                if node_name in name:
                    geom.visual.material = trimesh.visual.material.PBRMaterial(
                        name=material_name,
                        baseColorFactor=preset["baseColorFactor"],
                        metallicFactor=preset["metallicFactor"],
                        roughnessFactor=preset["roughnessFactor"]
                    )

    output_path = model_path.replace(".glb", "_customized.glb")
    scene.export(output_path)
    return output_path

# ADK Agent Definition
modeling_agent_def = Agent(
    name="modeling_engineer",
    description="Converts 2D cabin design images into interactive 3D models",
    model=ModelingAgentConfig.MODEL_NAME,
    tools=[analyze_cabin_image, generate_3d_model, customize_materials],
    instruction="You are ModelingAgent. Analyze cabin images, extract 3D params, generate GLB models with PBR materials. Optimize for web viewing."
)
