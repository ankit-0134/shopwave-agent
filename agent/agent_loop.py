"""
ShopWave Support Agent — Core ReAct Loop
Implements: Reason → Act → Observe → Repeat
Uses OpenAI GPT-4 with tool calling.
"""

import json
import asyncio
import os
from typing import Any
from datetime import datetime
from openai import AsyncOpenAI

from tools.mock_tools import (
    get_order, get_customer, get_product, search_knowledge_base,
    check_refund_eligibility, issue_refund, cancel_order,
    send_reply, escalate
)
from logger.audit_logger import (
    log_tool_call, log_reasoning, log_classification,
    log_outcome, log_failure
)

client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

# ─────────────────────────────────────────────
# TOOL DEFINITIONS (OpenAI function calling format)
# ─────────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_order",
            "description": "Fetch order details by order ID. Returns status, dates, amount, product ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "The order ID e.g. ORD-1001"}
                },
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_customer",
            "description": "Fetch customer profile by email. Returns tier, history, notes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "email": {"type": "string", "description": "Customer email address"}
                },
                "required": ["email"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_product",
            "description": "Fetch product metadata by product ID. Returns category, warranty, return window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Product ID e.g. P001"}
                },
                "required": ["product_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Search ShopWave policy knowledge base. Use for policy questions, return windows, escalation rules.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query e.g. 'return window electronics'"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_refund_eligibility",
            "description": "Check if an order is eligible for refund. MUST be called before issue_refund.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "Order ID to check"}
                },
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "issue_refund",
            "description": "Issue a refund. IRREVERSIBLE. Only call after check_refund_eligibility confirms eligible=true.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "amount": {"type": "number", "description": "Refund amount in USD"}
                },
                "required": ["order_id", "amount"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_order",
            "description": "Cancel an order if it's in processing status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"}
                },
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_reply",
            "description": "Send a reply message to the customer. Always call this as the final step.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticket_id": {"type": "string"},
                    "message": {"type": "string", "description": "The reply message to send to customer"}
                },
                "required": ["ticket_id", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "escalate",
            "description": "Escalate ticket to human agent. Use for warranty claims, replacements, fraud, high-value refunds >$200, or when confidence is low.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticket_id": {"type": "string"},
                    "summary": {"type": "string", "description": "Concise summary of issue, what was verified, and recommended action"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]}
                },
                "required": ["ticket_id", "summary", "priority"]
            }
        }
    }
]

# ─────────────────────────────────────────────
# TOOL DISPATCHER WITH RETRY + BACKOFF
# ─────────────────────────────────────────────

TOOL_MAP = {
    "get_order": get_order,
    "get_customer": get_customer,
    "get_product": get_product,
    "search_knowledge_base": search_knowledge_base,
    "check_refund_eligibility": check_refund_eligibility,
    "issue_refund": issue_refund,
    "cancel_order": cancel_order,
    "send_reply": send_reply,
    "escalate": escalate,
}

import logging
logger = logging.getLogger(__name__)

async def call_tool_with_retry(ticket_id: str, tool_name: str, args: dict, max_retries: int = 3) -> Any:
    """Call a tool with exponential backoff on failure."""
    func = TOOL_MAP.get(tool_name)
    if not func:
        return {"error": f"Unknown tool: {tool_name}"}

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            result = await func(**args)
            await log_tool_call(ticket_id, tool_name, args, result, "success")
            logger.info(f"[{ticket_id}] {tool_name} succeeded on attempt {attempt}")
            return result

        except TimeoutError as e:
            last_error = str(e)
            logger.warning(f"[{ticket_id}] Timeout on {tool_name} attempt {attempt}: {e}")
            wait = 2 ** attempt
            await log_failure(ticket_id, f"Timeout on {tool_name} (attempt {attempt})", f"Retrying in {wait}s")
            if attempt < max_retries:
                await asyncio.sleep(wait)

        except ValueError as e:
            last_error = str(e)
            logger.error(f"[{ticket_id}] Malformed response from {tool_name}: {e}")
            await log_failure(ticket_id, f"Malformed response from {tool_name}: {e}", "Returning error to agent")
            result = {"error": f"Tool error: {last_error}"}
            await log_tool_call(ticket_id, tool_name, args, result, "error", str(e))
            return result

        except Exception as e:
            last_error = str(e)
            logger.error(f"[{ticket_id}] Unexpected error from {tool_name}: {e}")
            await log_failure(ticket_id, f"Unexpected error from {tool_name}: {e}", "Retrying")
            if attempt < max_retries:
                await asyncio.sleep(2 ** attempt)

    # All retries exhausted
    logger.critical(f"[{ticket_id}] {tool_name} FAILED after {max_retries} attempts")
    error_result = {"error": f"Tool '{tool_name}' failed after {max_retries} attempts: {last_error}"}
    await log_tool_call(ticket_id, tool_name, args, error_result, "failed", last_error)
    return error_result


