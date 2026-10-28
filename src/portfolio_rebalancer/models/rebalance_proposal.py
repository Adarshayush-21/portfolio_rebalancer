
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from portfolio_rebalancer.database.base import Base


class RebalanceProposal(Base):
    __tablename__ = "rebalance_proposals"
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'VALIDATED', 'APPROVED', 'REJECTED', "
            "'EXECUTED', 'CANCELLED', 'FAILED')",
            name="ck_proposal_status",
        ),
        CheckConstraint(
            "total_fees >= 0",
            name="ck_proposal_fees_nonnegative",
        ),
    )

    proposal_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    portfolio_id: Mapped[str] = mapped_column(
        ForeignKey("portfolios.portfolio_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    estimated_turnover: Mapped[Decimal] = mapped_column(
        Numeric(20, 6), nullable=False, default=Decimal("0")
    )
    total_fees: Mapped[Decimal] = mapped_column(
        Numeric(20, 6), nullable=False, default=Decimal("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    rationale: Mapped[str] = mapped_column(String(1000), nullable=False, default="")

    portfolio: Mapped["Portfolio"] = relationship(back_populates="proposals")
    trades: Mapped[list["Trade"]] = relationship(back_populates="proposal")
