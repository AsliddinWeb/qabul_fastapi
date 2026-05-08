"""High-level CRM event firing.

Pattern
-------
Each helper builds a typed payload, then enqueues it to Redis via FastAPI's
`BackgroundTasks` so the request returns without waiting on Redis.
The `CrmWorker` (started at app lifespan) drains the queue, retries with
exponential backoff, and parks failed events in the DLQ after MAX_ATTEMPTS.

Why a queue (not direct send)?
-----------------------------
- CRM downtime no longer leaks into our request path.
- Retries are durable (survive restarts).
- Operations team can inspect / requeue / drop via /api/v1/integrations/crm/*.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import BackgroundTasks

from app.core.logging import get_logger
from app.core.redis import get_redis
from app.integrations.crm.queue import CrmQueue
from app.integrations.crm.schemas import (
    ApplicantLead,
    ApplicantLeadPassport,
    ApplicantLeadProgram,
    ApplicantStatusUpdate,
    ContractCreatedEvent,
    LeadSource,
)

logger = get_logger("crm.events")


# ---------- internal ----------
async def _enqueue(event_type: str, payload: dict) -> None:
    redis = get_redis()
    try:
        item_id = await CrmQueue(redis).enqueue(event_type, payload)
        logger.info("crm.enqueued", event=event_type, item_id=item_id)
    except Exception as exc:  # noqa: BLE001 — never break the user request
        logger.error("crm.enqueue_failed", event=event_type, error=str(exc))
    finally:
        await redis.aclose()


# ---------- Public enqueue helpers (used by routers) ----------
def enqueue_applicant_lead(
    bg: BackgroundTasks,
    *,
    applicant_id: UUID,
    phone: str,
    first_name: str,
    last_name: str,
    middle_name: str | None,
    birth_date,
    gender: str | None,
    email: str | None,
    source: LeadSource,
    created_at: datetime,
    passport: ApplicantLeadPassport | None = None,
    program: ApplicantLeadProgram | None = None,
    metadata: dict | None = None,
) -> None:
    payload = ApplicantLead(
        external_id=str(applicant_id),
        source=source,
        phone=phone,
        email=email,
        first_name=first_name,
        last_name=last_name,
        middle_name=middle_name,
        birth_date=birth_date,
        gender=gender,
        passport=passport,
        program=program,
        metadata=metadata or {},
        created_at=created_at,
    ).model_dump(mode="json")
    bg.add_task(_enqueue, "applicant_lead", payload)


def enqueue_application_status_event(
    bg: BackgroundTasks,
    *,
    external_id: str,
    status: str,
    note: str | None = None,
    changed_at: datetime | None = None,
) -> None:
    from datetime import timezone

    payload = ApplicantStatusUpdate(
        external_id=external_id,
        status=status,
        note=note,
        changed_at=changed_at or datetime.now(timezone.utc),
    ).model_dump(mode="json")
    bg.add_task(_enqueue, "applicant_status", payload)


def enqueue_contract_signed_event(
    bg: BackgroundTasks,
    *,
    applicant_id: UUID,
    contract_number: str,
    contract_type: str,
    total_amount: float,
    currency: str,
    signed_at: datetime,
) -> None:
    payload = ContractCreatedEvent(
        external_id=str(applicant_id),
        contract_number=contract_number,
        contract_type=contract_type,
        total_amount=total_amount,
        currency=currency,
        signed_at=signed_at,
    ).model_dump(mode="json")
    bg.add_task(_enqueue, "contract_signed", payload)
