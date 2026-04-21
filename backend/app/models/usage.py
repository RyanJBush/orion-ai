from datetime import date

from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UsageQuotaModel(Base):
    __tablename__ = "usage_quotas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    actor_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    period_day: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    max_runs: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    used_runs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
