"""
One-command interactive web demo for Enterprise Inbox Radar & SLA Follow-Up Engine.
Serves the authentic executive Linear/Apple Pro cockpit preloaded with 100% synthetic commercial threads.
Run: python demo_app.py
"""
import json
import os
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs, unquote
from src.models import RawEmail
from src.engine import InboxRadarEngine

PORT = int(os.environ.get("PORT", "8005"))
DEMO_HTML_PATH = os.path.join(os.path.dirname(__file__), "demo", "index.html")


def build_synthetic_mailbox():
    now = datetime(2026, 11, 23, 14, 0, tzinfo=timezone.utc)
    engine = InboxRadarEngine(
        internal_domain="nordicmetals.example",
        client_directory=[
            ("Baltic Foundry AS", ["balticfoundry", "baltic"]),
            ("Scandia Steelworks AB", ["scandiasteel", "scandia"]),
            ("Vanguard Castings GmbH", ["vanguard", "castings"]),
            ("Tallinn Port Logistics OÜ", ["portlogistics", "tallinnport"]),
        ],
    )
    raw_messages = [
        RawEmail(
            message_id="m-001",
            sender_email="k.tamm@balticfoundry.example",
            sender_name="Kristjan Tamm",
            recipient_emails=["sales@nordicmetals.example"],
            subject="RFQ: Electrolytic Manganese 150 ton — Pedido 4500987123",
            body_text="Hello team, confirming Pedido 4500987123 for 150 ton of Electrolytic Manganese 99.7%. Please issue NF 89234 and confirm truck dispatch window for Thursday.",
            received_timestamp=(now - timedelta(hours=5)).isoformat(),
        ),
        RawEmail(
            message_id="m-002",
            sender_email="sales@nordicmetals.example",
            sender_name="Commercial Desk",
            recipient_emails=["a.lind@scandiasteel.example"],
            subject="Re: Quotation — Ferro-Silicon 75% Lump (80 ton)",
            body_text="Attached updated DDP quotation for 80 ton FeSi 75% Lump (valid 5 business days). Please let us know once procurement approves the PO.",
            received_timestamp=(now - timedelta(days=4)).isoformat(),
        ),
        RawEmail(
            message_id="m-003",
            sender_email="procurement@vanguardcastings.example",
            sender_name="Lukas Weber",
            recipient_emails=["sales@nordicmetals.example"],
            subject="Urgent: Silicon Metal 553 specification & moisture certificate (60 ton)",
            body_text="Before unloading the 60 ton batch, our QA lab requires the updated CoA and moisture analysis for NF 90412.",
            received_timestamp=(now - timedelta(hours=11)).isoformat(),
        ),
        RawEmail(
            message_id="m-004",
            sender_email="dispatch@tallinnport.example",
            sender_name="Port Operations",
            recipient_emails=["ops@nordicmetals.example"],
            subject="Weighbridge scale batch reconciliation — 120 ton release",
            body_text="Scale tickets 9001–9004 cleared within ±0.3% tolerance for 120 ton bulk ferroalloy lot. Ready for carrier pickup.",
            received_timestamp=(now - timedelta(hours=22)).isoformat(),
        ),
    ]
    triaged = engine.process_mailbox(raw_messages)

    action_map = {
        "DISPATCH_OPERATIONAL_ACTION": "ACAO_OPERACIONAL",
        "REPLY_PENDING_CLIENT": "RESPONDER",
        "FOLLOW_UP_OUTSTANDING_QUOTE": "COBRAR_FUP",
        "ARCHIVED_RESOLVED": "CONCLUIDO",
    }
    prio_map = {"P1_URGENT": "P1", "P2_STANDARD": "P2", "P3_INFORMATIONAL": "P3"}

    threads = []
    messages_by_key = {}
    for idx, t in enumerate(triaged):
        raw = next((m for m in raw_messages if m.sender_email == t.last_sender_email), raw_messages[0])
        act = action_map.get(t.stage, "RESPONDER")
        prio = prio_map.get(t.priority, "P2")
        po = t.entities.purchase_orders[0] if t.entities.purchase_orders else None
        qty = f"{t.entities.quantities_metric_tons[0]:.0f} MT" if t.entities.quantities_metric_tons else "—"
        nf = t.entities.invoice_numbers[0] if t.entities.invoice_numbers else None

        thread_obj = {
            "thread_key": t.thread_hash[:16],
            "topic": t.normalized_subject,
            "priority": prio,
            "manual_priority": None,
            "is_pinned": idx == 0,
            "effective_action": act,
            "category": "Comercial / Supply Chain",
            "current_stage": t.stage,
            "client_or_partner": t.entities.client_name or "External Counterparty",
            "product_or_theme": t.entities.product_category or "Ferroalloys / Metals",
            "po_number": po,
            "has_draft": idx == 0,
            "fup_is_overdue": act == "COBRAR_FUP",
            "fup_label": "Follow-up 4d" if act == "COBRAR_FUP" else None,
            "fup_due_at": (now + timedelta(days=1)).isoformat() if act == "COBRAR_FUP" else None,
            "days_waiting": 4 if act == "COBRAR_FUP" else 1,
            "days_without_our_contact": 8 if act == "COBRAR_FUP" else 1,
            "message_count": t.total_messages,
            "last_message_at": t.last_received_timestamp,
            "last_sender_name": raw.sender_name,
            "priority_reason": f"Detected {t.stage} with PO/NF entities ({po or nf or 'RFQ'})",
            "recommended_action": "Confirm PO allocation, verify fiscal invoice, and reply to client within SLA window.",
            "manual_notes": "",
            "intel_summary": {
                "material": t.entities.product_category or "Electrolytic Manganese / Ferroalloys",
                "quantity": qty,
                "invoice": nf or "Pending",
                "internal_team": "Commercial & Logistics Desk",
                "external_contacts": [f"{raw.sender_name} <{raw.sender_email}>"],
            },
            "manual_intel": {},
        }
        threads.append(thread_obj)
        messages_by_key[thread_obj["thread_key"]] = [
            {
                "id": raw.message_id,
                "direction": "TEAM_OUT" if t.is_last_sender_internal else "INBOUND",
                "sender_name": raw.sender_name,
                "sender_email": raw.sender_email,
                "recipients": ", ".join(raw.recipient_emails),
                "subject": raw.subject,
                "sent_at": raw.received_timestamp,
                "body_preview": raw.body_text,
                "body_full": raw.body_text,
                "has_attachments": idx in (0, 2),
                "attachments": ["PO_4500987123_Synthetic.pdf"] if idx == 0 else (["CoA_Silicon553.pdf"] if idx == 2 else []),
            }
        ]
    return threads, messages_by_key


