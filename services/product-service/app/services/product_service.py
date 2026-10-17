from app.contracts.product import (
    ProductCreateContract,
    ProductListResponse,
    ProductResponse,
    ProductUpdateContract,
    StockResponse,
)
from app.models.product import Product
from app.repositories.product_repository import ProductRepository
from app.utils.errors import ConflictError, NotFoundError
from app.utils.logging import setup_logger

logger = setup_logger(__name__)


class ProductService:
    def __init__(self, product_repository: ProductRepository) -> None:
        self.product_repository = product_repository

    async def create_product(self, request: ProductCreateContract) -> ProductResponse:
        if await self.product_repository.get_by_sku(request.sku):
            raise ConflictError(f"Product with SKU '{request.sku}' already exists", "sku")

        product = await self.product_repository.create(request.model_dump())
        logger.info("Product created", extra={"product_id": product.id})
        return ProductResponse.from_product_model(product)

    async def get_product(self, product_id: str) -> ProductResponse:
        return ProductResponse.from_product_model(await self._get_or_404(product_id))

    async def list_products(self, skip: int, limit: int, active_only: bool) -> ProductListResponse:
        products, total = await self.product_repository.list_page(skip, limit, active_only)
        return ProductListResponse(
            products=[ProductResponse.from_product_model(p) for p in products],
            total=total,
        )

    async def update_product(
        self, product_id: str, request: ProductUpdateContract
    ) -> ProductResponse:
        product = await self._get_or_404(product_id)
        fields = request.model_dump(exclude_unset=True)
        if fields:
            product = await self.product_repository.update(product, fields)
            logger.info("Product updated", extra={"product_id": product_id})
        return ProductResponse.from_product_model(product)

    async def delete_product(self, product_id: str) -> None:
        await self.product_repository.delete(await self._get_or_404(product_id))
        logger.info("Product deleted", extra={"product_id": product_id})

    async def get_stock(self, product_id: str) -> StockResponse:
        return StockResponse.from_product_model(await self._get_or_404(product_id))

    async def decrement_stock(self, product_id: str, quantity: int) -> StockResponse:
        product = await self.product_repository.decrement_stock(product_id, quantity)
        if product is None:
            await self._get_or_404(product_id)
            raise ConflictError(f"Insufficient stock for product '{product_id}'", "stock")
        return StockResponse.from_product_model(product)

    async def increment_stock(self, product_id: str, quantity: int) -> StockResponse:
        product = await self.product_repository.increment_stock(product_id, quantity)
        if product is None:
            raise NotFoundError("Product", product_id)
        return StockResponse.from_product_model(product)

    async def _get_or_404(self, product_id: str) -> Product:
        product = await self.product_repository.get_by_id(product_id)
        if product is None:
            raise NotFoundError("Product", product_id)
        return product
