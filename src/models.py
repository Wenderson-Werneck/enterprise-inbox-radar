from typing import Literal, Optional, List
from pydantic import BaseModel, Field


TriageStage = Literal[
    "REPLY_PENDING_CLIENT",       # Inbound email from client awaiting internal response
    "FOLLOW_UP_OUTSTANDING_QUOTE", # Internal quotation sent, awaiting client feedback
    "DISPATCH_OPERATIONAL_ACTION", # PO received, dispatch/logistics coordination required
    "ARCHIVED_RESOLVED"           # Demands completed or closed
]

PriorityLevel = Literal["P1_URGENT", "P2_STANDARD", "P3_INFORMATIONAL"]


class ExtractedEntities(BaseModel):
    purchase_orders: List[str] = Field(default_factory=list)
    invoice_numbers: List[str] = Field(default_factory=list)
    quantities_metric_tons: List[float] = Field(default_factory=list)
    client_name: Optional[str] = None
    product_category: Optional[str] = None


class RawEmail(BaseModel):
    message_id: str
    sender_email: str
    sender_name: str
    recipient_emails: List[str]
    subject: str
    body_text: str
    received_timestamp: str  # ISO 8601


class TriagedThread(BaseModel):
    thread_hash: str
    normalized_subject: str
    stage: TriageStage
    priority: PriorityLevel
    total_messages: int
    last_sender_email: str
    last_received_timestamp: str
    is_last_sender_internal: bool
    entities: ExtractedEntities
