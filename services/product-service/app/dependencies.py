"""Composition root: wires repositories into services for each request."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.product_repository import ProductRepository
from app.services.product_service import ProductService


def get_product_service(session: AsyncSession = Depends(get_db)) -> ProductService:
    return ProductService(ProductRepository(session))