THREADS, MESSAGES_BY_KEY = build_synthetic_mailbox()
RECURRING = [
    {
        "id": 1,
        "title": "Weekly PTAX & Freight Margin Review",
        "client_or_partner": "Executive Treasury",
        "frequency": "WEEKLY",
        "next_due_at": "2026-11-23T17:00:00Z",
        "days_until_due": 0,
        "notes": "Compare S0 vs S-1 PTAX and review open bulk orders.",
    },
    {
        "id": 2,
        "title": "Monthly Warehouse Weighbridge Reconciliation",
        "client_or_partner": "Tallinn Port Logistics OÜ",
        "frequency": "MONTHLY",
        "next_due_at": "2026-11-30T12:00:00Z",
        "days_until_due": 7,
        "notes": "Verify FIFO return balance within ±0.5% tolerance.",
    },
]


class DemoHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        p = parsed.path
        if p in ("/", "/index.html"):
            with open(DEMO_HTML_PATH, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(data)
            return

        if p == "/api/dashboard":
            kpis = {
                "p1_criticos": sum(1 for t in THREADS if t["priority"] == "P1"),
                "pendentes_resposta": sum(1 for t in THREADS if t["effective_action"] == "RESPONDER"),
                "cobrar_fup": sum(1 for t in THREADS if t["effective_action"] == "COBRAR_FUP"),
                "sem_contato_7d": sum(1 for t in THREADS if t["days_without_our_contact"] >= 7),
                "acao_operacional": sum(1 for t in THREADS if t["effective_action"] == "ACAO_OPERACIONAL"),
                "recurring_active": len(RECURRING),
            }
            self._json({
                "kpis": kpis,
                "last_sync": {"finished_at": datetime.now(timezone.utc).isoformat()},
                "due_recurring": RECURRING,
            })
            return

        if p == "/api/threads":
            qs = parse_qs(parsed.query)
            act = qs.get("action_status", ["ALL"])[0]
            prio = qs.get("priority", ["ALL"])[0]
            q = qs.get("q", [""])[0].lower().strip()
            out = THREADS
            if act not in ("ALL", "", "FILA_DIA", "HOJE_FILA", "MEU_DIA", "PENDENTES"):
                if act == "SEM_CONTATO_7D":
                    out = [t for t in out if t["days_without_our_contact"] >= 7]
                elif act == "COM_PO":
                    out = [t for t in out if t["po_number"]]
                else:
                    out = [t for t in out if t["effective_action"] == act]
            if prio not in ("ALL", ""):
                out = [t for t in out if t["priority"] == prio]
            if q:
                out = [t for t in out if q in (t["topic"] + " " + t["client_or_partner"]).lower()]
            self._json({"threads": out})
            return

        if p.startswith("/api/threads/"):
            key = unquote(p[len("/api/threads/"):])
            t = next((x for x in THREADS if x["thread_key"] == key), THREADS[0])
            self._json({"thread": t, "messages": MESSAGES_BY_KEY.get(t["thread_key"], [])})
            return

        if p == "/api/recurring":
            self._json({"items": RECURRING})
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        self._json({"ok": True})

    def do_PATCH(self):
        self._json({"ok": True})

    def do_DELETE(self):
        self._json({"ok": True})


if __name__ == "__main__":
    print(f"Enterprise Inbox Radar (Authentic Cockpit Demo) running at http://127.0.0.1:{PORT}")
    HTTPServer(("127.0.0.1", PORT), DemoHandler).serve_forever()
