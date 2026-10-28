
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from portfolio_rebalancer.database.base import Base


class PostTradePosition(Base):
    __tablename__ = "post_trade_positions"

    __table_args__ = (
        UniqueConstraint(
            "proposal_id",
            "instrument_id",
            name="uq_post_trade_position_proposal_instrument",
        ),
        CheckConstraint(
            "quantity >= 0",
            name="ck_post_trade_position_quantity_nonnegative",
        ),
        CheckConstraint(
            "valuation_price > 0",
            name="ck_post_trade_position_price_positive",
        ),
        CheckConstraint(
            "market_value >= 0",
            name="ck_post_trade_position_market_value_nonnegative",
        ),
    )

    position_id: Mapped[str] = mapped_column(
        String(160),
        primary_key=True,
    )
    proposal_id: Mapped[str] = mapped_column(
        ForeignKey("rebalance_proposals.proposal_id"),
        nullable=False,
        index=True,
    )
    instrument_id: Mapped[str] = mapped_column(
        ForeignKey("instruments.instrument_id"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(24, 8),
        nullable=False,
    )
    valuation_price: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
    )
    market_value: Mapped[Decimal] = mapped_column(
        Numeric(24, 2),
        nullable=False,
    )
    asset_class: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )
    valuation_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
