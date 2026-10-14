"""Order routes. The acting user is always the JWT subject."""

from fastapi import APIRouter, Depends, Query

from app.contracts.order import CreateOrderRequest, OrderListResponse, OrderResponse
from app.dependencies import get_order_service
from app.services.order_service import OrderService
from common.auth import Principal, get_current_principal

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("/", response_model=OrderResponse, status_code=201)
async def create_order(
    request: CreateOrderRequest,
    principal: Principal = Depends(get_current_principal),
    service: OrderService = Depends(get_order_service),
) -> OrderResponse:
    return await service.create_order(request, user_id=principal.user_id)


@router.get("/", response_model=OrderListResponse)
async def list_my_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    principal: Principal = Depends(get_current_principal),
    service: OrderService = Depends(get_order_service),
) -> OrderListResponse:
    return await service.list_orders(principal.user_id, skip=skip, limit=limit)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    principal: Principal = Depends(get_current_principal),
    service: OrderService = Depends(get_order_service),
) -> OrderResponse:
    return await service.get_order(order_id, user_id=principal.user_id)
