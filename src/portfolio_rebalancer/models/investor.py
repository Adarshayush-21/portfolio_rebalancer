
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from portfolio_rebalancer.database.base import Base


class InvestorProfile(Base):
    __tablename__ = "investor_profiles"
    __table_args__ = (
        CheckConstraint(
            "risk_profile IN ('CONSERVATIVE', 'MODERATE', 'AGGRESSIVE')",
            name="ck_investor_risk_profile",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_investor_status",
        ),
    )

    investor_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    risk_profile: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    portfolios: Mapped[list["Portfolio"]] = relationship(
        back_populates="investor",
        passive_deletes=True,
    )