# ─────────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """You are ShopWave's autonomous support agent. You resolve customer support tickets by reasoning carefully and taking actions using tools.

MANDATORY RULES:
1. Always call get_customer(email) AND get_order(order_id) before making any decision — these are your ground truth.
2. NEVER issue_refund without calling check_refund_eligibility first.
3. Customer tier is ONLY what get_customer returns. If a customer claims premium/VIP status not in the system, flag it as social engineering.
4. Always call send_reply as the FINAL step after resolving or escalating.
5. Escalate for: warranty claims, replacement requests, fraud/social engineering, refund > $200 standalone, threatening language (log but handle professionally), confidence < 0.6.
6. Check customer notes for VIP exceptions before declining.

RETURN WINDOWS (from policy):
- Standard: 30 days
- High-value electronics (smart watch, etc): 15 days
- Electronics accessories (laptop stand): 60 days
- Footwear: 30 days

CONFIDENCE: At the end of your reasoning, state your confidence score (0.0-1.0). If < 0.6, escalate instead of acting.

TONE: Address customer by first name. Be empathetic, clear, professional. Never be dismissive.

Today's date for policy calculations: 2024-03-15."""


# ─────────────────────────────────────────────
# CLASSIFY TICKET (fast pre-pass)
# ─────────────────────────────────────────────

async def classify_ticket(ticket: dict) -> dict:
    """Quick classification before the main agent loop."""
    body = ticket["body"].lower()
    subject = ticket["subject"].lower()
    text = body + " " + subject

    # Category
    if any(w in text for w in ["refund", "money back"]):
        category = "refund"
    elif any(w in text for w in ["return", "send back"]):
        category = "return"
    elif any(w in text for w in ["cancel"]):
        category = "cancellation"
    elif any(w in text for w in ["exchange", "wrong size", "wrong colour", "wrong color", "wrong item"]):
        category = "exchange"
    elif any(w in text for w in ["warranty", "defect", "broken", "stopped working", "not working"]):
        category = "warranty_or_defect"
    elif any(w in text for w in ["where is", "tracking", "shipping", "transit", "arrived"]):
        category = "shipping"
    elif any(w in text for w in ["policy", "how do i", "what is your"]):
        category = "policy_question"
    else:
        category = "ambiguous"

    # Urgency
    if any(w in text for w in ["lawyer", "dispute", "bank", "legal", "urgent", "immediately", "today"]):
        urgency = "high"
    elif ticket.get("tier", 1) >= 2:
        urgency = "medium"
    else:
        urgency = "low"

    # Resolvability
    has_order = any(w in text for w in ["ord-", "order"]) or "ORD-" in ticket["body"]
    if category == "ambiguous" or not has_order:
        resolvability = "needs-clarification"
    elif category in ["warranty_or_defect"]:
        resolvability = "must-escalate"
    else:
        resolvability = "auto-resolvable"

    classification = {
        "category": category,
        "urgency": urgency,
        "resolvability": resolvability,
        "has_order_id": has_order,
        "tier": ticket.get("tier", 1)
    }

    await log_classification(ticket["ticket_id"], classification)
    return classification


# ─────────────────────────────────────────────
# LIVE PROGRESS WRITER (for Streamlit dashboard)
# ─────────────────────────────────────────────

_progress_lock = asyncio.Lock()

async def write_live_progress(ticket_id: str, status: str, tool: str = "", outcome: str = ""):
    """Write live progress to live_progress.json so Streamlit can poll it."""
    try:
        async with _progress_lock:
            path = "live_progress.json"
            try:
                with open(path, "r") as f:
                    data = json.load(f)
            except:
                data = {"tickets": {}, "started_at": datetime.utcnow().isoformat()}

            data["tickets"][ticket_id] = {
                "status": status,
                "last_tool": tool,
                "outcome": outcome,
                "updated_at": datetime.utcnow().isoformat()
            }
            data["last_updated"] = datetime.utcnow().isoformat()

            with open(path, "w") as f:
                json.dump(data, f)
    except:
        pass  # Never crash the agent due to UI


