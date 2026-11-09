import re
import hashlib
from typing import List, Tuple
from src.models import ExtractedEntities, PriorityLevel, TriageStage


class EmailEntityClassifier:
    """
    Regex and rules-based extractor for SAP POs, invoices, tonnages, and subjects.
    """

    # Regex patterns
    PO_PATTERN = re.compile(r"\b(?:PO|Pedido|Purchase\s*Order)[\s:#-]*(\d{5,12})\b", re.IGNORECASE)
    INV_PATTERN = re.compile(r"\b(?:NF|NFe|Invoice|Nota\s*Fiscal)[\s:#-]*(\d{3,10})\b", re.IGNORECASE)
    TON_PATTERN = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:ton(?:eladas?)?|mt|tons|t)\b", re.IGNORECASE)

    # Subject prefixes to strip for thread clustering
    PREFIX_PATTERN = re.compile(r"^(?:re|fwd|fw|res|enc|autom[aá]tico):\s*", re.IGNORECASE)

    @classmethod
    def normalize_subject(cls, subject: str) -> str:
        s = subject.strip()
        while True:
            cleaned = cls.PREFIX_PATTERN.sub("", s)
            if cleaned == s:
                break
            s = cleaned.strip()
        # Collapse multiple spaces
        return re.sub(r"\s+", " ", s).strip()

    @classmethod
    def compute_thread_hash(cls, normalized_subject: str) -> str:
        key = normalized_subject.lower().encode("utf-8")
        return hashlib.sha256(key).hexdigest()[:16]

    @classmethod
    def extract_entities(cls, text: str, custom_clients: List[Tuple[str, List[str]]] = None) -> ExtractedEntities:
        pos = list(set(cls.PO_PATTERN.findall(text)))
        invs = list(set(cls.INV_PATTERN.findall(text)))

        tons = []
        for match in cls.TON_PATTERN.finditer(text):
            val_str = match.group(1).replace(",", ".")
            try:
                tons.append(float(val_str))
            except ValueError:
                pass

        matched_client = None
        if custom_clients:
            text_lower = text.lower()
            for client_name, aliases in custom_clients:
                if any(alias in text_lower for alias in aliases):
                    matched_client = client_name
                    break

        return ExtractedEntities(
            purchase_orders=pos,
            invoice_numbers=invs,
            quantities_metric_tons=sorted(list(set(tons))),
            client_name=matched_client,
        )

    @classmethod
    def determine_stage_and_priority(
        cls,
        is_last_internal: bool,
        entities: ExtractedEntities,
        text_content: str
    ) -> Tuple[TriageStage, PriorityLevel]:
        text_lower = text_content.lower()

        # Operational action / PO received
        if entities.purchase_orders or "pedido de compra" in text_lower or "ordem de fornecimento" in text_lower:
            return "DISPATCH_OPERATIONAL_ACTION", "P1_URGENT"

        # If last email was sent by external client -> internal team must reply
        if not is_last_internal:
            priority = "P1_URGENT" if any(w in text_lower for w in ["urgente", "asap", "prazo", "atraso"]) else "P2_STANDARD"
            return "REPLY_PENDING_CLIENT", priority

        # If last email was sent internally -> we are waiting for client follow-up
        return "FOLLOW_UP_OUTSTANDING_QUOTE", "P2_STANDARD"
