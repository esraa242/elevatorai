"""
Workflow Orchestrator: Coordinates multi-agent pipeline
VisionAgent -> MatchingAgent -> ModelingAgent -> SalesAgent
"""
import os
import asyncio
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents.vision_agent.agent import vision_agent_def, analyze_interior_image
from agents.matching_agent.agent import matching_agent_def, match_cabins
from agents.modeling_agent.agent import modeling_agent_def, generate_3d_model, analyze_cabin_image
from agents.sales_agent.agent import sales_agent_def, generate_quote, send_quote_via_whatsapp

@dataclass
class WorkflowState:
    """Shared state across the multi-agent workflow"""
    session_id: str
    customer_phone: Optional[str] = None
    customer_name: Optional[str] = None
    uploaded_image: Optional[bytes] = None
    vision_analysis: Optional[Dict] = None
    matched_cabins: Optional[List[Dict]] = None
    selected_cabin: Optional[Dict] = None
    generated_model: Optional[Dict] = None
    quote: Optional[Dict] = None
    status: str = "initialized"
    created_at: str = ""
    updated_at: str = ""

class ElevatorAIWorkflow:
    """Main workflow orchestrator for the elevator cabin design pipeline"""

    def __init__(self):
        self.active_sessions: Dict[str, WorkflowState] = {}
        # Cache for uploaded images (session_id -> image_bytes)
        self._image_cache: Dict[str, bytes] = {}

    async def run_full_pipeline(
        self,
        image_bytes: bytes,
        customer_phone: Optional[str] = None,
        customer_name: Optional[str] = None,
        budget: Optional[float] = None
    ) -> Dict:
        """
        Run complete workflow: Vision -> Matching -> Modeling -> Quote
        """
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        state = WorkflowState(
            session_id=session_id,
            customer_phone=customer_phone,
            customer_name=customer_name,
            uploaded_image=image_bytes,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat()
        )
        self.active_sessions[session_id] = state
        # Cache the uploaded image for later use by modeling agent
        self._image_cache[session_id] = image_bytes

        try:
            # Step 1: Vision Analysis
            print(f"[{session_id}] Step 1: Running Vision Analysis...")
            state.status = "analyzing"
            state.vision_analysis = await analyze_interior_image(image_bytes)
            
            # Check if vision analysis returned an error
            if "error" in state.vision_analysis and state.vision_analysis.get("confidence", 0) < 0.6:
                print(f"[{session_id}] Warning: Vision analysis had low confidence")
            
            state.updated_at = datetime.utcnow().isoformat()

            # Step 2: Cabin Matching
            print(f"[{session_id}] Step 2: Matching Cabins...")
            state.status = "matching"
            state.matched_cabins = await match_cabins(
                vision_analysis=state.vision_analysis,
                customer_budget=budget,
                top_k=3
            )
            state.updated_at = datetime.utcnow().isoformat()

            # Select top match for 3D generation
            if state.matched_cabins:
                state.selected_cabin = state.matched_cabins[0]
            else:
                raise ValueError("No cabin matches found")

            # Step 3: 3D Model Generation
            print(f"[{session_id}] Step 3: Generating 3D Model...")
            state.status = "modeling"

            # Use the original uploaded image for cabin analysis if no cabin-specific image
            # This allows the modeling agent to analyze the style from the interior photo
            cabin_image = await self._get_cabin_image(session_id, state.selected_cabin["id"])
            cabin_params = await analyze_cabin_image(cabin_image)

            # Apply style overrides from vision analysis
            style_overrides = {
                "colors": state.vision_analysis.get("color_palette", {}).get("dominant", []),
                "mood": state.vision_analysis.get("mood", {}).get("primary", "neutral")
            }

            state.generated_model = await generate_3d_model(
                cabin_params=cabin_params,
                style_params=style_overrides,
                output_format="glb"
            )
            state.updated_at = datetime.utcnow().isoformat()

            # Step 4: Quote Generation & WhatsApp Delivery (optional)
            if customer_phone:
                print(f"[{session_id}] Step 4: Generating Quote...")
                state.status = "quoting"

                customer_details = {
                    "name": customer_name or "Valued Customer",
                    "phone": customer_phone,
                    "location": "villa",
                    "tier": "premium"
                }

                state.quote = await generate_quote(
                    cabin_design=state.selected_cabin,
                    customer_details=customer_details,
                    customizations=state.selected_cabin.get("features", [])
                )

                # Try to send WhatsApp - graceful fallback if not configured
                try:
                    preview_url = state.generated_model.get("preview_images", [""])[0]
                    await send_quote_via_whatsapp(
                        phone_number=customer_phone,
                        quote=state.quote,
                        preview_image_url=preview_url
                    )
                    state.status = "completed"
                except Exception as wa_err:
                    print(f"[{session_id}] WhatsApp send failed (non-critical): {wa_err}")
                    # Quote is still generated, just not sent via WhatsApp
                    state.status = "completed_no_whatsapp"
            else:
                state.status = "pending_quote"

            state.updated_at = datetime.utcnow().isoformat()

            # Clean up image cache
            self._image_cache.pop(session_id, None)
            
            return self._build_response(state)

        except Exception as e:
            print(f"[{session_id}] Pipeline error: {str(e)}")
            state.status = f"error: {str(e)}"
            state.updated_at = datetime.utcnow().isoformat()
            # Clean up on error too
            self._image_cache.pop(session_id, None)
            return self._build_response(state, error=str(e))

    async def run_vision_only(self, image_bytes: bytes) -> Dict:
        """Run only vision analysis (for quick style detection)"""
        return await analyze_interior_image(image_bytes)

    async def run_matching_only(self, vision_analysis: Dict, budget: Optional[float] = None) -> List[Dict]:
        """Run only cabin matching (when vision analysis is cached)"""
        return await match_cabins(vision_analysis=vision_analysis, customer_budget=budget, top_k=5)

    async def run_modeling_only(self, cabin_id: str, style_overrides: Optional[Dict] = None, image_bytes: Optional[bytes] = None) -> Dict:
        """Run only 3D generation (when cabin is already selected)"""
        cabin_image = image_bytes or await self._get_cabin_image(None, cabin_id)
        cabin_params = await analyze_cabin_image(cabin_image)
        return await generate_3d_model(cabin_params=cabin_params, style_params=style_overrides)

    async def send_quote_only(self, cabin: Dict, customer_phone: str, customer_name: Optional[str] = None) -> Dict:
        """Generate and send quote for already-selected cabin"""
        customer_details = {
            "name": customer_name or "Valued Customer",
            "phone": customer_phone,
            "location": "villa",
            "tier": "premium"
        }

        quote = await generate_quote(
            cabin_design=cabin,
            customer_details=customer_details,
            customizations=cabin.get("features", [])
        )

        # Graceful WhatsApp fallback
        try:
            await send_quote_via_whatsapp(
                phone_number=customer_phone,
                quote=quote
            )
            return {"status": "sent", "quote": quote}
        except Exception as e:
            print(f"WhatsApp send failed (non-critical): {e}")
            return {"status": "quote_generated_whatsapp_skipped", "quote": quote, "note": "Quote generated but WhatsApp not configured"}

    async def _get_cabin_image(self, session_id: Optional[str], cabin_id: str) -> bytes:
        """Fetch cabin reference image from storage or use cached uploaded image"""
        # First try: use the cached uploaded image from this session
        if session_id and session_id in self._image_cache:
            print(f"Using cached uploaded image for cabin analysis (session: {session_id})")
            return self._image_cache[session_id]
        
        # Second try: check if there's a static cabin image
        static_paths = [
            f"static/cabins/{cabin_id}.jpg",
            f"static/cabins/{cabin_id}.png",
            f"static/thumbnails/{cabin_id}.jpg",
            f"static/thumbnails/{cabin_id}.png",
        ]
        for path in static_paths:
            if os.path.exists(path):
                print(f"Found static cabin image: {path}")
                with open(path, 'rb') as f:
                    return f.read()
        
        # Third try: use any available cabin thumbnail from the matching data
        # Return empty bytes - the modeling agent will use defaults
        print("No cabin image found, using empty data (modeling agent will use defaults)")
        return b""

    def _build_response(self, state: WorkflowState, error: Optional[str] = None) -> Dict:
        """Build standardized workflow response"""
        response = {
            "session_id": state.session_id,
            "status": state.status,
            "customer": {
                "name": state.customer_name,
                "phone": state.customer_phone
            },
            "vision_analysis": state.vision_analysis,
            "matched_cabins": state.matched_cabins,
            "selected_cabin": state.selected_cabin,
            "generated_model": state.generated_model,
            "quote": state.quote,
            "timestamps": {
                "created": state.created_at,
                "updated": state.updated_at
            }
        }

        if error:
            response["error"] = error

        return response

    def get_session_status(self, session_id: str) -> Optional[Dict]:
        """Get current status of a workflow session"""
        state = self.active_sessions.get(session_id)
        if not state:
            return None
        return self._build_response(state)


