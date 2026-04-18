# ShopWave Autonomous Support Agent
### Ksolves Agentic AI Hackathon 2026

---

## Live Demo
**[Click here to try the live app](https://your-app.streamlit.app)**

---

## What This Is

An autonomous AI agent that resolves ShopWave customer support tickets end-to-end — no humans needed for standard cases.

Built with a **ReAct (Reason → Act → Observe → Repeat)** architecture using GPT-4o-mini with real tool calling, concurrent processing, and a live Streamlit dashboard.

---

## How To Use (Live Demo)

1. Open the live link above
2. Select any tickets from the list
3. Click **Run Agent**
4. Watch live progress in the sidebar
5. See full results — every step taken + final reply
6. Download audit log

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11 |
| LLM | OpenAI GPT-4o-mini |
| Orchestration | Custom async ReAct loop |
| Concurrency | asyncio.gather() — all tickets concurrent |
| UI | Streamlit |
| Logging | Python logging + audit_log.json |

---

## Run Locally

```bash
# 1. Clone
git clone https://github.com/ankit-0134/shopwave-agent
cd shopwave-agent

# 2. Install
pip install -r requirements.txt

# 3. Add API key
echo "OPENAI_API_KEY=your-key-here" > .env

# 4. Run
streamlit run app.py
```

---

## Project Structure

```
shopwave-agent/
├── app.py                  # Streamlit dashboard (entry point)
├── main.py                 # CLI runner
├── agent/
│   └── agent_loop.py       # ReAct loop + tool dispatcher
├── tools/
│   └── mock_tools.py       # 8 mock tools with realistic failures
├── logger/
│   └── audit_logger.py     # Full audit trail
├── mocks/
│   ├── tickets.json        # 20 support tickets
│   ├── orders.json
│   ├── customers.json
│   ├── products.json
│   └── knowledge-base.md
├── architecture.png        # Agent architecture diagram
├── failure_modes.md        # 5 failure scenarios documented
├── requirements.txt
└── README.md
```

---

## Agent Capabilities

| Ticket Type | Agent Action |
|-------------|-------------|
| Refund request | Check eligibility → issue refund |
| Return request | Verify window → approve/decline |
| Cancellation | Check status → cancel if processing |
| Wrong item | Arrange exchange or refund |
| Warranty/defect | Escalate to warranty team |
| Damaged on arrival | Full refund, no return needed |
| Ambiguous request | Ask clarifying questions |
| Fraud/social engineering | Flag and escalate |

---

## Key Features

- **Concurrent processing** — all tickets processed simultaneously via asyncio
- **ReAct loop** — minimum 3 tool calls per ticket
- **Graceful failure handling** — retry with exponential backoff
- **Dead letter queue** — failed tickets logged, never lost
- **Full audit trail** — every decision logged and downloadable
- **Live dashboard** — real-time progress visible per ticket

---

## Tools

**Read:** get_order · get_customer · get_product · search_knowledge_base

**Write:** check_refund_eligibility · issue_refund · cancel_order · send_reply · escalate

---

## Failure Modes

See failure_modes.md for 5 documented failure scenarios.