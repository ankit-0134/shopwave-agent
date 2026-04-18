# ShopWave Autonomous Support Resolution Agent
### Ksolves Agentic AI Hackathon 2026

---

## What This Is

An autonomous AI agent that resolves ShopWave customer support tickets end-to-end — no humans in the loop for standard cases. Built with a **ReAct (Reason → Act → Observe → Repeat)** architecture using OpenAI GPT-4o with real tool calling.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.10+ |
| LLM | OpenAI GPT-4o |
| Orchestration | Custom async ReAct loop |
| Concurrency | `asyncio.gather()` — all 20 tickets processed simultaneously |
| Logging | Custom audit logger → `audit_log.json` |
| Error Handling | Exponential backoff, dead-letter queue, graceful degradation |

---

## Project Structure

```
hackathon2026/
├── main.py                     # Entry point — run this
├── agent/
│   └── agent_loop.py           # Core ReAct loop, tool dispatcher, classifier
├── tools/
│   └── mock_tools.py           # All 8 mock tools with realistic failures
├── logger/
│   └── audit_logger.py         # Full audit trail per ticket
├── mocks/
│   ├── tickets.json            # 20 support tickets
│   ├── orders.json             # Order data
│   ├── customers.json          # Customer profiles + tiers
│   ├── products.json           # Product metadata
│   └── knowledge-base.md       # ShopWave policies
├── audit_log.json              # Generated after running (covers all 20 tickets)
├── failure_modes.md            # 5 failure scenarios documented
├── architecture.png            # Agent loop diagram
├── requirements.txt
└── README.md
```

---

## Setup & Run

### 1. Clone the repo
```bash
git clone https://github.com/yourusername/hackathon2026-yourname
cd hackathon2026-yourname
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set your API key
```bash
# Option A: environment variable
export OPENAI_API_KEY=your_openai_api_key_here

# Option B: create a .env file
echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
```

### 4. Run the agent
```bash
python main.py
```

That's it. The agent will process all 20 tickets concurrently and save `audit_log.json`.

---

## How the Agent Works

### ReAct Loop
```
For each ticket (all run concurrently via asyncio.gather):
  1. CLASSIFY  → urgency, category, resolvability
  2. REASON    → LLM reads ticket + pre-classification
  3. ACT       → LLM calls tools (min 3 tool calls per ticket)
  4. OBSERVE   → Tool result returned to LLM
  5. REPEAT    → Until resolution or escalation
  6. REPLY     → send_reply() always called as final step
  7. LOG       → Every step written to audit_log.json
```

### Tools Available

**Read / Lookup:**
- `get_order(order_id)` — order details, status, dates
- `get_customer(email)` — customer tier, history, notes
- `get_product(product_id)` — category, return window, warranty
- `search_knowledge_base(query)` — policy & FAQ

**Write / Act:**
- `check_refund_eligibility(order_id)` — must be called before refund
- `issue_refund(order_id, amount)` — irreversible, gated by eligibility
- `cancel_order(order_id)` — only works on processing status
- `send_reply(ticket_id, message)` — always the final step
- `escalate(ticket_id, summary, priority)` — hands off to human

### Mock Tool Failures (Realistic)
- ~8% chance of timeout on `get_order`
- ~7% chance of malformed response from `check_refund_eligibility`
- ~6% chance of partial data from `get_customer`
- All failures handled with exponential backoff + dead-letter logging

---

## Key Business Rules Encoded

- Customer tier verified from system only — self-declared tier = social engineering flag
- `issue_refund` is blocked without prior `check_refund_eligibility`
- Return windows: 15 days (smart watch), 30 days (standard), 60 days (laptop stand)
- VIP customers: always check notes for management pre-approvals before declining
- Warranty claims always escalated to warranty team
- Replacement requests always escalated (not auto-resolved)
- Refunds > $200 escalated for supervisor approval

---

## Concurrency Model

All 20 tickets are processed **simultaneously**, not sequentially:

```python
tasks = [process_ticket(t) for t in tickets]
results = await asyncio.gather(*tasks, return_exceptions=True)
```

`return_exceptions=True` ensures one failing ticket never blocks the others.

---

## Audit Log Format

Each ticket in `audit_log.json` contains:
- `classification` — category, urgency, resolvability
- `tool_calls` — every tool invoked with input, output, status
- `reasoning_chain` — LLM reasoning at each step
- `failures_encountered` — any tool errors and recovery actions
- `outcome` — final result (refund_issued / escalated / replied / etc.)

---

## Failure Handling

See `failure_modes.md` for 5 documented failure scenarios.

Summary:
1. **Tool timeout** → exponential backoff (2s, 4s, 8s) → escalate after 3 fails
2. **Malformed response** → conservative defaults, log warning
3. **Social engineering** → tier mismatch detection, flag + escalate high
4. **Order not found** → ask customer for clarification
5. **LLM API failure** → dead-letter queue, other tickets unaffected
