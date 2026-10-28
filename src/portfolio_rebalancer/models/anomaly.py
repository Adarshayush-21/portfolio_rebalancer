
from datetime import datetime, timezone

from sqlalchemy import DateTime, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from portfolio_rebalancer.database.base import Base


class AnomalyRecord(Base):
    __tablename__ = "anomaly_records"

    anomaly_id: Mapped[str] = mapped_column(String(60), primary_key=True)
    dataset_run_id: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    anomaly_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    injected: Mapped[bool] = mapped_column(nullable=False, default=False)
    detected: Mapped[bool] = mapped_column(nullable=False, default=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
