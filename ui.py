"""Provenance Guard — Gradio frontend (extra feature).

A visual demo of every backend feature. It calls the LIVE Flask API over HTTP
(server-to-server, so no CORS), which means it exercises the real endpoints —
including rate limiting and the audit log — rather than re-implementing anything.

Run BOTH processes:
    python app.py       # backend  (http://localhost:5000)
    python ui.py        # this UI   (http://localhost:7860)

If the backend runs on a different port (e.g. PORT=5001 to avoid macOS AirPlay),
point the UI at it:  API_BASE=http://localhost:5001 python ui.py
"""

import os

import gradio as gr
import requests

API_BASE = os.getenv("API_BASE", "http://localhost:5000")
TIMEOUT = 30

# Per-verdict presentation (colors + icon + title), matching labels.py.
VERDICT_STYLE = {
    "likely-ai": {
        "color": "#b45309", "bg": "#fffbeb", "border": "#f59e0b",
        "icon": "🤖", "title": "Likely AI-generated",
    },
    "likely-human": {
        "color": "#15803d", "bg": "#f0fdf4", "border": "#22c55e",
        "icon": "✍️", "title": "Likely written by a human",
    },
    "uncertain": {
        "color": "#475569", "bg": "#f8fafc", "border": "#94a3b8",
        "icon": "❓", "title": "Attribution uncertain",
    },
}

# --- Example texts for the quick-fill buttons ---
EX_AI = (
    "The global economy in 2026 is being reshaped by rapid technological innovation, changing "
    "labor markets, and evolving international trade relationships. Artificial intelligence and "
    "automation are transforming industries by increasing productivity while also creating "
    "demand for new skills. Many countries are investing in renewable energy, digital "
    "infrastructure, and advanced manufacturing to strengthen long-term economic growth. At the "
    "same time, businesses and consumers continue to adapt to inflation, shifting interest "
    "rates, and changing supply chains."
)
EX_HUMAN = (
    "British Cycling changed one day in 2003. The organization had recently hired Dave "
    "Brailsford as its new performance director. At the time, professional cyclists in Great "
    "Britain had endured nearly one hundred years of mediocrity. Since 1908, British riders had "
    "won just a single gold medal at the Olympic Games, and they had fared even worse in the "
    "Tour de France. In 110 years, no British cyclist had ever won the event. In fact, one of "
    "the top bike manufacturers in Europe refused to sell bikes to the team, afraid it would "
    "hurt sales if other pros saw the Brits using their gear."
)
EX_SHORT = "The meeting is scheduled for Tuesday at noon. Please bring your reports."


# --------------------------------------------------------------------------- #
# HTML builders
# --------------------------------------------------------------------------- #

def _bar(label: str, value01: float, color: str, note: str = "") -> str:
    pct = round(max(0.0, min(1.0, value01)) * 100)
    return (
        f'<div style="margin:8px 0;">'
        f'  <div style="display:flex;justify-content:space-between;font-size:0.85em;color:#374151;">'
        f'    <span>{label}</span><span>{value01:.2f}{note}</span>'
        f'  </div>'
        f'  <div style="background:#e5e7eb;border-radius:6px;height:12px;overflow:hidden;">'
        f'    <div style="width:{pct}%;background:{color};height:100%;"></div>'
        f'  </div>'
        f'</div>'
    )


def _warning(msg: str) -> str:
    return (
        f'<div style="border-left:6px solid #dc2626;background:#fef2f2;padding:14px 18px;'
        f'border-radius:0 10px 10px 0;color:#991b1b;">{msg}</div>'
    )


def _http_error(resp) -> str:
    """Turn a non-OK backend response into a helpful warning."""
    if resp.status_code == 403:
        return _warning(
            f"Got <b>HTTP 403</b> from <code>{API_BASE}</code>. On macOS this usually means the "
            "UI is hitting <b>AirPlay Receiver</b> on port 5000, not the backend. Fix: run the "
            "backend on another port and point the UI at it — "
            "<code>PORT=5001 python app.py</code>, then "
            "<code>API_BASE=http://localhost:5001 python ui.py</code> "
            "(or disable AirPlay Receiver to free port 5000)."
        )
    return _warning(f"Backend error {resp.status_code}: {resp.text[:200]}")


