from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import Field

from app.contracts.base import BaseContract

if TYPE_CHECKING:
    from app.models.product import Product


class ProductCreateContract(BaseContract):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    price: float = Field(..., gt=0)
    stock: int = Field(0, ge=0)
    sku: str = Field(..., min_length=1, max_length=64)
    is_active: bool = True


class ProductUpdateContract(BaseContract):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    price: float | None = Field(None, gt=0)
    stock: int | None = Field(None, ge=0)
    is_active: bool | None = None


class ProductResponse(BaseContract):
    id: str
    name: str
    description: str | None = None
    price: float
    stock: int
    sku: str
    is_active: bool
    created_at: datetime | None = Field(default_factory=datetime.now)
    updated_at: datetime | None = Field(default_factory=datetime.now)

    @classmethod
    def from_product_model(cls, product: "Product") -> "ProductResponse":
        return cls(
            id=str(product.id),
            name=product.name,
            description=product.description,
            price=product.price,
            stock=product.stock,
            sku=product.sku,
            is_active=product.is_active,
            created_at=product.created_at,
            updated_at=product.updated_at,
        )

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True)


class StockDecrementRequest(BaseContract):
    quantity: int = Field(..., gt=0)


class StockResponse(BaseContract):
    id: str
    name: str
    stock: int

    @classmethod
    def from_product_model(cls, product: "Product") -> "StockResponse":
        return cls(
            id=str(product.id),
            name=product.name,
            stock=product.stock,
        )

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True)


class ProductListResponse(BaseContract):
    products: list[ProductResponse]
    total: int

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True)
