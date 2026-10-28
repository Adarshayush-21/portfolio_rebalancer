
from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from portfolio_rebalancer.database.base import Base


class Portfolio(Base):
    __tablename__ = "portfolios"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE', 'CLOSED')",
            name="ck_portfolio_status",
        ),
    )

    portfolio_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    investor_id: Mapped[str] = mapped_column(
        ForeignKey("investor_profiles.investor_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")

    investor: Mapped["InvestorProfile"] = relationship(back_populates="portfolios")
    holdings: Mapped[list["Holding"]] = relationship(back_populates="portfolio")
    target_allocations: Mapped[list["TargetAllocation"]] = relationship(
        back_populates="portfolio"
    )
    proposals: Mapped[list["RebalanceProposal"]] = relationship(
        back_populates="portfolio"
    )
