import asyncio
import os
import io
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

from agents.vision_agent.agent import analyze_interior_image
from agents.modeling_agent.agent import analyze_cabin_image, generate_3d_model
from agents.matching_agent.agent import match_cabins

async def test_all():
    print("Testing Agents...")
    
    # 1. Create a dummy test image
    print("Generating dummy image...")
    img = Image.new('RGB', (400, 400), color = 'white')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    image_bytes = img_byte_arr.getvalue()
    
    # 2. Test Vision Agent
    print("\n--- Testing Vision Agent ---")
    try:
        vision_result = await analyze_interior_image(image_bytes=image_bytes)
        print("Vision Agent Success!")
        print(f"Primary Style: {vision_result.get('primary_style', {}).get('name')}")
    except Exception as e:
        print(f"Vision Agent Failed: {e}")
        return

    # 3. Test Modeling Agent
    print("\n--- Testing Modeling Agent ---")
    try:
        modeling_result = await analyze_cabin_image(image_bytes=image_bytes)
        print("Modeling Agent Analyze Success!")
        
        # Test 3D generation
        print("Generating 3D model...")
        model_res = await generate_3d_model(cabin_params=modeling_result)
        print("Modeling Agent Generate Success!")
        print(f"Generated Model: {model_res.get('model_files', {}).get('glb')}")
    except Exception as e:
        print(f"Modeling Agent Failed: {e}")

    # 4. Test Matching Agent
    print("\n--- Testing Matching Agent ---")
    try:
        # Pass the vision analysis to the matching agent
        match_result = await match_cabins(vision_analysis=vision_result, top_k=2)
        print("Matching Agent Success!")
        print(f"Found {len(match_result)} matches.")
    except Exception as e:
        print(f"Matching Agent Failed: {e}")

if __name__ == '__main__':
    asyncio.run(test_all())
