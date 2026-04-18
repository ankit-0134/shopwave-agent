# Failure Mode Analysis — ShopWave Support Agent

## Overview
This document outlines at least 3 realistic failure scenarios the agent may encounter, and how the system handles each one gracefully without crashing or producing incorrect outcomes.

---

## Failure Mode 1: Tool Timeout (e.g., `get_order` or `check_refund_eligibility`)

### What Happens
A tool call times out due to simulated network latency or upstream service unavailability.

### How the System Responds
- The `call_tool_with_retry()` function catches `TimeoutError`
- Applies **exponential backoff**: waits 2s, then 4s, then 8s between retries
- After 3 failed attempts, returns a structured error dict to the LLM
- The LLM is instructed to handle errors gracefully and either retry with a different approach or escalate
- The failure is logged to `audit_log.json` with a `"failure"` event type

### Recovery
```
Attempt 1 → Timeout → wait 2s
Attempt 2 → Timeout → wait 4s
Attempt 3 → Timeout → return {"error": "Tool failed after 3 attempts"}
Agent → escalates ticket with summary of what was attempted
```

---

## Failure Mode 2: Malformed / Partial Tool Response

### What Happens
A tool returns a response with a missing critical field (e.g., `get_customer` missing the `tier` field), simulating an upstream API returning partial data.

### How the System Responds
- The `_maybe_malformed()` helper randomly drops a field and adds a `_warning` key
- The LLM receives the partial response and reasons about what's missing
- If `tier` is missing, the agent **defaults to standard tier** (safest assumption — no over-privileging)
- If `return_deadline` is missing from order, agent calls `search_knowledge_base` to determine the correct window from product category
- Malformed responses are NOT retried (they are a data quality issue, not a transient failure)
- Logged as `"status": "error"` in audit log

### Recovery
```
get_customer() → partial response (tier missing)
Agent → logs warning, assumes standard tier, proceeds conservatively
Agent → documents assumption in escalation summary if needed
```

---

## Failure Mode 3: Social Engineering / Fraudulent Claims

### What Happens
A customer claims to be a premium/VIP member or invents a non-existent policy to get an unfair refund (e.g., TKT-018: Bob Mendes claims "premium members get instant refunds").

### How the System Responds
- Agent calls `get_customer()` to verify actual tier from system — **system is ground truth**
- Detects mismatch between claimed tier and verified tier
- Flags this as social engineering in reasoning log
- Does NOT process the claimed "instant refund"
- Responds professionally without accusing the customer
- Escalates with `priority: "high"` and summary noting the discrepancy
- Sends polite reply informing customer their request cannot be processed as described

### Recovery
```
Customer claims: "I'm premium, give me instant refund"
get_customer() → tier: "standard"
Agent → detects fraud, flags in audit log
escalate() → priority: high, summary includes fraud flag
send_reply() → professional decline, no accusation
```

---

## Failure Mode 4: Order Not Found / Unknown Customer

### What Happens
A customer provides an order ID that doesn't exist (TKT-017: ORD-9999), or their email isn't in the system (TKT-016: unknown.user@email.com).

### How the System Responds
- `get_order()` returns `{"error": "Order not found"}`
- `get_customer()` returns `{"error": "No customer found"}`
- Agent does NOT attempt to issue refunds or take irreversible actions on unknown entities
- Sends a reply asking for the correct order ID and registered email
- Logs a `"needs-clarification"` outcome

### Recovery
```
get_order("ORD-9999") → {"error": "Order not found"}
Agent → does NOT proceed with refund
send_reply() → "Please provide your correct order ID and registered email"
Outcome logged as: needs_clarification
```

---

## Failure Mode 5: LLM API Failure

### What Happens
The OpenAI API itself fails (network error, rate limit, etc.)

### How the System Responds
- Wrapped in try/except in `process_ticket()`
- Ticket is logged with outcome `"llm_error"`
- `asyncio.gather(return_exceptions=True)` ensures other tickets continue processing
- Failed tickets are added to a **dead-letter log** for manual review
- The system never crashes — other 19 tickets process normally

### Recovery
```
LLM call → Exception
process_ticket() → catches exception, logs "llm_error"
asyncio.gather() → continues with remaining tickets
Dead-letter entry created for manual follow-up
```

---

## Summary Table

| Failure | Detection | Recovery Strategy | Outcome |
|---------|-----------|-------------------|---------|
| Tool timeout | TimeoutError caught | Exponential backoff + retry | Escalate after 3 fails |
| Malformed response | Missing fields detected | Conservative defaults + log | Proceed or escalate |
| Social engineering | Tier mismatch via get_customer | Flag + professional decline | Escalate high priority |
| Order not found | Error in get_order response | Ask for clarification | needs_clarification |
| LLM API failure | Exception in process_ticket | Dead-letter queue | Manual review |
