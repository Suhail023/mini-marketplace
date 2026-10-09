"""Service-to-service endpoints. Not routed by the gateway; require the internal token."""

from typing import Any

from fastapi import APIRouter, Depends

from app.routers.products import get_product_service
from app.services.product_service import ProductService
from common.auth import require_internal_service

router = APIRouter(
    prefix="/internal/products",
    tags=["Internal"],
    dependencies=[Depends(require_internal_service)],
)


@router.post("/{product_id}/stock/decrement")
async def decrement_stock(
    product_id: str,
    data: dict,
    service: ProductService = Depends(get_product_service),
) -> Any:
    response = await service.decrement_stock(product_id, data)
    return response.to_dict()
