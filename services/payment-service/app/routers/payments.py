"""Payment routes.

Payments are internal-only: they are charged by the order-service saga and are
never exposed through the gateway. Every route requires the internal service token.
"""

from fastapi import APIRouter, Depends

from app.contracts.payment import ChargeRequest, PaymentResponse
from app.dependencies import get_payment_service
from app.services.payment_service import PaymentService
from common.auth import require_internal_service

router = APIRouter(
    prefix="/internal/payments",
    tags=["Payments (internal)"],
    dependencies=[Depends(require_internal_service)],
)


@router.post("/charge", response_model=PaymentResponse, status_code=201)
async def charge(
    request: ChargeRequest,
    service: PaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    return await service.charge(request)


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: str,
    service: PaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    return await service.get_payment(payment_id)
