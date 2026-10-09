"""Payment routes.

Payments are internal-only: they are charged by the order-service saga and are
never exposed through the gateway. Every route requires the internal service token.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.payment import ChargeRequest, PaymentResponse
from app.database import get_db
from app.repositories.payment_repository import PaymentRepository
from app.services.payment_service import PaymentService
from common.auth import require_internal_service

router = APIRouter(
    prefix="/internal/payments",
    tags=["Payments (internal)"],
    dependencies=[Depends(require_internal_service)],
)


def _get_payment_service(db: AsyncSession = Depends(get_db)) -> PaymentService:
    repo = PaymentRepository(db)
    return PaymentService(repo)


@router.post("/charge", response_model=PaymentResponse, status_code=201)
async def charge(
    request: ChargeRequest,
    service: PaymentService = Depends(_get_payment_service),
):
    return await service.charge(request)


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: str,
    service: PaymentService = Depends(_get_payment_service),
):
    payment = await service.get_payment(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment
