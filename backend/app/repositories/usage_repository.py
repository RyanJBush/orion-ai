from datetime import date

from sqlalchemy.orm import Session

from app.models.usage import UsageQuotaModel


class UsageQuotaRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_for_day(self, actor_id: str, period_day: date) -> UsageQuotaModel | None:
        return (
            self.db.query(UsageQuotaModel)
            .filter(UsageQuotaModel.actor_id == actor_id)
            .filter(UsageQuotaModel.period_day == period_day)
            .first()
        )

    def create_for_day(self, actor_id: str, period_day: date, max_runs: int) -> UsageQuotaModel:
        row = UsageQuotaModel(actor_id=actor_id, period_day=period_day, max_runs=max_runs, used_runs=0)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def update(self, row: UsageQuotaModel, *, max_runs: int | None = None, used_runs: int | None = None) -> UsageQuotaModel:
        if max_runs is not None:
            row.max_runs = max_runs
        if used_runs is not None:
            row.used_runs = used_runs
        self.db.commit()
        self.db.refresh(row)
        return row