# ==================== FastAPI Application ====================

app = FastAPI(title="ElevatorAI ADK", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global workflow instance
workflow = ElevatorAIWorkflow()

class QuoteRequest(BaseModel):
    cabin_id: str
    customer_phone: str
    customer_name: Optional[str] = None
    customizations: Optional[List[str]] = []

class WorkflowRequest(BaseModel):
    customer_phone: Optional[str] = None
    customer_name: Optional[str] = None
    budget: Optional[float] = None


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "gemini_configured": bool(os.getenv("GEMINI_API_KEY")),
        "whatsapp_configured": bool(os.getenv("WHATSAPP_API_TOKEN") and os.getenv("WHATSAPP_PHONE_NUMBER_ID"))
    }

@app.post("/api/v2/analyze")
async def analyze_image(file: UploadFile = File(...)):
    """Step 1: Analyze interior image"""
    contents = await file.read()
    result = await workflow.run_vision_only(contents)
    return result

@app.post("/api/v2/match")
async def match_cabins_endpoint(vision_data: Dict, budget: Optional[float] = None):
    """Step 2: Match cabins based on vision analysis"""
    result = await workflow.run_matching_only(vision_data, budget)
    return {"matches": result}

@app.post("/api/v2/generate-3d")
async def generate_3d_endpoint(
    cabin_id: str,
    style_overrides: Optional[Dict] = None,
    file: Optional[UploadFile] = File(None)
):
    """Step 3: Generate 3D model (optionally with reference image)"""
    image_bytes = None
    if file:
        image_bytes = await file.read()
    result = await workflow.run_modeling_only(cabin_id, style_overrides, image_bytes)
    return result

