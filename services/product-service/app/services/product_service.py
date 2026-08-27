from typing import Any, Dict, Optional

from app.contracts.product import (
    ProductCreateContract,
    ProductListResponse,
    ProductResponse,
    ProductUpdateContract,
    StockDecrementRequest,
    StockResponse,
)
from app.repositories.product_repository import ProductRepository
from app.utils.errors import AppError, ConflictError, NotFoundError, ValidationError
from app.utils.logging import setup_logger

logger = setup_logger(__name__)


class ProductService:
    def __init__(self, product_repository: ProductRepository):
        self.product_repository = product_repository

    async def create_product(self, data: Dict[str, Any]) -> ProductResponse:
        logger.info("Processing product creation request")

        try:
            request_model = ProductCreateContract(**data)
        except Exception as e:
            raise ValidationError(str(e))

        existing = await self.product_repository.get_by_sku(request_model.sku)
        if existing:
            raise ConflictError(
                f"Product with SKU '{request_model.sku}' already exists", "sku"
            )

        product_data = {
            "name": request_model.name,
            "description": request_model.description,
            "price": request_model.price,
            "stock": request_model.stock,
            "sku": request_model.sku,
            "is_active": request_model.is_active,
        }

        product = await self.product_repository.create(product_data)
        logger.info(f"Successfully created product {product.id}")
        return ProductResponse.from_product_model(product)

    async def get_product(self, product_id: str) -> ProductResponse:
        logger.info(f"Processing get product request for {product_id}")

        product = await self.product_repository.get_by_id(product_id)
        if not product:
            raise NotFoundError("Product", product_id)

        logger.info(f"Successfully retrieved product {product_id}")
        return ProductResponse.from_product_model(product)

    async def list_products(
        self,
        skip: int = 0,
        limit: int = 20,
        active_only: bool = True,
    ) -> ProductListResponse:
        logger.info("Processing list products request")

        products = await self.product_repository.list_products(
            skip=skip, limit=limit, active_only=active_only
        )

        logger.info(f"Successfully retrieved {len(products)} products")
        return ProductListResponse(
            products=[ProductResponse.from_product_model(p) for p in products],
            total=len(products),
        )

    async def update_product(
        self, product_id: str, data: Dict[str, Any]
    ) -> ProductResponse:
        logger.info(f"Processing update product request for {product_id}")

        try:
            request_model = ProductUpdateContract(**data)
        except Exception as e:
            raise ValidationError(str(e))

        product = await self.product_repository.get_by_id(product_id)
        if not product:
            raise NotFoundError("Product", product_id)

        updates = request_model.model_dump(exclude_unset=True)
        if not updates:
            return ProductResponse.from_product_model(product)

        updated_product = await self.product_repository.update(product_id, updates)
        if not updated_product:
            raise AppError(f"Failed to update product {product_id}", 500)

        logger.info(f"Successfully updated product {product_id}")
        return ProductResponse.from_product_model(updated_product)

    async def delete_product(self, product_id: str) -> bool:
        logger.info(f"Processing delete product request for {product_id}")

        product = await self.product_repository.get_by_id(product_id)
        if not product:
            raise NotFoundError("Product", product_id)

        deleted = await self.product_repository.delete(product_id)
        logger.info(f"Successfully deleted product {product_id}")
        return deleted

    async def get_stock(self, product_id: str) -> StockResponse:
        logger.info(f"Processing get stock request for {product_id}")

        product = await self.product_repository.get_by_id(product_id)
        if not product:
            raise NotFoundError("Product", product_id)

        logger.info(f"Successfully retrieved stock for {product_id}")
        return StockResponse.from_product_model(product)

    async def decrement_stock(
        self, product_id: str, data: Dict[str, Any]
    ) -> StockResponse:
        logger.info(f"Processing stock decrement request for {product_id}")

        try:
            request_model = StockDecrementRequest(**data)
        except Exception as e:
            raise ValidationError(str(e))

        product = await self.product_repository.decrement_stock(
            product_id, request_model.quantity
        )
        if not product:
            raise NotFoundError("Product", product_id)

        logger.info(f"Successfully decremented stock for {product_id}")
        return StockResponse.from_product_model(product)
