from datetime import date

from pydantic import BaseModel


class UsageQuotaSetRequest(BaseModel):
    actor_id: str
    max_runs: int


class UsageQuotaResponse(BaseModel):
    actor_id: str
    period_day: date
    max_runs: int
    used_runs: int
    remaining_runs: int
