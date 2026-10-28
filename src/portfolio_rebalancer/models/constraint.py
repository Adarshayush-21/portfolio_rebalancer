
from datetime import date

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    JSON,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from portfolio_rebalancer.database.base import Base


class Constraint(Base):
    __tablename__ = "constraints"
    __table_args__ = (
        CheckConstraint(
            "constraint_type IN ('EXCLUDE_INSTRUMENT', 'MAX_TRADE_VALUE', "
            "'MIN_TRADE_VALUE', 'MAX_ASSET_WEIGHT', 'MIN_CASH_WEIGHT', "
            "'MAX_TURNOVER', 'BLOCK_BUY', 'BLOCK_SELL')",
            name="ck_constraint_type",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_constraint_effective_dates",
        ),
    )

    constraint_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    portfolio_id: Mapped[str | None] = mapped_column(
        ForeignKey("portfolios.portfolio_id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    instrument_id: Mapped[str | None] = mapped_column(
        ForeignKey("instruments.instrument_id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    constraint_type: Mapped[str] = mapped_column(String(40), nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
