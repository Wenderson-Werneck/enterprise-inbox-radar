from typing import List, Dict, Tuple
from collections import defaultdict
from src.models import RawEmail, TriagedThread, ExtractedEntities
from src.classifier import EmailEntityClassifier


class InboxRadarEngine:
    """
    Core triage engine that groups heterogeneous email messages into normalized
    threads and evaluates operational SLAs.
    """

    def __init__(self, internal_domain: str = "enterprise.com", client_directory: List[Tuple[str, List[str]]] = None):
        self.internal_domain = internal_domain.lower()
        self.client_directory = client_directory or []

    def is_internal_email(self, email: str) -> bool:
        return self.internal_domain in email.lower()

    def process_mailbox(self, messages: List[RawEmail]) -> List[TriagedThread]:
        # Group by normalized thread hash
        grouped: Dict[str, List[RawEmail]] = defaultdict(list)
        for msg in messages:
            norm_subj = EmailEntityClassifier.normalize_subject(msg.subject)
            th_hash = EmailEntityClassifier.compute_thread_hash(norm_subj)
            grouped[th_hash].append(msg)

        triaged_threads: List[TriagedThread] = []

        for th_hash, thread_msgs in grouped.items():
            # Sort messages chronologically
            thread_msgs.sort(key=lambda m: m.received_timestamp)

            norm_subj = EmailEntityClassifier.normalize_subject(thread_msgs[0].subject)
            last_msg = thread_msgs[-1]
            is_last_internal = self.is_internal_email(last_msg.sender_email)

            # Combine all text across thread for entity extraction
            combined_text = "\n".join([f"{m.subject}\n{m.body_text}" for m in thread_msgs])
            entities = EmailEntityClassifier.extract_entities(combined_text, self.client_directory)

            stage, priority = EmailEntityClassifier.determine_stage_and_priority(
                is_last_internal, entities, last_msg.body_text
            )

            triaged_threads.append(
                TriagedThread(
                    thread_hash=th_hash,
                    normalized_subject=norm_subj,
                    stage=stage,
                    priority=priority,
                    total_messages=len(thread_msgs),
                    last_sender_email=last_msg.sender_email,
                    last_received_timestamp=last_msg.received_timestamp,
                    is_last_sender_internal=is_last_internal,
                    entities=entities,
                )
            )

        # Sort threads: P1 first, then by latest timestamp descending
        priority_rank = {"P1_URGENT": 0, "P2_STANDARD": 1, "P3_INFORMATIONAL": 2}
        triaged_threads.sort(
            key=lambda t: (priority_rank[t.priority], t.last_received_timestamp),
            reverse=False
        )

        return triaged_threads
