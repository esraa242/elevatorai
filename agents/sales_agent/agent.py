"""
SalesAgent: Converts leads to WhatsApp with quote generation
"""
import json
import os
from typing import Dict, List, Optional
from datetime import datetime
from google.adk.agents import Agent
from google.adk.tools import tool
import aiohttp

class SalesAgentConfig:
    WHATSAPP_API_VERSION = "v18.0"
    WHATSAPP_API_BASE = "https://graph.facebook.com"
    TEMPLATES = {
        "welcome": "elevatorai_welcome",
        "quote_ready": "elevatorai_quote_ready",
        "consultation_booked": "elevatorai_consultation",
        "follow_up": "elevatorai_followup"
    }

class QuoteGenerator:
    BASE_PRICES = {
        "standard": 8500, "premium": 15000, "luxury": 28000, "bespoke": 45000
    }
    MATERIAL_MULTIPLIERS = {
        "stainless_steel": 1.0, "brushed_gold": 1.8, "chrome": 1.2,
        "matte_black": 1.1, "glass": 1.3, "mirror": 1.4,
        "marble": 2.0, "white_oak": 1.3, "walnut": 1.5, "teak": 1.6,
        "brass": 1.7, "copper": 1.6, "bronze": 1.5
    }
    FEATURE_PRICES = {
        "led_ambient_lighting": 1200, "touchless_controls": 800,
        "smart_mirror": 1500, "crystal_chandelier": 3500,
        "marble_flooring": 2800, "anti_fingerprint": 400,
        "voice_control": 600, "air_purification": 900,
        "hand_sanitizer": 300, "emergency_intercom": 500
    }

    @classmethod
    def generate_quote(cls, cabin_design, dimensions, customizations, installation_location, customer_tier="standard"):
        base_price = cls.BASE_PRICES.get(customer_tier, 8500)
        material_cost = sum(base_price * (cls.MATERIAL_MULTIPLIERS.get(m.lower().replace(" ", "_"), 1.0) - 1.0) * 0.3 
                           for m in cabin_design.get("materials", []))
        feature_costs = {f: cls.FEATURE_PRICES.get(f.lower().replace(" ", "_"), 0) for f in customizations}
        standard_area = 1.4 * 1.6
        actual_area = dimensions.get("width", 1.4) * dimensions.get("depth", 1.6)
        dim_mult = max(0.8, actual_area / standard_area)
        install_mult = {"villa": 1.0, "penthouse": 1.15, "commercial": 1.3, "historic_building": 1.4}.get(installation_location.lower(), 1.0)

        subtotal = (base_price + material_cost + sum(feature_costs.values())) * dim_mult
        installation = subtotal * 0.15 * install_mult
        shipping = 800 if dimensions.get("width", 1.4) > 1.6 else 500
        tax = (subtotal + installation) * 0.05
        total = subtotal + installation + shipping + tax

        return {
            "quote_id": f"EQ-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            "cabin_design": cabin_design.get("name", "Custom"),
            "dimensions": dimensions,
            "breakdown": {
                "base_price": round(base_price, 2),
                "material_premium": round(material_cost, 2),
                "features": {k: round(v, 2) for k, v in feature_costs.items()},
                "subtotal": round(subtotal, 2),
                "installation": round(installation, 2),
                "shipping": round(shipping, 2),
                "tax_vat_5%": round(tax, 2)
            },
            "total": round(total, 2),
            "currency": "USD",
            "delivery_time": "8-12 weeks",
            "warranty": "2 years comprehensive"
        }

