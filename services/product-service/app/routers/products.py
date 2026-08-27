from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.product_service import ProductService
from app.repositories.product_repository import ProductRepository

router = APIRouter(prefix="/products", tags=["Products"])


def _get_product_service(db: AsyncSession = Depends(get_db)) -> ProductService:
    repo = ProductRepository(db)
    return ProductService(repo)


@router.post("/", status_code=201)
async def create_product(
    data: dict,
    service: ProductService = Depends(_get_product_service),
) -> Any:
    response = await service.create_product(data)
    return response.to_dict()


@router.get("/")
async def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    active_only: bool = Query(True),
    service: ProductService = Depends(_get_product_service),
) -> Any:
    response = await service.list_products(skip=skip, limit=limit, active_only=active_only)
    return response.to_dict()


@router.get("/{product_id}")
async def get_product(
    product_id: str,
    service: ProductService = Depends(_get_product_service),
) -> Any:
    response = await service.get_product(product_id)
    return response.to_dict()


@router.patch("/{product_id}")
async def update_product(
    product_id: str,
    data: dict,
    service: ProductService = Depends(_get_product_service),
) -> Any:
    response = await service.update_product(product_id, data)
    return response.to_dict()


@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: str,
    service: ProductService = Depends(_get_product_service),
) -> None:
    await service.delete_product(product_id)


@router.get("/{product_id}/stock")
async def get_stock(
    product_id: str,
    service: ProductService = Depends(_get_product_service),
) -> Any:
    response = await service.get_stock(product_id)
    return response.to_dict()


@router.post("/{product_id}/stock/decrement")
async def decrement_stock(
    product_id: str,
    data: dict,
    service: ProductService = Depends(_get_product_service),
) -> Any:
    response = await service.decrement_stock(product_id, data)
    return response.to_dict()
