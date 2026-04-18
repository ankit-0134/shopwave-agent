"""
Mock Tools for ShopWave Support Agent
Each tool simulates realistic failures: timeouts, malformed data, missing fields.
"""

import json
import asyncio
import random
import os
from datetime import datetime


def validate_order(data: dict) -> bool:
    """Check order data has required fields before acting."""
    required = ["order_id", "status"]
    return all(k in data for k in required)

def validate_customer(data: dict) -> bool:
    """Check customer data has required fields before acting."""
    required = ["customer_id", "tier"]
    return all(k in data for k in required)

# Load mock data
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOCKS_DIR = os.path.join(BASE_DIR, "mocks")

def _load(filename):
    with open(os.path.join(MOCKS_DIR, filename)) as f:
        return json.load(f)

ORDERS = {o["order_id"]: o for o in _load("orders.json")}
CUSTOMERS = {c["email"]: c for c in _load("customers.json")}
PRODUCTS = {p["product_id"]: p for p in _load("products.json")}

with open(os.path.join(MOCKS_DIR, "knowledge-base.md")) as f:
    KNOWLEDGE_BASE = f.read()

# Simulated cancelled orders (in-memory state)
CANCELLED_ORDERS = set()
ISSUED_REFUNDS = {}  # order_id -> amount
SENT_REPLIES = []
ESCALATIONS = []

# ─────────────────────────────────────────────
# FAILURE SIMULATION HELPERS
# ─────────────────────────────────────────────

def _maybe_timeout(tool_name: str, probability: float = 0.08):
    """Randomly simulate a timeout for realism."""
    if random.random() < probability:
        raise TimeoutError(f"[{tool_name}] Tool timed out after 5s")

def _maybe_malformed(tool_name: str, data: dict, probability: float = 0.06):
    """Randomly drop a key to simulate malformed response."""
    if random.random() < probability:
        data = dict(data)
        key_to_drop = random.choice(list(data.keys()))
        del data[key_to_drop]
        data["_warning"] = f"Partial response: field '{key_to_drop}' missing"
    return data

# ─────────────────────────────────────────────
# READ / LOOKUP TOOLS
# ─────────────────────────────────────────────

async def get_order(order_id: str) -> dict:
    """Fetch order details by order ID."""
    await asyncio.sleep(random.uniform(0.05, 0.3))  # simulate network latency
    _maybe_timeout("get_order", probability=0.08)

    if order_id in CANCELLED_ORDERS:
        return {"order_id": order_id, "status": "cancelled", "notes": "Order was cancelled by customer request."}

    order = ORDERS.get(order_id)
    if not order:
        return {"error": f"Order '{order_id}' not found in system.", "order_id": order_id}

    result = dict(order)
    if order_id in ISSUED_REFUNDS:
        result["refund_status"] = "refunded"
        result["refund_amount"] = ISSUED_REFUNDS[order_id]

    return _maybe_malformed("get_order", result)


async def get_customer(email: str) -> dict:
    """Fetch customer profile by email."""
    await asyncio.sleep(random.uniform(0.05, 0.25))
    _maybe_timeout("get_customer", probability=0.06)

    customer = CUSTOMERS.get(email)
    if not customer:
        return {"error": f"No customer found with email '{email}'.", "email": email}

    # Also find all orders for this customer
    customer_orders = [o["order_id"] for o in ORDERS.values() if o["customer_id"] == customer["customer_id"]]
    result = dict(customer)
    result["order_history"] = customer_orders

    return _maybe_malformed("get_customer", result)


async def get_product(product_id: str) -> dict:
    """Fetch product metadata by product ID."""
    await asyncio.sleep(random.uniform(0.05, 0.2))
    _maybe_timeout("get_product", probability=0.05)

    product = PRODUCTS.get(product_id)
    if not product:
        return {"error": f"Product '{product_id}' not found.", "product_id": product_id}

    return _maybe_malformed("get_product", dict(product))


async def search_knowledge_base(query: str) -> dict:
    """Search the knowledge base for policy information."""
    await asyncio.sleep(random.uniform(0.1, 0.4))
    _maybe_timeout("search_knowledge_base", probability=0.05)

    query_lower = query.lower()
    sections = KNOWLEDGE_BASE.split("## ")
    relevant = []

    keywords_map = {
        "return": ["return", "window", "deadline"],
        "refund": ["refund", "eligib", "process"],
        "warranty": ["warranty", "defect", "manufactur"],
        "cancel": ["cancel", "processing", "shipped"],
        "exchange": ["exchange", "wrong item", "colour", "size"],
        "tier": ["tier", "vip", "premium", "standard"],
        "escalat": ["escalat", "human", "specialist"],
        "damaged": ["damaged", "broken", "arrival"],
        "shipping": ["shipping", "transit", "tracking"],
    }

    for section in sections:
        section_text = section.lower()
        for key, kws in keywords_map.items():
            if key in query_lower:
                if any(kw in section_text for kw in kws):
                    relevant.append(section[:800])
                    break

    if not relevant:
        # fallback: return first 1000 chars of KB
        relevant = [KNOWLEDGE_BASE[:1000]]

    return {
        "query": query,
        "results": relevant[:3],
        "source": "ShopWave Knowledge Base"
    }