def _build_result_html(data: dict) -> str:
    attribution = data.get("attribution", "uncertain")
    style = VERDICT_STYLE.get(attribution, VERDICT_STYLE["uncertain"])
    confidence = data.get("confidence", 0.0)
    label_text = data.get("label", "")
    signals = data.get("signals", {})
    llm = signals.get("llm", {})
    sty = signals.get("stylometry", {})
    metrics = sty.get("metrics", {})
    scoring = data.get("scoring", {})

    # Label card
    card = (
        f'<div style="border-left:6px solid {style["border"]};background:{style["bg"]};'
        f'padding:16px 20px;border-radius:0 10px 10px 0;margin-bottom:14px;">'
        f'  <div style="font-size:1.25em;font-weight:800;color:{style["color"]};">'
        f'{style["icon"]} {style["title"]}</div>'
        f'  <div style="margin-top:8px;color:#374151;line-height:1.5;">{label_text}</div>'
        f'</div>'
    )

    # Confidence meter
    conf_block = (
        f'<div style="margin-bottom:14px;">'
        f'  <div style="font-weight:700;color:#111827;margin-bottom:2px;">Confidence in this verdict</div>'
        f'  {_bar("certainty", confidence, style["border"])}'
        f'  <div style="font-size:0.78em;color:#6b7280;">0.5 = genuinely unsure · higher = more certain in the stated verdict</div>'
        f'</div>'
    )

    # Signals breakdown
    signals_block = (
        f'<div style="border:1px solid #e5e7eb;border-radius:10px;padding:14px 16px;">'
        f'  <div style="font-weight:700;color:#111827;margin-bottom:6px;">Two independent signals</div>'
        f'  {_bar("Signal 1 — LLM (semantic)", llm.get("llm_score", 0.0), "#6366f1", " (0=human,1=AI)")}'
        f'  <div style="font-size:0.8em;color:#6b7280;margin:2px 0 8px;">reason: {llm.get("reason", "—")}</div>'
        f'  {_bar("Signal 2 — Stylometry (structural)", sty.get("sty_score", 0.0), "#0d9488", " (0=human,1=AI)")}'
        f'  <div style="font-size:0.8em;color:#6b7280;margin-top:2px;">'
        f'words={metrics.get("word_count","?")} · sentence-length CV={metrics.get("sentence_len_cv","?")} · '
        f'distinct punctuation={metrics.get("distinct_punctuation","?")}</div>'
        f'  <hr style="border:none;border-top:1px solid #f0f0f0;margin:10px 0;">'
        f'  <div style="font-size:0.82em;color:#374151;">'
        f'combined p_ai={scoring.get("p_ai","?")} · agreement={scoring.get("agreement","?")} · '
        f'direction={scoring.get("direction","?")}'
        f'{" · text too short → capped" if scoring.get("too_short") else ""}</div>'
        f'</div>'
    )

    return card + conf_block + signals_block


def _build_log_html(entries: list) -> str:
    if not entries:
        return '<div style="color:#6b7280;font-style:italic;">No entries yet — analyze something first.</div>'

    head = (
        '<tr style="background:#f3f4f6;text-align:left;">'
        + "".join(
            f'<th style="padding:6px 10px;font-size:0.8em;">{h}</th>'
            for h in ["time (UTC)", "event", "content_id", "attribution", "conf", "llm", "sty", "status", "appeal_reasoning"]
        )
        + "</tr>"
    )
    rows = []
    for e in entries:
        is_appeal = e.get("event") == "appeal"
        bg = "#fffbeb" if is_appeal else "#ffffff"
        ts = (e.get("timestamp") or "")[11:23]  # HH:MM:SS.mmm
        cid = (e.get("content_id") or "")[:8]
        cells = [
            ts,
            e.get("event", ""),
            cid,
            e.get("attribution", ""),
            e.get("confidence", ""),
            e.get("llm_score", ""),
            e.get("sty_score", ""),
            e.get("status", ""),
            (e.get("appeal_reasoning") or "")[:60],
        ]
        rows.append(
            f'<tr style="background:{bg};border-bottom:1px solid #f0f0f0;">'
            + "".join(f'<td style="padding:6px 10px;font-size:0.82em;">{c}</td>' for c in cells)
            + "</tr>"
        )
    return (
        '<div style="overflow-x:auto;">'
        f'<table style="border-collapse:collapse;width:100%;min-width:820px;">{head}{"".join(rows)}</table>'
        '</div>'
        '<div style="font-size:0.78em;color:#6b7280;margin-top:6px;">'
        'Amber rows are appeal events (they carry the original decision alongside the reasoning).</div>'
    )


# --------------------------------------------------------------------------- #
# API calls (Gradio event handlers)
# --------------------------------------------------------------------------- #

def analyze(text, creator_id):
    """POST /submit and render the result. Returns (result_html, cid_md, cid_state)."""
    if not text or not text.strip():
        return _warning("Please enter some text to analyze."), "", ""
    try:
        resp = requests.post(
            f"{API_BASE}/submit",
            json={"text": text, "creator_id": creator_id or None},
            timeout=TIMEOUT,
        )
    except requests.exceptions.RequestException:
        return _warning(f"Cannot reach the backend at {API_BASE}. Is <code>python app.py</code> running?"), "", ""

    if resp.status_code == 429:
        body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        return _warning(
            "🚦 <b>Rate limit reached.</b> " + body.get("error", "Too many requests.")
            + f" (limit: {body.get('limit', '5/min')}). This is the rate limiter working — wait a bit and retry."
        ), "", ""
    if resp.status_code != 200:
        return _http_error(resp), "", ""

    data = resp.json()
    cid = data.get("content_id", "")
    cid_md = f"**content_id:** `{cid}` · status: `{data.get('status','')}`"
    return _build_result_html(data), cid_md, cid


