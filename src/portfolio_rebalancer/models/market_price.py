
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from portfolio_rebalancer.database.base import Base


class MarketPrice(Base):
    __tablename__ = "market_prices"
    __table_args__ = (
        UniqueConstraint(
            "instrument_id",
            "price_date",
            name="uq_market_price_instrument_date",
        ),
        CheckConstraint("price > 0", name="ck_market_price_positive"),
        CheckConstraint(
            "quality IN ('VALID', 'STALE', 'MISSING', 'INVALID')",
            name="ck_market_price_quality",
        ),
    )

    price_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    instrument_id: Mapped[str] = mapped_column(
        ForeignKey("instruments.instrument_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    price_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    price: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    quality: Mapped[str] = mapped_column(String(20), nullable=False, default="VALID")
    source: Mapped[str] = mapped_column(String(100), nullable=False, default="SYNTHETIC")

    instrument: Mapped["Instrument"] = relationship(back_populates="market_prices")
