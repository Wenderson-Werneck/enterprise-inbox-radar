import pytest
from src.models import RawEmail
from src.classifier import EmailEntityClassifier
from src.engine import InboxRadarEngine


def test_subject_normalization_and_hash():
    s1 = "Re: Fwd: RES: Cotação de Manganês Eletrolítico"
    s2 = "Cotação de Manganês Eletrolítico"
    s3 = "  RES:  Cotação de Manganês Eletrolítico  "

    assert EmailEntityClassifier.normalize_subject(s1) == s2
    assert EmailEntityClassifier.normalize_subject(s3) == s2
    assert (
        EmailEntityClassifier.compute_thread_hash(EmailEntityClassifier.normalize_subject(s1))
        == EmailEntityClassifier.compute_thread_hash(s2)
    )


def test_entity_extraction_po_and_tonnage():
    text = """
    Olá equipe, segue confirmação do Pedido 4500987123 para fornecimento de 150 ton de ferro-liga.
    Favor emitir NF 89234 para faturamento.
    """
    entities = EmailEntityClassifier.extract_entities(
        text,
        custom_clients=[("Nordic Minerals AG", ["nordic minerals", "nordic"])]
    )

    assert "4500987123" in entities.purchase_orders
    assert "89234" in entities.invoice_numbers
    assert 150.0 in entities.quantities_metric_tons


def test_triage_flow_stages():
    engine = InboxRadarEngine(internal_domain="enterprise.com")

    emails = [
        # Thread 1: Inbound client inquiry (Needs reply)
        RawEmail(
            message_id="msg_001",
            sender_email="procurement@nordicsteel.com",
            sender_name="Jane Doe",
            recipient_emails=["sales@enterprise.com"],
            subject="Solicitação de Preço - Cobre Catodo",
            body_text="Precisamos de cotação urgente para 50 toneladas.",
            received_timestamp="2026-11-09T08:30:00Z",
        ),
        # Thread 2: We sent a quote, waiting on client follow-up
        RawEmail(
            message_id="msg_002",
            sender_email="sales@enterprise.com",
            sender_name="John Internal",
            recipient_emails=["buyer@balticalloys.com"],
            subject="Proposta Comercial #9021 - Baltic Alloys",
            body_text="Segue em anexo nossa proposta técnica.",
            received_timestamp="2026-11-09T09:00:00Z",
        ),
        # Thread 3: PO received (Operational action)
        RawEmail(
            message_id="msg_003",
            sender_email="buyer@balticalloys.com",
            sender_name="Hans Schmidt",
            recipient_emails=["sales@enterprise.com"],
            subject="PO 88001122 - Ordem de Fornecimento Aprovada",
            body_text="Segue PO 88001122 aprovada para carregamento nesta sexta-feira.",
            received_timestamp="2026-11-09T09:15:00Z",
        ),
    ]

    triaged = engine.process_mailbox(emails)
    assert len(triaged) == 3

    # Check stages
    stage_by_subject = {t.normalized_subject: t.stage for t in triaged}
    assert stage_by_subject["Solicitação de Preço - Cobre Catodo"] == "REPLY_PENDING_CLIENT"
    assert stage_by_subject["Proposta Comercial #9021 - Baltic Alloys"] == "FOLLOW_UP_OUTSTANDING_QUOTE"
    assert stage_by_subject["PO 88001122 - Ordem de Fornecimento Aprovada"] == "DISPATCH_OPERATIONAL_ACTION"
