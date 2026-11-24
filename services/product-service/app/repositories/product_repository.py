from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product, StockRelease
from app.utils.errors import ConflictError


class ProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, fields: dict[str, Any]) -> Product:
        product = Product(**fields)
        self.session.add(product)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise ConflictError(f"Product with SKU '{product.sku}' already exists", "sku")
        await self.session.refresh(product)
        return product

    async def get_by_id(self, product_id: str) -> Product | None:
        return await self.session.get(Product, product_id)

    async def get_by_sku(self, sku: str) -> Product | None:
        result = await self.session.execute(select(Product).where(Product.sku == sku))
        return result.scalar_one_or_none()

    async def list_page(
        self, skip: int, limit: int, active_only: bool
    ) -> tuple[list[Product], int]:
        stmt = select(Product)
        if active_only:
            stmt = stmt.where(Product.is_active.is_(True))

        total = await self.session.scalar(select(func.count()).select_from(stmt.subquery()))
        result = await self.session.execute(
            stmt.order_by(Product.created_at.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all()), total or 0

    async def update(self, product: Product, fields: dict[str, Any]) -> Product:
        for key, value in fields.items():
            setattr(product, key, value)
        await self.session.commit()
        await self.session.refresh(product)
        return product

    async def delete(self, product: Product) -> None:
        await self.session.delete(product)
        await self.session.commit()

    async def decrement_stock(self, product_id: str, quantity: int) -> Product | None:
        """Atomically decrement; returns None if the product is missing or short on stock."""
        result = await self.session.execute(
            update(Product)
            .where(Product.id == product_id, Product.stock >= quantity)
            .values(stock=Product.stock - quantity)
        )
        if result.rowcount == 0:
            await self.session.rollback()
            return None
        await self.session.commit()
        return await self._reload(product_id)

    async def increment_stock(
        self, product_id: str, quantity: int, order_id: str | None = None
    ) -> Product | None:
        if order_id is not None:
            inserted = await self.session.scalar(
                insert(StockRelease)
                .values(order_id=order_id, product_id=product_id, quantity=quantity)
                .on_conflict_do_nothing(index_elements=[StockRelease.order_id])
                .returning(StockRelease.order_id)
            )
            if inserted is None:
                previous = await self.session.get(StockRelease, order_id)
                if previous.product_id != product_id or previous.quantity != quantity:
                    raise ConflictError(
                        "Stock release differs from the original request", "order_id"
                    )
                return await self._reload(product_id)
        result = await self.session.execute(
            update(Product).where(Product.id == product_id).values(stock=Product.stock + quantity)
        )
        if result.rowcount == 0:
            await self.session.rollback()
            return None
        await self.session.commit()
        return await self._reload(product_id)

    async def _reload(self, product_id: str) -> Product | None:
        return await self.session.get(Product, product_id, populate_existing=True)
