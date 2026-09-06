"""Order routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.order import CreateOrderRequest, OrderListResponse, OrderResponse
from app.database import get_db
from app.repositories.order_repository import OrderRepository
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["Orders"])


def _get_order_service(db: AsyncSession = Depends(get_db)) -> OrderService:
    repo = OrderRepository(db)
    return OrderService(repo)


@router.post("/", response_model=OrderResponse, status_code=201)
async def create_order(
    request: CreateOrderRequest,
    service: OrderService = Depends(_get_order_service),
):
    try:
        return await service.create_order(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    service: OrderService = Depends(_get_order_service),
):
    order = await service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.get("/user/{user_id}", response_model=OrderListResponse)
async def list_orders(
    user_id: str,
    skip: int = 0,
    limit: int = 20,
    service: OrderService = Depends(_get_order_service),
):
    orders = await service.list_orders(user_id, skip=skip, limit=limit)
    return OrderListResponse(orders=orders, total=len(orders))
