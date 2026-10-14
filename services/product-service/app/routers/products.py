from fastapi import APIRouter, Depends, Query

from app.contracts.product import (
    ProductCreateContract,
    ProductListResponse,
    ProductResponse,
    ProductUpdateContract,
    StockResponse,
)
from app.dependencies import get_product_service
from app.services.product_service import ProductService
from common.auth import require_admin

router = APIRouter(prefix="/products", tags=["Products"])


@router.post(
    "/",
    status_code=201,
    response_model=ProductResponse,
    dependencies=[Depends(require_admin)],
)
async def create_product(
    request: ProductCreateContract,
    service: ProductService = Depends(get_product_service),
) -> ProductResponse:
    return await service.create_product(request)


@router.get("/", response_model=ProductListResponse)
async def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    active_only: bool = Query(True),
    service: ProductService = Depends(get_product_service),
) -> ProductListResponse:
    return await service.list_products(skip=skip, limit=limit, active_only=active_only)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    service: ProductService = Depends(get_product_service),
) -> ProductResponse:
    return await service.get_product(product_id)


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    dependencies=[Depends(require_admin)],
)
async def update_product(
    product_id: str,
    request: ProductUpdateContract,
    service: ProductService = Depends(get_product_service),
) -> ProductResponse:
    return await service.update_product(product_id, request)


@router.delete("/{product_id}", status_code=204, dependencies=[Depends(require_admin)])
async def delete_product(
    product_id: str,
    service: ProductService = Depends(get_product_service),
) -> None:
    await service.delete_product(product_id)


@router.get("/{product_id}/stock", response_model=StockResponse)
async def get_stock(
    product_id: str,
    service: ProductService = Depends(get_product_service),
) -> StockResponse:
    return await service.get_stock(product_id)