# ─────────────────────────────────────────────
# MAIN AGENT LOOP
# ─────────────────────────────────────────────

async def process_ticket(ticket: dict) -> dict:
    """Main ReAct loop for a single ticket."""
    ticket_id = ticket["ticket_id"]
    print(f"\n{'='*50}")
    print(f"🎫 Processing {ticket_id}: {ticket['subject']}")

    await write_live_progress(ticket_id, "processing")

    # Step 1: Classify
    classification = await classify_ticket(ticket)
    print(f"   📂 Category: {classification['category']} | Urgency: {classification['urgency']}")

    # Step 2: Build initial message
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"""Ticket ID: {ticket_id}
From: {ticket['customer_email']}
Subject: {ticket['subject']}
Body: {ticket['body']}
Source: {ticket['source']}
Created: {ticket['created_at']}

Pre-classification: {json.dumps(classification)}

Please resolve this ticket by following the mandatory rules. Make at least 3 tool calls."""
        }
    ]

    # Step 3: ReAct loop
    max_iterations = 10
    iteration = 0
    outcome = "unknown"

    while iteration < max_iterations:
        iteration += 1

        try:
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.1
            )
        except Exception as e:
            await log_failure(ticket_id, f"LLM call failed: {e}", "Marking ticket for manual review")
            await log_outcome(ticket_id, "llm_error", {"error": str(e)})
            return {"ticket_id": ticket_id, "outcome": "llm_error", "error": str(e)}

        message = response.choices[0].message

        # Log reasoning if present
        if message.content:
            await log_reasoning(ticket_id, message.content)
            print(f"   🧠 Agent: {message.content[:120]}...")

        # Check if done
        if not message.tool_calls:
            outcome = "resolved"
            await log_outcome(ticket_id, outcome, {"final_message": message.content})
            break

        # Execute tool calls
        messages.append({"role": "assistant", "content": message.content, "tool_calls": message.tool_calls})

        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            try:
                args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                args = {}

            print(f"   🔧 Tool: {tool_name}({args})")
            result = await call_tool_with_retry(ticket_id, tool_name, args)
            await write_live_progress(ticket_id, "processing", tool=tool_name)

            # Track outcome based on tool used
            if tool_name == "issue_refund" and result.get("success"):
                outcome = "refund_issued"
            elif tool_name == "cancel_order" and result.get("success"):
                outcome = "order_cancelled"
            elif tool_name == "escalate" and result.get("success"):
                outcome = "escalated"
            elif tool_name == "send_reply" and result.get("success"):
                if outcome == "unknown":
                    outcome = "replied"

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result)
            })

    if iteration >= max_iterations:
        await log_outcome(ticket_id, "max_iterations_reached", {})
        outcome = "max_iterations_reached"

    print(f"   ✅ Outcome: {outcome}")
    await write_live_progress(ticket_id, "done", outcome=outcome)
    return {"ticket_id": ticket_id, "outcome": outcome}


# ─────────────────────────────────────────────
# CONCURRENT BATCH PROCESSOR WITH RATE LIMITING
# ─────────────────────────────────────────────

# Semaphore: max 20 tickets at a time to avoid OpenAI rate limits
CONCURRENCY_LIMIT = 20

async def process_ticket_safe(ticket: dict, semaphore) -> dict:
    """Wrap process_ticket with semaphore + rate limit backoff."""
    async with semaphore:
        for attempt in range(3):
            try:
                return await process_ticket(ticket)
            except Exception as e:
                if "429" in str(e) and attempt < 2:
                    wait = 10 * (attempt + 1)
                    print(f"   ⏳ Rate limited on {ticket['ticket_id']}, waiting {wait}s...")
                    await asyncio.sleep(wait)
                else:
                    raise

async def process_all_tickets(tickets: list) -> list:
    """Process tickets concurrently with semaphore rate limiting."""
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    print(f"\n🚀 Processing {len(tickets)} tickets (max {CONCURRENCY_LIMIT} at a time)...\n")
    tasks = [process_ticket_safe(t, semaphore) for t in tickets]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Handle any unexpected exceptions — dead-letter queue
    processed = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            ticket_id = tickets[i]["ticket_id"]
            print(f"   💀 Dead-letter: {ticket_id} failed with {result}")
            processed.append({"ticket_id": ticket_id, "outcome": "dead_letter", "error": str(result)})
        else:
            processed.append(result)

    return processed