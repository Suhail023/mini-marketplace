"""Order routes. The acting user is always the JWT subject."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.order import CreateOrderRequest, OrderListResponse, OrderResponse
from app.database import get_db
from app.repositories.order_repository import OrderRepository
from app.services.order_service import OrderService
from app.utils.errors import AppError
from common.auth import Principal, get_current_principal

router = APIRouter(prefix="/orders", tags=["Orders"])


def _get_order_service(db: AsyncSession = Depends(get_db)) -> OrderService:
    repo = OrderRepository(db)
    return OrderService(repo)


@router.post("/", response_model=OrderResponse, status_code=201)
async def create_order(
    request: CreateOrderRequest,
    principal: Principal = Depends(get_current_principal),
    service: OrderService = Depends(_get_order_service),
):
    try:
        return await service.create_order(request, user_id=principal.user_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=OrderListResponse)
async def list_my_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    principal: Principal = Depends(get_current_principal),
    service: OrderService = Depends(_get_order_service),
):
    orders = await service.list_orders(principal.user_id, skip=skip, limit=limit)
    return OrderListResponse(orders=orders, total=len(orders))


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    principal: Principal = Depends(get_current_principal),
    service: OrderService = Depends(_get_order_service),
):
    order = await service.get_order(order_id, user_id=principal.user_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order
