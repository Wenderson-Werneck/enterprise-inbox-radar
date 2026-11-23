"""
One-command interactive web demo for Enterprise Inbox Radar & SLA Follow-Up Engine.
Run: python demo_app.py
"""
import json
import os
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from src.models import RawEmail
from src.engine import InboxRadarEngine

PORT = int(os.environ.get("PORT", "8005"))


def run_radar():
    engine = InboxRadarEngine(
        internal_domain="nordicmetals.example",
        client_directory=[
            ("Baltic Foundry AS", ["balticfoundry", "baltic"]),
            ("Scandia Steel AB", ["scandiasteel", "scandia"]),
            ("Port Terminal Ops", ["portterminal"]),
        ],
    )
    now = datetime(2026, 11, 23, 12, 0, tzinfo=timezone.utc)
    emails = [
        RawEmail(
            message_id="msg-101",
            sender_email="procurement@balticfoundry.example",
            sender_name="K. Tamm",
            recipient_emails=["sales@nordicmetals.example"],
            subject="RFQ: Electrolytic Manganese 150 ton — PO 4500987123",
            body_text="Hello team, confirming Pedido 4500987123 for 150 ton of Electrolytic Manganese. Please issue NF 89234 and confirm delivery slot.",
            received_timestamp=(now - timedelta(hours=18)).isoformat(),
        ),
        RawEmail(
            message_id="msg-102",
            sender_email="sales@nordicmetals.example",
            sender_name="Commercial Desk",
            recipient_emails=["buyers@scandiasteel.example"],
            subject="Re: Quotation — Ferro-Silicon 75% (80 ton)",
            body_text="Quote sent for 80 ton FeSi 75% DDP. Awaiting your PO confirmation.",
            received_timestamp=(now - timedelta(hours=36)).isoformat(),
        ),
        RawEmail(
            message_id="msg-103",
            sender_email="logistics@portterminal.example",
            sender_name="Port Dispatch",
            recipient_emails=["ops@nordicmetals.example"],
            subject="FWD: Scale Ticket Batch & NF 90412 — 120 ton release",
            body_text="Attached weighbridge batch for 120 ton and fiscal invoice NF 90412 for immediate clearance.",
            received_timestamp=(now - timedelta(hours=4)).isoformat(),
        ),
    ]
    threads = engine.process_mailbox(emails)
    return [t.model_dump() for t in threads]


HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Enterprise Inbox Radar — Live Demo</title>
  <style>
    :root { --bg:#0a0f1c; --card:#131c30; --surf:#0d1424; --bdr:#23314c; --txt:#f1f5f9; --mut:#94a3b8; --acc:#38bdf8; --grn:#10b981; --amb:#f59e0b; --red:#ef4444; }
    * { box-sizing:border-box; font-family:-apple-system,BlinkMacSystemFont,"Inter","Segoe UI",sans-serif; }
    body { margin:0; background:var(--bg); color:var(--txt); padding:24px; line-height:1.45; }
    .wrap { max-width:1280px; margin:0 auto; }
    header { display:flex; justify-content:space-between; align-items:center; padding-bottom:16px; margin-bottom:20px; border-bottom:1px solid var(--bdr); }
    h1 { margin:0; font-size:1.35rem; }
    .sub { margin:3px 0 0; font-size:0.84rem; color:var(--mut); }
    .pill { padding:5px 11px; border-radius:999px; font-size:0.75rem; font-weight:600; background:rgba(56,189,248,0.14); color:var(--acc); border:1px solid rgba(56,189,248,0.3); }
    .kpis { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:18px; }
    .kpi { background:var(--card); border:1px solid var(--bdr); border-radius:10px; padding:14px 16px; }
    .kpi span { font-size:0.74rem; text-transform:uppercase; color:var(--mut); }
    .kpi strong { display:block; font-size:1.35rem; margin-top:5px; }
    .card { background:var(--card); border:1px solid var(--bdr); border-radius:10px; padding:18px; }
    .card h2 { margin:0 0 12px; font-size:0.88rem; text-transform:uppercase; letter-spacing:0.06em; color:var(--mut); border-bottom:1px solid var(--bdr); padding-bottom:8px; }
    table { width:100%; border-collapse:collapse; font-size:0.84rem; }
    th, td { text-align:left; padding:10px; border-bottom:1px solid var(--bdr); vertical-align:top; }
    th { font-size:0.73rem; text-transform:uppercase; color:var(--mut); }
    .badge { display:inline-block; padding:3px 8px; border-radius:4px; font-size:0.72rem; font-weight:700; }
    .REPLY { background:rgba(239,68,68,0.16); color:var(--red); }
    .FOLLOW { background:rgba(245,158,11,0.16); color:var(--amb); }
    .DONE { background:rgba(16,185,129,0.16); color:var(--grn); }
    .chip { display:inline-block; padding:2px 7px; border-radius:4px; background:var(--surf); border:1px solid var(--bdr); font-family:ui-monospace,monospace; font-size:0.74rem; margin-right:4px; }
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <div>
        <h1>Enterprise Inbox Radar &amp; SLA Follow-Up Engine</h1>
        <p class="sub">Automated SAP PO &amp; NF-e Entity Extraction, Subject-Hash Thread Clustering &amp; Commercial SLA State Machine</p>
      </div>
      <span class="pill">Python · Pydantic v2 · Synthetic Inbox Feed</span>
    </header>
    <div class="kpis" id="kpis"></div>
    <div class="card">
      <h2>Triaged Commercial Threads &amp; Extracted Entities</h2>
      <table>
        <thead><tr><th>Normalized Subject &amp; Hash</th><th>Stage / SLA</th><th>Client Match</th><th>Extracted POs / NFs / Tonnage</th><th>Messages</th></tr></thead>
        <tbody id="body"></tbody>
      </table>
    </div>
  </div>
  <script>
    fetch("/api/data").then(r => r.json()).then(rows => {
      const needs = rows.filter(x => String(x.stage).includes("REPLY") || String(x.stage).includes("ACTION")).length;
      const pos = rows.reduce((a,r) => a + (r.entities?.purchase_orders?.length || 0), 0);
      const nfs = rows.reduce((a,r) => a + (r.entities?.invoice_numbers?.length || 0), 0);
      document.getElementById("kpis").innerHTML = `
        <div class="kpi"><span>Clustered Threads</span><strong>${rows.length}</strong></div>
        <div class="kpi"><span>Action / Reply Queue</span><strong style="color:var(--red)">${needs}</strong></div>
        <div class="kpi"><span>SAP POs Extracted</span><strong style="color:var(--acc)">${pos}</strong></div>
        <div class="kpi"><span>Fiscal Invoices (NF-e)</span><strong style="color:var(--grn)">${nfs}</strong></div>
      `;
      document.getElementById("body").innerHTML = rows.map(r => {
        const st = String(r.stage || "");
        const cls = st.includes("REPLY") || st.includes("ACTION") ? "REPLY" : st.includes("FOLLOW") ? "FOLLOW" : "DONE";
        const ent = r.entities || {};
        const chips = [
          ...(ent.purchase_orders || []).map(x => `<span class="chip">PO:${x}</span>`),
          ...(ent.invoice_numbers || []).map(x => `<span class="chip">NF:${x}</span>`),
          ...(ent.quantities_metric_tons || []).map(x => `<span class="chip">${x}t</span>`)
        ].join("") || "<span style='color:var(--mut)'>None</span>";
        return `<tr>
          <td><strong>${r.normalized_subject}</strong><br><small style="color:var(--mut)">hash: <code>${String(r.thread_hash||"").slice(0,12)}</code> · priority: ${r.priority}</small></td>
          <td><span class="badge ${cls}">${st}</span></td>
          <td>${ent.client_name || "External Counterparty"}</td>
          <td>${chips}</td>
          <td>${r.total_messages || 1}</td>
        </tr>`;
      }).join("");
    });
  </script>
</body>
</html>"""


class DemoHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML.encode("utf-8"))
        elif self.path == "/api/data":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(run_radar(), default=str).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


if __name__ == "__main__":
    print(f"Enterprise Inbox Radar Demo running at http://127.0.0.1:{PORT}")
    HTTPServer(("127.0.0.1", PORT), DemoHandler).serve_forever()
