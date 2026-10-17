"""Service-to-service endpoints. Not routed by the gateway; require the internal token."""

from fastapi import APIRouter, Depends

from app.contracts.product import StockDecrementRequest, StockIncrementRequest, StockResponse
from app.dependencies import get_product_service
from app.services.product_service import ProductService
from common.auth import require_internal_service

router = APIRouter(
    prefix="/internal/products",
    tags=["Internal"],
    dependencies=[Depends(require_internal_service)],
)


@router.post("/{product_id}/stock/decrement", response_model=StockResponse)
async def decrement_stock(
    product_id: str,
    request: StockDecrementRequest,
    service: ProductService = Depends(get_product_service),
) -> StockResponse:
    return await service.decrement_stock(product_id, request.quantity)


@router.post("/{product_id}/stock/increment", response_model=StockResponse)
async def increment_stock(
    product_id: str,
    request: StockIncrementRequest,
    service: ProductService = Depends(get_product_service),
) -> StockResponse:
    return await service.increment_stock(product_id, request.quantity)