def submit_appeal(content_id, reasoning):
    """POST /appeal for the last-analyzed content_id."""
    if not content_id:
        return _warning("Analyze a piece of text first — then you can appeal its result.")
    if not reasoning or not reasoning.strip():
        return _warning("Please explain why you believe the classification is wrong.")
    try:
        resp = requests.post(
            f"{API_BASE}/appeal",
            json={"content_id": content_id, "creator_reasoning": reasoning},
            timeout=TIMEOUT,
        )
    except requests.exceptions.RequestException:
        return _warning(f"Cannot reach the backend at {API_BASE}. Is <code>python app.py</code> running?")

    if resp.status_code == 404:
        return _warning("No submission found for that content_id.")
    if resp.status_code != 200:
        return _http_error(resp)

    data = resp.json()
    return (
        f'<div style="border-left:6px solid #2563eb;background:#eff6ff;padding:14px 18px;'
        f'border-radius:0 10px 10px 0;color:#1e3a8a;">'
        f'✅ {data.get("message", "Appeal received.")}<br>'
        f'<span style="font-size:0.85em;">appeal_id: <code>{data.get("appeal_id","")}</code> · '
        f'status: <b>{data.get("status","under_review")}</b></span></div>'
    )


def load_log():
    """GET /log and render the audit table."""
    try:
        resp = requests.get(f"{API_BASE}/log", timeout=TIMEOUT)
    except requests.exceptions.RequestException:
        return _warning(f"Cannot reach the backend at {API_BASE}. Is <code>python app.py</code> running?")
    if resp.status_code != 200:
        return _http_error(resp)
    return _build_log_html(resp.json().get("entries", []))


# --------------------------------------------------------------------------- #
# Layout
# --------------------------------------------------------------------------- #

THEME = gr.themes.Soft(primary_hue="indigo", secondary_hue="slate")

with gr.Blocks(title="Provenance Guard") as demo:
    gr.Markdown(
        "# 🛡️ Provenance Guard\n"
        "Was this text written by a **human** or generated by **AI**? This UI calls the live "
        "Provenance Guard API — showing the multi-signal verdict, confidence, transparency "
        "label, appeals, rate limiting, and the audit log."
    )

    content_id_state = gr.State("")

    with gr.Tabs():
        with gr.Tab("Analyze"):
            with gr.Row():
                with gr.Column(scale=1):
                    text_in = gr.Textbox(
                        label="Content to analyze",
                        placeholder="Paste a poem, story excerpt, or blog post…",
                        lines=10,
                    )
                    creator_in = gr.Textbox(label="creator_id (optional)", placeholder="e.g. writer-anna")
                    analyze_btn = gr.Button("Analyze", variant="primary")
                    gr.Markdown("**Try an example:**")
                    with gr.Row():
                        ex_ai_btn = gr.Button("AI sample", size="sm")
                        ex_hu_btn = gr.Button("Human sample", size="sm")
                        ex_sh_btn = gr.Button("Short sample", size="sm")

                with gr.Column(scale=1):
                    result_html = gr.HTML(
                        value='<div style="color:#9ca3af;font-style:italic;">Result will appear here.</div>'
                    )
                    cid_display = gr.Markdown("")
                    with gr.Accordion("⚖️ Appeal this result", open=False):
                        gr.Markdown(
                            "Believe the classification is wrong? File an appeal — it sets the "
                            "status to `under_review` and logs your reasoning alongside the original decision."
                        )
                        reasoning_in = gr.Textbox(
                            label="Your reasoning",
                            placeholder="e.g. I wrote this myself from personal experience…",
                            lines=3,
                        )
                        appeal_btn = gr.Button("Submit Appeal")
                        appeal_result = gr.HTML("")

        with gr.Tab("Audit Log"):
            gr.Markdown("Every submission and appeal is recorded here (served by `GET /log`).")
            refresh_btn = gr.Button("🔄 Refresh log", variant="primary")
            log_html = gr.HTML("")

    # --- wiring ---
    analyze_btn.click(analyze, [text_in, creator_in], [result_html, cid_display, content_id_state])
    ex_ai_btn.click(lambda: EX_AI, None, text_in)
    ex_hu_btn.click(lambda: EX_HUMAN, None, text_in)
    ex_sh_btn.click(lambda: EX_SHORT, None, text_in)
    appeal_btn.click(submit_appeal, [content_id_state, reasoning_in], [appeal_result])
    refresh_btn.click(load_log, None, [log_html])
    demo.load(load_log, None, [log_html])  # populate the log on startup


if __name__ == "__main__":
    demo.launch(theme=THEME)
