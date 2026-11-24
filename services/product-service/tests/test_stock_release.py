from unittest import IsolatedAsyncioTestCase

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.product import Base, Product
from app.repositories.product_repository import ProductRepository
from app.utils.errors import ConflictError


class StockReleaseTest(IsolatedAsyncioTestCase):
    async def test_retry_after_committed_release(self):
        engine = create_async_engine("sqlite+aiosqlite://")
        self.addAsyncCleanup(engine.dispose)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions() as session:
            session.add(Product(id="item", name="Item", sku="sku", price=1, stock=4))
            await session.commit()
            await ProductRepository(session).increment_stock("item", 3, "order")
        async with sessions() as session:
            repo = ProductRepository(session)
            result = await repo.increment_stock("item", 3, "order")
            self.assertEqual(result.stock, 7)
            with self.assertRaises(ConflictError):
                await repo.increment_stock("item", 2, "order")
