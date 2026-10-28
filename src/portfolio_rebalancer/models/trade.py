
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from portfolio_rebalancer.database.base import Base


class Trade(Base):
    __tablename__ = "trades"
    __table_args__ = (
        CheckConstraint("side IN ('BUY', 'SELL')", name="ck_trade_side"),
        CheckConstraint("quantity > 0", name="ck_trade_quantity_positive"),
        CheckConstraint("price > 0", name="ck_trade_price_positive"),
        CheckConstraint("fees >= 0", name="ck_trade_fees_nonnegative"),
        CheckConstraint(
            "status IN ('PROPOSED', 'APPROVED', 'REJECTED', 'EXECUTED', 'FAILED')",
            name="ck_trade_status",
        ),
    )

    trade_id: Mapped[str] = mapped_column(String(60), primary_key=True)
    proposal_id: Mapped[str] = mapped_column(
        ForeignKey("rebalance_proposals.proposal_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    instrument_id: Mapped[str] = mapped_column(
        ForeignKey("instruments.instrument_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    side: Mapped[str] = mapped_column(String(4), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    fees: Mapped[Decimal] = mapped_column(
        Numeric(20, 6), nullable=False, default=Decimal("0")
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PROPOSED")
    reason_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    proposal: Mapped["RebalanceProposal"] = relationship(back_populates="trades")
