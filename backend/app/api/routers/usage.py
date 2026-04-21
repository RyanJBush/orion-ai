from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.usage import UsageQuotaResponse, UsageQuotaSetRequest
from app.services.usage_service import UsageService

router = APIRouter()


@router.get("/quota/{actor_id}", response_model=UsageQuotaResponse)
def get_quota(actor_id: str, db: Session = Depends(get_db)) -> UsageQuotaResponse:
    return UsageService(db).get_quota(actor_id)


@router.post("/quota", response_model=UsageQuotaResponse)
def set_quota(payload: UsageQuotaSetRequest, db: Session = Depends(get_db)) -> UsageQuotaResponse:
    return UsageService(db).set_quota(payload)
