"""
Audit Logger for ShopWave Support Agent
Logs every tool call, reasoning chain, and final outcome per ticket.
"""

import json
import asyncio
from datetime import datetime
from typing import Any

# Thread-safe log storage
_audit_log = []
_lock = asyncio.Lock()


async def log_event(ticket_id: str, event_type: str, data: dict):
    """Log a single event for a ticket."""
    async with _lock:
        _audit_log.append({
            "ticket_id": ticket_id,
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "data": data
        })


async def log_tool_call(ticket_id: str, tool_name: str, input_data: Any, output_data: Any, status: str, error: str = None):
    """Log a tool call with input, output, and status."""
    await log_event(ticket_id, "tool_call", {
        "tool": tool_name,
        "input": input_data,
        "output": output_data,
        "status": status,
        "error": error
    })


async def log_reasoning(ticket_id: str, reasoning: str):
    """Log agent reasoning step."""
    await log_event(ticket_id, "reasoning", {"text": reasoning})


async def log_classification(ticket_id: str, classification: dict):
    """Log ticket classification."""
    await log_event(ticket_id, "classification", classification)


async def log_outcome(ticket_id: str, outcome: str, details: dict = None):
    """Log final outcome for ticket."""
    await log_event(ticket_id, "outcome", {
        "result": outcome,
        "details": details or {}
    })


async def log_failure(ticket_id: str, error: str, recovery_action: str):
    """Log a failure and how it was recovered."""
    await log_event(ticket_id, "failure", {
        "error": error,
        "recovery": recovery_action
    })


def get_full_log() -> list:
    return _audit_log


def save_audit_log(filepath: str = "audit_log.json"):
    """Save full audit log to file."""
    # Group by ticket for readability
    grouped = {}
    for entry in _audit_log:
        tid = entry["ticket_id"]
        if tid not in grouped:
            grouped[tid] = []
        grouped[tid].append(entry)

    output = []
    for ticket_id, events in grouped.items():
        # Extract key summary fields
        classification = next((e["data"] for e in events if e["event_type"] == "classification"), {})
        outcome = next((e["data"] for e in events if e["event_type"] == "outcome"), {})
        tool_calls = [e["data"] for e in events if e["event_type"] == "tool_call"]
        reasoning_steps = [e["data"]["text"] for e in events if e["event_type"] == "reasoning"]
        failures = [e["data"] for e in events if e["event_type"] == "failure"]

        output.append({
            "ticket_id": ticket_id,
            "classification": classification,
            "tool_calls": tool_calls,
            "reasoning_chain": reasoning_steps,
            "failures_encountered": failures,
            "outcome": outcome,
            "total_tool_calls": len(tool_calls),
            "raw_events": events
        })

    with open(filepath, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ Audit log saved to {filepath} ({len(output)} tickets logged)")
    return filepath