class WhatsAppAPI:
    def __init__(self):
        self.api_token = os.getenv("WHATSAPP_API_TOKEN")
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        self.base_url = f"{SalesAgentConfig.WHATSAPP_API_BASE}/{SalesAgentConfig.WHATSAPP_API_VERSION}"

    async def send_text_message(self, to_number: str, message: str):
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "text",
            "text": {"body": message}
        }
        headers = {"Authorization": f"Bearer {self.api_token}", "Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                return await resp.json()

    async def send_media_message(self, to_number: str, media_type: str, media_url: str, caption: str = ""):
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": media_type,
            media_type: {"link": media_url, "caption": caption}
        }
        headers = {"Authorization": f"Bearer {self.api_token}", "Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                return await resp.json()

    async def send_interactive_message(self, to_number: str, header: str, body: str, buttons: List[Dict]):
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "header": {"type": "text", "text": header},
                "body": {"text": body},
                "action": {"buttons": [{"type": "reply", "reply": {"id": b["id"], "title": b["title"]}} for b in buttons]}
            }
        }
        headers = {"Authorization": f"Bearer {self.api_token}", "Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                return await resp.json()

@tool
async def generate_quote(cabin_design: Dict, customer_details: Dict, customizations: Optional[List[str]] = None) -> Dict:
    """Generate professional quote for elevator cabin"""
    customizations = customizations or []
    quote = QuoteGenerator.generate_quote(
        cabin_design=cabin_design,
        dimensions=cabin_design.get("dimensions", {"width": 1.4, "depth": 1.6, "height": 2.5}),
        customizations=customizations,
        installation_location=customer_details.get("location", "villa"),
        customer_tier=customer_details.get("tier", "standard")
    )
    return quote

@tool
async def send_quote_via_whatsapp(phone_number: str, quote: Dict, preview_image_url: Optional[str] = None) -> Dict:
    """Send quote to customer via WhatsApp"""
    wa = WhatsAppAPI()

    quote_text = f"""*Your Elevator Cabin Quote*

Quote ID: {quote['quote_id']}
Design: {quote['cabin_design']}

*Price Breakdown:*
Base Price: ${quote['breakdown']['base_price']:,.2f}
Materials: ${quote['breakdown']['material_premium']:,.2f}
Subtotal: ${quote['breakdown']['subtotal']:,.2f}
Installation: ${quote['breakdown']['installation']:,.2f}
Shipping: ${quote['breakdown']['shipping']:,.2f}
Tax (5%): ${quote['breakdown']['tax_vat_5%']:,.2f}

*TOTAL: ${quote['total']:,.2f}*

Delivery: {quote['delivery_time']}
Warranty: {quote['warranty']}

Reply *BOOK* to schedule consultation
Reply *CUSTOMIZE* to modify design"""

    await wa.send_text_message(phone_number, quote_text)

    if preview_image_url:
        await wa.send_media_message(phone_number, "image", preview_image_url, f"Your {quote['cabin_design']} - 3D Preview")

    await wa.send_interactive_message(
        phone_number,
        "Ready to proceed?",
        "Our design team is ready to finalize your elevator cabin.",
        [
            {"id": "book_consultation", "title": "Book Consultation"},
            {"id": "customize_design", "title": "Customize"},
            {"id": "ask_question", "title": "Ask Question"}
        ]
    )

    return {"status": "sent", "quote_id": quote["quote_id"], "phone": phone_number}

@tool
async def handle_whatsapp_webhook(payload: Dict) -> Dict:
    """Handle incoming WhatsApp webhook"""
    entry = payload.get("entry", [{}])[0]
    changes = entry.get("changes", [{}])[0]
    value = changes.get("value", {})

    if "messages" in value:
        message = value["messages"][0]
        from_number = message.get("from")
        msg_type = message.get("type")

        if msg_type == "text":
            text = message["text"]["body"].lower().strip()
            wa = WhatsAppAPI()

            if text in ["book", "schedule"]:
                await wa.send_text_message(from_number, "*Consultation Booking*\n\nOur team is available Mon-Fri 9AM-6PM. Please reply with your preferred date/time.")
                return {"status": "booking_requested"}
            elif text in ["customize", "modify"]:
                await wa.send_interactive_message(from_number, "Customize", "What to customize?", [
                    {"id": "mat", "title": "Materials"}, {"id": "dim", "title": "Dimensions"}, {"id": "feat", "title": "Features"}
                ])
                return {"status": "customization_requested"}
            else:
                await wa.send_text_message(from_number, "Thank you for your message! Our team will respond shortly. For urgent inquiries, call +1 (555) 123-4567")
                return {"status": "general_response"}

    return {"status": "processed"}

# ADK Agent Definition
sales_agent_def = Agent(
    name="sales_converter",
    description="Converts leads to WhatsApp with professional quotes and consultation booking",
    model="gemini-1.5-pro-002",
    tools=[generate_quote, send_quote_via_whatsapp, handle_whatsapp_webhook],
    instruction="You are SalesAgent. Generate quotes, send via WhatsApp, handle bookings. Be professional, concise, and always offer consultation."
)
