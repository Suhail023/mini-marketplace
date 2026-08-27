from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.utils.errors import AppError, NotFoundError
from app.utils.logging import setup_logger

logger = setup_logger(__name__)


class ProductRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, product_data: dict) -> Product:
        try:
            product = Product(**product_data)
            self.db.add(product)
            await self.db.commit()
            await self.db.refresh(product)
            return product
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating product: {str(e)}")
            raise AppError("Failed to create product", 500)

    async def get_by_id(self, product_id: str) -> Optional[Product]:
        try:
            return await self.db.get(Product, product_id)
        except Exception as e:
            logger.error(f"Error fetching product {product_id}: {str(e)}")
            raise AppError("Failed to fetch product", 500)

    async def get_by_sku(self, sku: str) -> Optional[Product]:
        try:
            stmt = select(Product).where(Product.sku == sku)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching product by SKU {sku}: {str(e)}")
            raise AppError("Failed to fetch product", 500)

    async def list_products(
        self,
        skip: int = 0,
        limit: int = 20,
        active_only: bool = True,
    ) -> list[Product]:
        try:
            stmt = select(Product)
            if active_only:
                stmt = stmt.where(Product.is_active.is_(True))
            stmt = stmt.offset(skip).limit(limit).order_by(Product.created_at.desc())
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error listing products: {str(e)}")
            raise AppError("Failed to list products", 500)

    async def update(self, product_id: str, updates: dict) -> Optional[Product]:
        try:
            product = await self.db.get(Product, product_id)
            if not product:
                return None

            for key, value in updates.items():
                if hasattr(product, key):
                    setattr(product, key, value)

            await self.db.commit()
            await self.db.refresh(product)
            return product
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating product {product_id}: {str(e)}")
            raise AppError("Failed to update product", 500)

    async def delete(self, product_id: str) -> bool:
        try:
            product = await self.db.get(Product, product_id)
            if not product:
                return False

            await self.db.delete(product)
            await self.db.commit()
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting product {product_id}: {str(e)}")
            raise AppError("Failed to delete product", 500)

    async def decrement_stock(
        self, product_id: str, quantity: int
    ) -> Optional[Product]:
        try:
            stmt = (
                update(Product)
                .where(Product.id == product_id, Product.stock >= quantity)
                .values(stock=Product.stock - quantity)
            )
            result = await self.db.execute(stmt)
            if result.rowcount == 0:
                return None

            await self.db.commit()
            return await self.db.get(Product, product_id)
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error decrementing stock for {product_id}: {str(e)}")
            raise AppError("Failed to decrement stock", 500)
