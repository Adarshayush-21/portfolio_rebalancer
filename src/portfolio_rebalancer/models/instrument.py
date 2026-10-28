
from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from portfolio_rebalancer.database.base import Base


class Instrument(Base):
    __tablename__ = "instruments"
    __table_args__ = (
        CheckConstraint(
            "asset_class IN ('EQUITY', 'BOND', 'GOLD', 'CASH', 'OTHER')",
            name="ck_instrument_asset_class",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE', 'EXCLUDED')",
            name="ck_instrument_status",
        ),
    )

    instrument_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    asset_class: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")

    holdings: Mapped[list["Holding"]] = relationship(back_populates="instrument")
    market_prices: Mapped[list["MarketPrice"]] = relationship(
        back_populates="instrument"
    )
