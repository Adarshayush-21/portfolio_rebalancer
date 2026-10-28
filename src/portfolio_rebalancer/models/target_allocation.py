
from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from portfolio_rebalancer.database.base import Base


class TargetAllocation(Base):
    __tablename__ = "target_allocations"
    __table_args__ = (
        UniqueConstraint(
            "portfolio_id",
            "asset_class",
            "effective_from",
            name="uq_target_portfolio_class_effective",
        ),
        CheckConstraint(
            "target_weight >= 0 AND target_weight <= 1",
            name="ck_target_weight_range",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_target_effective_dates",
        ),
    )

    target_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    portfolio_id: Mapped[str] = mapped_column(
        ForeignKey("portfolios.portfolio_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    asset_class: Mapped[str] = mapped_column(String(20), nullable=False)
    target_weight: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    portfolio: Mapped["Portfolio"] = relationship(
        back_populates="target_allocations"
    )
