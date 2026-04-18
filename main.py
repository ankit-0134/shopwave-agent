"""
ShopWave Autonomous Support Agent
Main entry point — run with: python main.py

Requirements:
    pip install openai python-dotenv
    export OPENAI_API_KEY=your_key_here  (or create a .env file)
"""

import asyncio
import json
import os
import time
from dotenv import load_dotenv


import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("agent.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()  # Load from .env file if present

from agent.agent_loop import process_all_tickets
from logger.audit_logger import save_audit_log, get_full_log


def load_tickets(path: str = "mocks/tickets.json") -> list:
    with open(path) as f:
        return json.load(f)


async def main():
    print("=" * 60)
    print("  ShopWave Autonomous Support Resolution Agent")
    print("  Ksolves Agentic AI Hackathon 2026")
    print("=" * 60)

    # Validate API key
    if not os.environ.get("OPENAI_API_KEY"):
        print("\n❌ ERROR: OPENAI_API_KEY not set.")
        print("   Set it via: export OPENAI_API_KEY=your_key")
        print("   Or create a .env file with: OPENAI_API_KEY=your_key")
        return

    # Load tickets
    tickets = load_tickets()
    print(f"\n📥 Loaded {len(tickets)} tickets from mocks/tickets.json")

    # Process all tickets concurrently
    start_time = time.time()
    results = await process_all_tickets(tickets)
    elapsed = time.time() - start_time

    # Summary
    print("\n" + "=" * 60)
    print(f"  ✅ Processing Complete in {elapsed:.1f}s")
    print("=" * 60)

    outcome_counts = {}
    for r in results:
        outcome = r.get("outcome", "unknown")
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1

    print("\n📊 Outcome Summary:")
    for outcome, count in sorted(outcome_counts.items()):
        print(f"   {outcome}: {count}")

    # Save audit log
    save_audit_log("audit_log.json")
    print(f"\n📋 Total events logged: {len(get_full_log())}")


if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
