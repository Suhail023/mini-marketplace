from datetime import datetime
from typing import Any, Dict, Optional, TYPE_CHECKING

from pydantic import Field

from app.contracts.base import BaseContract

if TYPE_CHECKING:
    from app.models.product import Product


class ProductCreateContract(BaseContract):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    stock: int = Field(0, ge=0)
    sku: str = Field(..., min_length=1, max_length=64)
    is_active: bool = True


class ProductUpdateContract(BaseContract):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    stock: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class ProductResponse(BaseContract):
    id: str
    name: str
    description: Optional[str] = None
    price: float
    stock: int
    sku: str
    is_active: bool
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)

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

    def to_dict(self) -> Dict[str, Any]:
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

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(by_alias=True)


class ProductListResponse(BaseContract):
    products: list[ProductResponse]
    total: int

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(by_alias=True)