# ─────────────────────────────────────────────
# WRITE / ACT TOOLS
# ─────────────────────────────────────────────

async def check_refund_eligibility(order_id: str) -> dict:
    """
    Check if an order is eligible for a refund.
    WARNING: May throw errors — agent must handle gracefully.
    """
    await asyncio.sleep(random.uniform(0.1, 0.5))
    _maybe_timeout("check_refund_eligibility", probability=0.1)

    # Simulate occasional malformed response
    if random.random() < 0.07:
        raise ValueError(f"[check_refund_eligibility] Malformed response for order {order_id}: upstream service error")

    if order_id in CANCELLED_ORDERS:
        return {"eligible": False, "reason": "Order has been cancelled. No refund applicable."}

    order = ORDERS.get(order_id)
    if not order:
        return {"eligible": False, "reason": f"Order '{order_id}' not found."}

    if order.get("refund_status") == "refunded" or order_id in ISSUED_REFUNDS:
        return {"eligible": False, "reason": "Refund already issued for this order."}

    if order["status"] == "processing":
        return {"eligible": False, "reason": "Order not yet delivered. Cancel the order instead."}

    if order["status"] == "shipped":
        return {"eligible": False, "reason": "Order in transit. Must wait for delivery before refund."}

    # Check return deadline
    return_deadline = order.get("return_deadline")
    if return_deadline:
        deadline_dt = datetime.strptime(return_deadline, "%Y-%m-%d")
        ticket_date = datetime(2024, 3, 15)  # simulated "today"
        if ticket_date > deadline_dt:
            return {
                "eligible": False,
                "reason": f"Return window expired on {return_deadline}.",
                "return_deadline": return_deadline
            }

    return {
        "eligible": True,
        "reason": "Order is within return window and eligible for refund.",
        "amount": order["amount"],
        "return_deadline": return_deadline
    }


async def issue_refund(order_id: str, amount: float) -> dict:
    """
    Issue a refund. IRREVERSIBLE — must check eligibility first.
    Will raise an error if called without prior eligibility check signal.
    """
    await asyncio.sleep(random.uniform(0.2, 0.6))
    _maybe_timeout("issue_refund", probability=0.07)

    order = ORDERS.get(order_id)
    if not order:
        return {"success": False, "error": f"Order '{order_id}' not found. Refund not issued."}

    if order.get("refund_status") == "refunded" or order_id in ISSUED_REFUNDS:
        return {"success": False, "error": "Refund already issued for this order."}

    if order_id in CANCELLED_ORDERS:
        return {"success": False, "error": "Order is cancelled. No refund applicable."}

    # Issue the refund
    ISSUED_REFUNDS[order_id] = amount
    return {
        "success": True,
        "order_id": order_id,
        "amount_refunded": amount,
        "message": f"Refund of ${amount:.2f} successfully issued to original payment method.",
        "processing_time": "5-7 business days"
    }


async def cancel_order(order_id: str) -> dict:
    """Cancel an order if it's in processing status."""
    await asyncio.sleep(random.uniform(0.1, 0.3))
    _maybe_timeout("cancel_order", probability=0.06)

    order = ORDERS.get(order_id)
    if not order:
        return {"success": False, "error": f"Order '{order_id}' not found."}

    if order["status"] == "processing":
        CANCELLED_ORDERS.add(order_id)
        return {
            "success": True,
            "order_id": order_id,
            "message": "Order successfully cancelled. Confirmation email will be sent within 1 hour."
        }
    elif order["status"] == "shipped":
        return {"success": False, "error": "Order already shipped. Cannot cancel. Customer must wait for delivery and initiate a return."}
    elif order["status"] == "delivered":
        return {"success": False, "error": "Order already delivered. Cannot cancel. Please initiate a return instead."}
    else:
        return {"success": False, "error": f"Order status '{order['status']}' does not allow cancellation."}


async def send_reply(ticket_id: str, message: str) -> dict:
    """Send a reply to the customer."""
    await asyncio.sleep(random.uniform(0.05, 0.2))
    _maybe_timeout("send_reply", probability=0.04)

    SENT_REPLIES.append({
        "ticket_id": ticket_id,
        "message": message,
        "sent_at": datetime.utcnow().isoformat()
    })
    return {
        "success": True,
        "ticket_id": ticket_id,
        "message": "Reply sent to customer successfully."
    }


async def escalate(ticket_id: str, summary: str, priority: str) -> dict:
    """Escalate ticket to a human agent with full context."""
    await asyncio.sleep(random.uniform(0.05, 0.15))
    _maybe_timeout("escalate", probability=0.03)

    valid_priorities = ["low", "medium", "high", "urgent"]
    if priority not in valid_priorities:
        priority = "medium"

    ESCALATIONS.append({
        "ticket_id": ticket_id,
        "summary": summary,
        "priority": priority,
        "escalated_at": datetime.utcnow().isoformat()
    })
    return {
        "success": True,
        "ticket_id": ticket_id,
        "priority": priority,
        "message": f"Ticket escalated to human agent with priority '{priority}'."
    }
