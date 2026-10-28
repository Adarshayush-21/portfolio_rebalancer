
from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from portfolio_rebalancer.database.base import Base


class FeeSchedule(Base):
    __tablename__ = "fee_schedules"
    __table_args__ = (
        CheckConstraint("fee_rate >= 0", name="ck_fee_rate_nonnegative"),
        CheckConstraint("fixed_fee >= 0", name="ck_fixed_fee_nonnegative"),
        CheckConstraint("minimum_fee >= 0", name="ck_minimum_fee_nonnegative"),
        CheckConstraint("effective_to IS NULL OR effective_to >= effective_from",
                        name="ck_fee_effective_dates"),
    )

    fee_schedule_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    instrument_id: Mapped[str | None] = mapped_column(
        ForeignKey("instruments.instrument_id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    asset_class: Mapped[str | None] = mapped_column(String(20), nullable=True)
    fee_rate: Mapped[Decimal] = mapped_column(Numeric(12, 8), nullable=False)
    fixed_fee: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=Decimal("0")
    )
    minimum_fee: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=Decimal("0")
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
