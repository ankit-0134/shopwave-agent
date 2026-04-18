"""
ShopWave Autonomous Support Agent — Interactive Demo
Run: streamlit run app.py
Deploy: streamlit cloud (free)
"""

import streamlit as st
import json
import os
import asyncio
import threading
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="ShopWave AI Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: #080b14; }
.main .block-container { padding: 2rem 2rem 4rem; max-width: 100%; }

/* HEADER */
.hero {
    background: linear-gradient(135deg, #0d1526 0%, #111827 50%, #0d1526 100%);
    border: 1px solid #1e3a5f;
    border-radius: 16px;
    padding: 32px 40px;
    margin-bottom: 28px;
    position: relative;
    overflow: hidden;
}
.hero::before {
    content: '';
    position: absolute;
    top: -50%; left: -50%;
    width: 200%; height: 200%;
    background: radial-gradient(ellipse at 70% 50%, rgba(102,126,234,0.08) 0%, transparent 60%);
    pointer-events: none;
}
.hero h1 {
    font-size: 28px; font-weight: 700;
    background: linear-gradient(135deg, #667eea, #a78bfa);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin: 0 0 6px;
}
.hero p { color: #64748b; font-size: 15px; margin: 0; }
.hero-badge {
    display: inline-block;
    background: rgba(102,126,234,0.15);
    border: 1px solid rgba(102,126,234,0.3);
    color: #818cf8;
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 12px;
    font-weight: 600;
    margin-bottom: 12px;
}

/* TICKET CARDS */
.ticket-card {
    background: #0d1220;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 16px 18px;
    margin-bottom: 10px;
    transition: border-color 0.2s, background 0.2s;
    cursor: pointer;
}
.ticket-card:hover { border-color: #334155; background: #101828; }
.ticket-card.selected { border-color: #4f46e5; background: #0f172a; }

.ticket-id {
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px; font-weight: 600;
    color: #667eea;
}
.ticket-subject { font-size: 14px; font-weight: 500; color: #e2e8f0; margin: 4px 0; }
.ticket-body-preview { font-size: 12px; color: #475569; line-height: 1.5; }

.badge {
    display: inline-block;
    padding: 2px 10px; border-radius: 10px;
    font-size: 11px; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.3px;
}
.badge-refund          { background: #1e1b4b; color: #a5b4fc; }
.badge-return          { background: #1a2744; color: #93c5fd; }
.badge-cancellation    { background: #1c2d1e; color: #86efac; }
.badge-exchange        { background: #2d1f1a; color: #fca5a5; }
.badge-warranty_or_defect { background: #2d2a14; color: #fde047; }
.badge-shipping        { background: #1a2d2d; color: #67e8f9; }
.badge-policy_question { background: #1e1e2d; color: #c4b5fd; }
.badge-ambiguous       { background: #1e1e1e; color: #94a3b8; }

.urgency-high   { color: #f87171; font-weight: 600; }
.urgency-medium { color: #fb923c; font-weight: 600; }
.urgency-low    { color: #4ade80; font-weight: 600; }

/* SIDEBAR PROGRESS */
.sb-ticket {
    background: #0d1220;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 10px 14px;
    margin-bottom: 8px;
    transition: all 0.3s;
}
.sb-ticket.processing {
    border-color: #3b82f6;
    background: #0f1f3d;
    animation: pulse-border 2s infinite;
}
.sb-ticket.done-ok  { border-color: #22c55e; background: #0a1f12; }
.sb-ticket.done-err { border-color: #ef4444; background: #1f0a0a; }
.sb-ticket.done-esc { border-color: #f59e0b; background: #1f1a0a; }
.sb-ticket.pending  { opacity: 0.5; }

@keyframes pulse-border {
    0%, 100% { box-shadow: 0 0 0 0 rgba(59,130,246,0); }
    50%       { box-shadow: 0 0 0 4px rgba(59,130,246,0.15); }
}

.sb-id   { font-family: monospace; font-size: 12px; color: #667eea; font-weight: 700; }
.sb-tool { font-family: monospace; font-size: 11px; color: #38bdf8; }
.sb-status { font-size: 11px; }

/* RESULT CARDS */
.result-card {
    background: #0d1220;
    border: 1px solid #1e293b;
    border-radius: 14px;
    margin-bottom: 20px;
    overflow: hidden;
}
.result-header {
    padding: 18px 22px;
    background: #0f172a;
    border-bottom: 1px solid #1e293b;
    display: flex; align-items: center; justify-content: space-between;
}
.result-body { padding: 20px 22px; }

.step-line {
    display: flex; align-items: flex-start;
    gap: 12px; padding: 8px 0;
    border-bottom: 1px solid #0f172a;
}
.step-line:last-child { border-bottom: none; }
.step-icon { font-size: 16px; margin-top: 1px; flex-shrink: 0; }
.step-content { flex: 1; }
.step-tool { font-family: monospace; font-size: 13px; font-weight: 600; color: #67e8f9; }
.step-detail { font-size: 12px; color: #475569; margin-top: 2px; }
.step-output { font-size: 12px; color: #64748b; font-family: monospace;
               background: #080b14; border-radius: 6px; padding: 6px 10px;
               margin-top: 6px; max-height: 80px; overflow-y: auto; }

.reply-box {
    background: linear-gradient(135deg, #0f2027, #1a2a3a);
    border: 1px solid #1e4a6e;
    border-radius: 12px;
    padding: 18px 20px;
    margin-top: 16px;
}
.reply-label { font-size: 12px; font-weight: 700; color: #38bdf8;
               text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; }
.reply-text { font-size: 14px; color: #cbd5e1; line-height: 1.7; white-space: pre-wrap; }

.outcome-pill {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 5px 14px; border-radius: 20px;
    font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;
}
.pill-resolved      { background: #052e16; color: #4ade80; border: 1px solid #166534; }
.pill-refund_issued { background: #052e16; color: #4ade80; border: 1px solid #166534; }
.pill-escalated     { background: #431407; color: #fb923c; border: 1px solid #9a3412; }
.pill-llm_error     { background: #450a0a; color: #f87171; border: 1px solid #991b1b; }
.pill-replied       { background: #0c1a4a; color: #93c5fd; border: 1px solid #1e40af; }
.pill-cancelled     { background: #0a2818; color: #6ee7b7; border: 1px solid #065f46; }

/* BUTTONS */
.run-btn {
    background: linear-gradient(135deg, #4f46e5, #7c3aed) !important;
    border: none !important; border-radius: 10px !important;
    font-weight: 700 !important; font-size: 16px !important;
    padding: 14px !important; width: 100% !important;
    transition: opacity 0.2s !important;
}
.run-btn:hover { opacity: 0.9 !important; }

/* STAT PILL */
.stat-row { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px; }
.stat-pill {
    background: #0d1220; border: 1px solid #1e293b;
    border-radius: 10px; padding: 10px 18px; text-align: center;
}
.stat-num  { font-size: 24px; font-weight: 700; }
.stat-lbl  { font-size: 11px; color: #475569; text-transform: uppercase; letter-spacing: 0.5px; }

div[data-testid="stSidebar"] { background: #080b14 !important; border-right: 1px solid #1e293b; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SESSION STATE INIT
# ─────────────────────────────────────────────
if "selected_tickets" not in st.session_state:
    st.session_state.selected_tickets = []
if "running" not in st.session_state:
    st.session_state.running = False
if "results" not in st.session_state:
    st.session_state.results = {}
if "progress" not in st.session_state:
    st.session_state.progress = {}
if "run_complete" not in st.session_state:
    st.session_state.run_complete = False


# ─────────────────────────────────────────────
# DATA LOADERS
# ─────────────────────────────────────────────
@st.cache_data
def load_tickets():
    with open("mocks/tickets.json") as f:
        return json.load(f)

@st.cache_data
def load_customers():
    with open("mocks/customers.json") as f:
        return {c["email"]: c for c in json.load(f)}

@st.cache_data
def load_orders():
    with open("mocks/orders.json") as f:
        return {o["order_id"]: o for o in json.load(f)}

def load_progress():
    try:
        with open("live_progress.json") as f:
            return json.load(f)
    except:
        return {"tickets": {}}

def load_results():
    try:
        with open("audit_log.json") as f:
            data = json.load(f)
            return {t["ticket_id"]: t for t in data}
    except:
        return {}

def load_results_for(selected_ids):
    """Only return results for tickets in current run — never show stale data."""
    all_results = load_results()
    return {tid: all_results[tid] for tid in selected_ids if tid in all_results}


# ─────────────────────────────────────────────
# AGENT RUNNER (background thread)
# ─────────────────────────────────────────────
def run_agent_for_tickets(selected_ids):
    """Run agent in background thread for selected tickets."""
    import sys
    sys.path.insert(0, os.getcwd())

    # DELETE old files so stale results never show during new run
    if os.path.exists("audit_log.json"):
        os.remove("audit_log.json")
    if os.path.exists("live_progress.json"):
        os.remove("live_progress.json")

    from agent.agent_loop import process_all_tickets
    from logger.audit_logger import save_audit_log, _audit_log

    # Load only selected tickets
    with open("mocks/tickets.json") as f:
        all_tickets = json.load(f)
    tickets = [t for t in all_tickets if t["ticket_id"] in selected_ids]

    # Clear old logs
    _audit_log.clear()

    # Write fresh progress with all tickets as pending
    prog = {"tickets": {}, "started_at": datetime.utcnow().isoformat()}
    for tid in selected_ids:
        prog["tickets"][tid] = {"status": "pending", "last_tool": "", "outcome": ""}

    with open("live_progress.json", "w") as f:
        json.dump(prog, f)

    # Run
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(process_all_tickets(tickets))
    loop.close()

    # Save audit log
    save_audit_log("audit_log.json")


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def outcome_pill(outcome):
    emojis = {
        "resolved": "✅", "refund_issued": "💸",
        "order_cancelled": "🚫", "replied": "💬",
        "escalated": "⬆️", "llm_error": "❌",
        "dead_letter": "💀", "processing": "⚙️",
        "pending": "⏳",
    }
    css_class = f"pill-{outcome}" if outcome in [
        "resolved","refund_issued","escalated","llm_error","replied","cancelled"
    ] else "pill-replied"
    emoji = emojis.get(outcome, "❓")
    return f'<span class="outcome-pill {css_class}">{emoji} {outcome.replace("_"," ")}</span>'

def sidebar_class(status, outcome):
    if status == "processing": return "processing"
    if status == "done":
        if outcome in ("resolved","refund_issued","order_cancelled","replied"): return "done-ok"
        if outcome == "escalated": return "done-esc"
        return "done-err"
    return "pending"

CATEGORY_ICONS = {
    "refund": "💰", "return": "📦", "cancellation": "🚫",
    "exchange": "🔄", "warranty_or_defect": "🔧",
    "shipping": "🚚", "policy_question": "📋", "ambiguous": "❓"
}

URGENCY_ICONS = {"high": "🔴", "medium": "🟡", "low": "🟢"}


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='padding:16px 0 8px'>
        <div style='font-size:11px;color:#475569;text-transform:uppercase;
                    letter-spacing:1px;font-weight:700;margin-bottom:12px'>
            Live Progress
        </div>
    </div>""", unsafe_allow_html=True)

    sidebar_placeholder = st.empty()

    st.markdown("---")
    st.markdown("""
    <div style='font-size:11px;color:#475569;text-transform:uppercase;
                letter-spacing:1px;font-weight:700;margin-bottom:10px'>
        Legend
    </div>
    <div style='font-size:12px;color:#64748b;line-height:2'>
        ⚙️ Processing<br>
        ✅ Resolved<br>
        ⬆️ Escalated<br>
        ❌ Error<br>
        ⏳ Pending
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# MAIN CONTENT
# ─────────────────────────────────────────────

# HERO
st.markdown("""
<div class="hero">
    <div class="hero-badge">🏆 Ksolves Agentic AI Hackathon 2026</div>
    <h1>ShopWave Autonomous Support Agent</h1>
    <p>Select tickets below, click Run Agent, and watch AI resolve each one in real time — tool calls, reasoning, and final replies.</p>
</div>
""", unsafe_allow_html=True)


# ─── TICKET SELECTION PHASE ───
if not st.session_state.running and not st.session_state.run_complete:

    all_tickets  = load_tickets()
    customers    = load_customers()

    # Filter controls
    col_f1, col_f2, col_f3, col_f4 = st.columns([2, 2, 2, 1])
    with col_f1:
        cat_filter = st.selectbox("Category", ["All","refund","return","cancellation",
            "exchange","warranty_or_defect","shipping","policy_question","ambiguous"])
    with col_f2:
        urg_filter = st.selectbox("Urgency", ["All","high","medium","low"])
    with col_f3:
        src_filter = st.selectbox("Source", ["All","email","ticket_queue"])
    with col_f4:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Select All", use_container_width=True):
            st.session_state.selected_tickets = [t["ticket_id"] for t in all_tickets]
            st.rerun()

    st.markdown("---")
    st.markdown(f"### 🎫 Choose Tickets to Process")
    st.caption(f"{len(st.session_state.selected_tickets)} of {len(all_tickets)} selected")

    # Render ticket cards with checkboxes
    for ticket in all_tickets:
        # Determine category from subject/body for display
        body  = (ticket["body"] + ticket["subject"]).lower()
        if any(w in body for w in ["refund","money back"]): cat = "refund"
        elif any(w in body for w in ["return","send back"]): cat = "return"
        elif "cancel" in body: cat = "cancellation"
        elif any(w in body for w in ["exchange","wrong size","wrong colour","wrong item"]): cat = "exchange"
        elif any(w in body for w in ["defect","broken","stopped working","not working","cracked"]): cat = "warranty_or_defect"
        elif any(w in body for w in ["where is","tracking","shipping","transit"]): cat = "shipping"
        elif any(w in body for w in ["policy","how do","what is your"]): cat = "policy_question"
        else: cat = "ambiguous"

        urgency = "high" if any(w in body for w in ["lawyer","dispute","bank","urgent","immediately"]) else \
                  "medium" if ticket.get("tier",1) >= 2 else "low"

        # Apply filters
        if cat_filter != "All" and cat != cat_filter: continue
        if urg_filter != "All" and urgency != urg_filter: continue
        if src_filter != "All" and ticket["source"] != src_filter: continue

        tid        = ticket["ticket_id"]
        is_selected = tid in st.session_state.selected_tickets
        customer   = customers.get(ticket["customer_email"], {})
        cust_name  = customer.get("name", ticket["customer_email"])
        cust_tier  = customer.get("tier", "standard").upper()

        col_cb, col_card = st.columns([0.5, 11])
        with col_cb:
            checked = st.checkbox("", value=is_selected, key=f"cb_{tid}")
            if checked and tid not in st.session_state.selected_tickets:
                st.session_state.selected_tickets.append(tid)
                st.rerun()
            elif not checked and tid in st.session_state.selected_tickets:
                st.session_state.selected_tickets.remove(tid)
                st.rerun()

        with col_card:
            tier_color = {"VIP": "#f59e0b", "PREMIUM": "#a78bfa", "STANDARD": "#64748b"}.get(cust_tier, "#64748b")
            st.markdown(f"""
            <div class="ticket-card {'selected' if is_selected else ''}">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
                    <span class="ticket-id">{tid}</span>
                    <div style="display:flex;gap:6px;align-items:center">
                        <span style="font-size:11px;color:{tier_color};font-weight:700">{cust_tier}</span>
                        <span class="badge badge-{cat}">{CATEGORY_ICONS.get(cat,'')} {cat.replace('_',' ')}</span>
                        <span class="urgency-{urgency}">{URGENCY_ICONS.get(urgency,'')} {urgency}</span>
                    </div>
                </div>
                <div class="ticket-subject">{ticket['subject']}</div>
                <div style="font-size:12px;color:#334155;margin:4px 0">
                    👤 {cust_name} &nbsp;·&nbsp; 📧 {ticket['source']}
                </div>
                <div class="ticket-body-preview">{ticket['body'][:120]}...</div>
            </div>
            """, unsafe_allow_html=True)

    # RUN BUTTON
    st.markdown("---")
    n = len(st.session_state.selected_tickets)
    if n == 0:
        st.warning("Select at least one ticket to continue.")
    else:
        col_run1, col_run2, col_run3 = st.columns([2, 3, 2])
        with col_run2:
            if st.button(f"🚀 Run Agent on {n} ticket{'s' if n>1 else ''}", 
                        type="primary", use_container_width=True):
                # Start agent in background thread
                t = threading.Thread(
                    target=run_agent_for_tickets,
                    args=(st.session_state.selected_tickets.copy(),),
                    daemon=True
                )
                t.start()
                st.session_state.running = True
                st.session_state.results = {}
                st.rerun()


# ─── LIVE PROGRESS PHASE ───
elif st.session_state.running:

    selected_ids = st.session_state.selected_tickets
    all_tickets  = load_tickets()
    ticket_map   = {t["ticket_id"]: t for t in all_tickets}

    # Header
    st.markdown(f"""
    <div style='background:#0f172a;border:1px solid #1e3a5f;border-radius:12px;
                padding:20px 28px;margin-bottom:24px;display:flex;
                align-items:center;justify-content:space-between'>
        <div>
            <div style='font-size:20px;font-weight:700;color:#e2e8f0'>
                ⚙️ Agent Running...
            </div>
            <div style='font-size:13px;color:#475569;margin-top:4px'>
                Processing {len(selected_ids)} tickets concurrently with GPT-4o
            </div>
        </div>
        <div style='font-family:monospace;font-size:13px;color:#38bdf8'>
            ReAct Loop · Tool Calling · Async
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Live polling loop
    results_placeholder = st.empty()
    done_placeholder    = st.empty()

    poll_count = 0
    while True:
        poll_count += 1
        progress = load_progress()
        results  = load_results_for(selected_ids)
        ticket_progress = progress.get("tickets", {})

        # ── SIDEBAR UPDATE (pure Streamlit, no HTML) ──
        done_count = 0
        with sidebar_placeholder.container():
            for tid in selected_ids:
                prog      = ticket_progress.get(tid, {})
                status    = prog.get("status", "pending")
                last_tool = prog.get("last_tool", "")
                outcome   = prog.get("outcome", "")
                ticket    = ticket_map.get(tid, {})
                subject   = ticket.get("subject", "")[:40]

                if status == "done":
                    done_count += 1
                    if outcome in ("resolved","refund_issued","order_cancelled","replied"):
                        st.success(f"✅ **{tid}** — {outcome.replace('_',' ')}")
                    elif outcome == "escalated":
                        st.warning(f"⬆️ **{tid}** — escalated")
                    else:
                        st.error(f"❌ **{tid}** — {outcome.replace('_',' ')}")
                elif status == "processing":
                    tool_str = f"`{last_tool}()`" if last_tool else "reasoning..."
                    st.info(f"⚙️ **{tid}** — {tool_str}")
                else:
                    st.markdown(f"⏳ {tid} — *waiting*")

        # ── MAIN: show results as they come in ──
        with results_placeholder.container():
            completed = [tid for tid in selected_ids if ticket_progress.get(tid, {}).get("status") == "done"]
            pending   = [tid for tid in selected_ids if ticket_progress.get(tid, {}).get("status") != "done"]

            if completed:
                st.markdown(f"### ✅ Completed ({len(completed)}/{len(selected_ids)})")
                for tid in completed:
                    if tid not in results:
                        continue
                    result = results[tid]
                    ticket = ticket_map.get(tid, {})
                    outcome = result.get("outcome", {}).get("result", "unknown")
                    cls    = result.get("classification", {})
                    tool_calls = result.get("tool_calls", [])
                    reasoning  = result.get("reasoning_chain", [])
                    failures   = result.get("failures_encountered", [])

                    # Customer name from tool calls
                    cust_name = next((
                        tc.get("output",{}).get("name","Unknown")
                        for tc in tool_calls if tc.get("tool") == "get_customer"
                    ), "Unknown")

                    with st.expander(
                        f"{'✅' if outcome in ('resolved','refund_issued') else '⬆️' if outcome=='escalated' else '❌'} "
                        f"**{tid}** — {ticket.get('subject','')[:55]}",
                        expanded=True
                    ):
                        # Header row
                        col1, col2, col3 = st.columns([3,3,2])
                        col1.markdown(f"**Customer:** {cust_name}")
                        col2.markdown(f"**Category:** {cls.get('category','—')}")
                        col3.markdown(outcome_pill(outcome), unsafe_allow_html=True)

                        # Original ticket
                        st.markdown(f"""
                        <div style='background:#080b14;border:1px solid #1e293b;border-radius:8px;
                                    padding:12px 16px;margin:12px 0;font-size:13px;color:#64748b'>
                            📧 <b style='color:#94a3b8'>Original message:</b><br>
                            <span style='color:#cbd5e1'>{ticket.get('body','')}</span>
                        </div>
                        """, unsafe_allow_html=True)

                        # Steps taken
                        st.markdown("#### 🔧 Steps Taken")
                        for tc in tool_calls:
                            tool   = tc.get("tool","")
                            status = tc.get("status","")
                            inp    = tc.get("input",{})
                            out    = tc.get("output",{})
                            ok     = status == "success" and not out.get("error")

                            icon = {"get_customer":"👤","get_order":"📦","get_product":"🏷️",
                                    "search_knowledge_base":"📚","check_refund_eligibility":"🔍",
                                    "issue_refund":"💸","cancel_order":"🚫","send_reply":"📨",
                                    "escalate":"⬆️"}.get(tool,"🔧")

                            inp_str = ", ".join(f"{k}={v}" for k,v in inp.items())
                            out_str = json.dumps(out, indent=2)[:300]
                            status_str = "✅ success" if ok else "⚠️ " + str(out.get("error",""))[:60]

                            st.markdown(f"""
                            <div class="step-line">
                                <div class="step-icon">{icon}</div>
                                <div class="step-content">
                                    <div class="step-tool">{tool}({inp_str})</div>
                                    <div class="step-detail">→ {status_str}</div>
                                    <div class="step-output">{out_str}</div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

                        # Failures
                        if failures:
                            st.markdown("#### ⚠️ Failures & Recovery")
                            for f in failures:
                                err = f.get("error","")[:150]
                                rec = f.get("recovery","")
                                if "429" in err or "timeout" in err.lower():
                                    st.warning(f"🔄 **{err[:80]}** → Recovery: {rec}")
                                else:
                                    st.error(f"❌ **{err[:80]}** → Recovery: {rec}")

                        # Final reply
                        final_msg = ""
                        if reasoning:
                            final_msg = reasoning[-1]
                        elif outcome == "escalated":
                            esc = next((tc for tc in tool_calls if tc.get("tool") == "escalate"), None)
                            if esc:
                                final_msg = f"[Escalated to human agent]\n\nSummary: {esc.get('input',{}).get('summary','')}"
                        elif result.get("outcome",{}).get("details",{}).get("final_message"):
                            final_msg = result["outcome"]["details"]["final_message"]

                        if final_msg:
                            st.markdown(f"""
                            <div class="reply-box">
                                <div class="reply-label">📨 Reply sent to customer</div>
                                <div class="reply-text">{final_msg}</div>
                            </div>
                            """, unsafe_allow_html=True)

            if pending:
                st.markdown(f"### ⏳ In Queue ({len(pending)} remaining)")
                for tid in pending:
                    prog = ticket_progress.get(tid, {})
                    status = prog.get("status","pending")
                    ticket = ticket_map.get(tid,{})
                    if status == "processing":
                        tool = prog.get("last_tool","")
                        st.markdown(f"""
                        <div style='background:#0f1f3d;border:1px solid #3b82f6;border-radius:10px;
                                    padding:12px 16px;margin-bottom:8px'>
                            <span style='color:#667eea;font-family:monospace;font-weight:700'>{tid}</span>
                            <span style='color:#64748b;font-size:12px'> · {ticket.get('subject','')[:50]}</span><br>
                            <span style='color:#38bdf8;font-family:monospace;font-size:12px'>
                                ⚙️ Running: {tool}()...
                            </span>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style='background:#0d1220;border:1px solid #1e293b;border-radius:10px;
                                    padding:12px 16px;margin-bottom:8px;opacity:0.6'>
                            <span style='color:#667eea;font-family:monospace;font-weight:700'>{tid}</span>
                            <span style='color:#475569;font-size:12px'> · {ticket.get('subject','')[:50]}</span>
                            <span style='color:#334155;font-size:11px'> ⏳ waiting</span>
                        </div>
                        """, unsafe_allow_html=True)

        # Check if all done
        all_done = all(
            ticket_progress.get(tid, {}).get("status") == "done"
            for tid in selected_ids
        )

        if all_done:
            st.session_state.running = False
            st.session_state.run_complete = True
            # Save to session state so each user has their own copy
            st.session_state.results = load_results_for(selected_ids)
            st.rerun()

        time.sleep(2)
        st.rerun()


# ─── RESULTS PHASE (complete) ───
elif st.session_state.run_complete:

    selected_ids = st.session_state.selected_tickets
    all_tickets  = load_tickets()
    ticket_map   = {t["ticket_id"]: t for t in all_tickets}
    # Use session state first — avoids file conflicts between users
    results = st.session_state.results if st.session_state.results else load_results_for(selected_ids)

    # Summary stats
    done_tickets = [results[tid] for tid in selected_ids if tid in results]
    resolved  = sum(1 for t in done_tickets if t.get("outcome",{}).get("result") in ("resolved","refund_issued","order_cancelled","replied"))
    escalated = sum(1 for t in done_tickets if any(c.get("tool")=="escalate" for c in t.get("tool_calls",[])))
    errors    = sum(1 for t in done_tickets if t.get("outcome",{}).get("result")=="llm_error")
    total_tools = sum(t.get("total_tool_calls",0) for t in done_tickets)

    st.markdown(f"""
    <div style='background:linear-gradient(135deg,#052e16,#0a1f12);
                border:1px solid #166534;border-radius:14px;
                padding:24px 32px;margin-bottom:28px'>
        <div style='font-size:22px;font-weight:700;color:#4ade80;margin-bottom:4px'>
            🎉 All {len(selected_ids)} tickets processed!
        </div>
        <div style='display:flex;gap:24px;margin-top:16px'>
            <div><div style='font-size:28px;font-weight:700;color:#4ade80'>{resolved}</div>
                 <div style='font-size:12px;color:#166534'>Resolved</div></div>
            <div><div style='font-size:28px;font-weight:700;color:#fb923c'>{escalated}</div>
                 <div style='font-size:12px;color:#9a3412'>Escalated</div></div>
            <div><div style='font-size:28px;font-weight:700;color:#f87171'>{errors}</div>
                 <div style='font-size:12px;color:#991b1b'>Errors</div></div>
            <div><div style='font-size:28px;font-weight:700;color:#38bdf8'>{total_tools}</div>
                 <div style='font-size:12px;color:#0369a1'>Tool Calls</div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar final — pure Streamlit
    with sidebar_placeholder.container():
        for tid in selected_ids:
            result  = results.get(tid, {})
            outcome = result.get("outcome", {}).get("result", "unknown")
            if outcome in ("resolved","refund_issued","order_cancelled","replied"):
                st.success(f"✅ **{tid}** — {outcome.replace('_',' ')}")
            elif outcome == "escalated":
                st.warning(f"⬆️ **{tid}** — escalated")
            else:
                st.error(f"❌ **{tid}** — {outcome.replace('_',' ')}")

    # Results + Download buttons
    col_h1, col_h2, col_h3, col_h4 = st.columns([3, 1, 1, 1])
    with col_h1:
        st.markdown("### 📋 All Results")
    with col_h2:
        if st.button("🔄 Run Again", use_container_width=True):
            st.session_state.run_complete = False
            st.session_state.running      = False
            st.session_state.selected_tickets = []
            st.session_state.results = {}
            st.rerun()
    with col_h3:
        if os.path.exists("audit_log.json"):
            with open("audit_log.json", "rb") as f:
                st.download_button(
                    label="📥 Audit Log",
                    data=f.read(),
                    file_name="audit_log.json",
                    mime="application/json",
                    use_container_width=True
                )
    with col_h4:
        if os.path.exists("agent.log"):
            with open("agent.log", "rb") as f:
                st.download_button(
                    label="📥 Agent Log",
                    data=f.read(),
                    file_name="agent.log",
                    mime="text/plain",
                    use_container_width=True
                )
        else:
            log_lines = f"ShopWave Agent Log\nGenerated: {datetime.utcnow().isoformat()}\n"
            log_lines += f"Tickets: {len(selected_ids)} | Resolved: {resolved} | Escalated: {escalated} | Errors: {errors}\n\n"
            for tid in selected_ids:
                r = results.get(tid, {})
                outcome = r.get("outcome", {}).get("result", "unknown")
                log_lines += f"[INFO] {tid} outcome={outcome} tool_calls={r.get('total_tool_calls',0)}\n"
                for fi in r.get("failures_encountered", []):
                    log_lines += f"[WARNING] {tid} {fi.get('error','')[:80]}\n"
            st.download_button(
                label="📥 Agent Log",
                data=log_lines,
                file_name="agent.log",
                mime="text/plain",
                use_container_width=True
            )

    for tid in selected_ids:
        if tid not in results:
            continue
        result     = results[tid]
        ticket     = ticket_map.get(tid, {})
        outcome    = result.get("outcome", {}).get("result", "unknown")
        cls        = result.get("classification", {})
        tool_calls = result.get("tool_calls", [])
        reasoning  = result.get("reasoning_chain", [])
        failures   = result.get("failures_encountered", [])

        cust_name = next((
            tc.get("output",{}).get("name","Unknown")
            for tc in tool_calls if tc.get("tool") == "get_customer"
        ), "Unknown")

        emoji = "✅" if outcome in ("resolved","refund_issued","order_cancelled","replied") \
                else "⬆️" if outcome=="escalated" else "❌"

        with st.expander(f"{emoji} **{tid}** — {ticket.get('subject','')[:60]}", expanded=False):
            col1, col2, col3 = st.columns([3,3,2])
            col1.markdown(f"**Customer:** {cust_name}")
            col2.markdown(f"**Category:** {cls.get('category','—')} | **Urgency:** {cls.get('urgency','—')}")
            col3.markdown(outcome_pill(outcome), unsafe_allow_html=True)

            st.markdown(f"""
            <div style='background:#080b14;border:1px solid #1e293b;border-radius:8px;
                        padding:12px 16px;margin:12px 0;font-size:13px'>
                📧 <b style='color:#94a3b8'>Original:</b>
                <span style='color:#cbd5e1'>{ticket.get('body','')}</span>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("**🔧 Steps taken:**")
            for tc in tool_calls:
                tool   = tc.get("tool","")
                inp    = tc.get("input",{})
                out    = tc.get("output",{})
                ok     = tc.get("status") == "success" and not out.get("error")
                icon   = {"get_customer":"👤","get_order":"📦","get_product":"🏷️",
                          "search_knowledge_base":"📚","check_refund_eligibility":"🔍",
                          "issue_refund":"💸","cancel_order":"🚫","send_reply":"📨",
                          "escalate":"⬆️"}.get(tool,"🔧")
                inp_str = ", ".join(f"{k}={v}" for k,v in inp.items())
                status_str = "✅ success" if ok else f"⚠️ {str(out.get('error',''))[:80]}"
                st.markdown(f"""
                <div class="step-line">
                    <span class="step-icon">{icon}</span>
                    <span class="step-tool">{tool}({inp_str})</span>
                    &nbsp;<span class="step-detail">→ {status_str}</span>
                </div>""", unsafe_allow_html=True)

            if failures:
                for f in failures:
                    err = f.get("error","")[:120]
                    if "429" in err or "timeout" in err.lower():
                        st.warning(f"🔄 {err} → {f.get('recovery','')}")

            # Final reply
            final_msg = ""
            if reasoning:
                final_msg = reasoning[-1]
            elif result.get("outcome",{}).get("details",{}).get("final_message"):
                final_msg = result["outcome"]["details"]["final_message"]
            elif outcome == "escalated":
                esc = next((tc for tc in tool_calls if tc.get("tool")=="escalate"), None)
                if esc:
                    final_msg = f"Escalated to human.\n\n{esc.get('input',{}).get('summary','')}"

            if final_msg:
                st.markdown(f"""
                <div class="reply-box">
                    <div class="reply-label">📨 Final Reply to Customer</div>
                    <div class="reply-text">{final_msg}</div>
                </div>
                """, unsafe_allow_html=True)