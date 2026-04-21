from datetime import date

from sqlalchemy.orm import Session

from app.repositories.usage_repository import UsageQuotaRepository
from app.schemas.usage import UsageQuotaResponse, UsageQuotaSetRequest

DEFAULT_DAILY_MAX_RUNS = 100


class QuotaExceededError(Exception):
    pass


class UsageService:
    def __init__(self, db: Session) -> None:
        self.repo = UsageQuotaRepository(db)

    def _get_or_create_today(self, actor_id: str):
        today = date.today()
        row = self.repo.get_for_day(actor_id=actor_id, period_day=today)
        if row is None:
            row = self.repo.create_for_day(actor_id=actor_id, period_day=today, max_runs=DEFAULT_DAILY_MAX_RUNS)
        return row

    def set_quota(self, payload: UsageQuotaSetRequest) -> UsageQuotaResponse:
        row = self._get_or_create_today(payload.actor_id)
        row = self.repo.update(row, max_runs=payload.max_runs)
        return self._to_response(row)

    def get_quota(self, actor_id: str) -> UsageQuotaResponse:
        row = self._get_or_create_today(actor_id)
        return self._to_response(row)

    def consume_run(self, actor_id: str) -> UsageQuotaResponse:
        row = self._get_or_create_today(actor_id)
        if row.used_runs >= row.max_runs:
            raise QuotaExceededError(f"Daily run quota exceeded for actor '{actor_id}'")
        row = self.repo.update(row, used_runs=row.used_runs + 1)
        return self._to_response(row)

    @staticmethod
    def _to_response(row) -> UsageQuotaResponse:
        return UsageQuotaResponse(
            actor_id=row.actor_id,
            period_day=row.period_day,
            max_runs=row.max_runs,
            used_runs=row.used_runs,
            remaining_runs=max(row.max_runs - row.used_runs, 0),
        )
