
from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from portfolio_rebalancer.database.base import Base


class Holding(Base):
    __tablename__ = "holdings"
    __table_args__ = (
        UniqueConstraint(
            "portfolio_id",
            "instrument_id",
            "as_of_date",
            name="uq_holding_portfolio_instrument_date",
        ),
        CheckConstraint("quantity >= 0", name="ck_holding_quantity"),
    )

    holding_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    portfolio_id: Mapped[str] = mapped_column(
        ForeignKey("portfolios.portfolio_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    instrument_id: Mapped[str] = mapped_column(
        ForeignKey("instruments.instrument_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    portfolio: Mapped["Portfolio"] = relationship(back_populates="holdings")
    instrument: Mapped["Instrument"] = relationship(back_populates="holdings")
