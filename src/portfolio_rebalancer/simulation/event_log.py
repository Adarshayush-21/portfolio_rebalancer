
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from portfolio_rebalancer.models.events import SimulationEvent


def append_simulation_event(
    session: Session,
    event_type: str,
    entity_type: str,
    entity_id: str,
    payload: dict,
    correlation_id: str | None = None,
) -> SimulationEvent:
    if not event_type.strip():
        raise ValueError("event_type cannot be empty")
    if not entity_type.strip():
        raise ValueError("entity_type cannot be empty")
    if not entity_id.strip():
        raise ValueError("entity_id cannot be empty")
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dictionary")

    correlation = correlation_id or entity_id
    prefix = f"EVT-{correlation}-"

    existing_ids = session.scalars(
        select(SimulationEvent.event_id).where(
            SimulationEvent.event_id.like(f"{prefix}%")
        )
    ).all()

    sequence_numbers = []
    for existing_id in existing_ids:
        suffix = existing_id.removeprefix(prefix)
        if suffix.isdigit():
            sequence_numbers.append(int(suffix))

    sequence = max(sequence_numbers, default=0) + 1

    event = SimulationEvent(
        event_id=f"{prefix}{sequence:04d}",
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        occurred_at=datetime.now(timezone.utc),
        payload=payload,
        correlation_id=correlation,
    )

    session.add(event)
    session.flush()

    return event
