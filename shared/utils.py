"""
Shared utilities for ElevatorAI ADK agents
"""
import json
import logging
from typing import Dict, Any
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("elevator-ai")

def log_agent_action(agent_name: str, action: str, details: Dict[str, Any]):
    """Log agent actions for monitoring and debugging"""
    logger.info(f"[{agent_name}] {action}: {json.dumps(details)}")

def format_currency(amount: float, currency: str = "USD") -> str:
    """Format amount as currency string"""
    symbols = {"USD": "$", "EUR": "€", "GBP": "£", "AED": "AED "}
    symbol = symbols.get(currency, "$")
    return f"{symbol}{amount:,.2f}"

def validate_phone_number(phone: str) -> bool:
    """Validate international phone number format"""
    import re
    pattern = r'^\+[1-9]\d{1,14}$'
    return bool(re.match(pattern, phone.replace(" ", "")))

def generate_session_id() -> str:
    """Generate unique session ID"""
    return f"elevator_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{__import__('uuid').uuid4().hex[:8]}"

def serialize_for_json(obj: Any) -> Any:
    """Serialize objects for JSON response"""
    if hasattr(obj, '__dict__'):
        return obj.__dict__
    return str(obj)