@app.post("/api/v2/get-quote")
async def get_quote_endpoint(request: QuoteRequest):
    """Step 4: Generate and send quote via WhatsApp"""
    # Look up full cabin details from matching agent
    from agents.matching_agent.agent import get_cabin_details
    cabin = await get_cabin_details(request.cabin_id)
    
    if "error" in cabin:
        # Fallback: use minimal cabin data
        cabin = {
            "id": request.cabin_id,
            "name": request.cabin_id,
            "materials": [],
            "dimensions": {"width": 1.4, "depth": 1.6, "height": 2.5},
            "features": request.customizations or []
        }
    
    result = await workflow.send_quote_only(
        cabin=cabin,
        customer_phone=request.customer_phone,
        customer_name=request.customer_name
    )
    return result

@app.post("/api/v2/full-pipeline")
async def full_pipeline(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    customer_phone: Optional[str] = None,
    customer_name: Optional[str] = None,
    budget: Optional[float] = None
):
    """Run complete pipeline: Upload -> Analyze -> Match -> 3D -> Quote"""
    contents = await file.read()

    result = await workflow.run_full_pipeline(
        image_bytes=contents,
        customer_phone=customer_phone,
        customer_name=customer_name,
        budget=budget
    )

    return result

@app.get("/api/v2/session/{session_id}")
async def get_session(session_id: str):
    """Get session status"""
    status = workflow.get_session_status(session_id)
    if not status:
        raise HTTPException(status_code=404, detail="Session not found")
    return status

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(payload: Dict):
    """Handle WhatsApp Business API webhooks"""
    from agents.sales_agent.agent import handle_whatsapp_webhook
    return await handle_whatsapp_webhook(payload)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
