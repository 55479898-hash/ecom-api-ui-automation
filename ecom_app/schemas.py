from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    success: bool
    message: str
    token: str | None = None
    user_id: int | None = None
    username: str | None = None


class ProductResponse(BaseModel):
    id: int
    name: str
    category: str
    price: float
    stock: int
    description: str


class CartItemRequest(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity: int = Field(1, ge=1)


class OrderCreateRequest(BaseModel):
    pass


class OrderItemResponse(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    unit_price: float


class OrderResponse(BaseModel):
    id: int
    user_id: int
    total_amount: float
    discount_amount: float = 0.0
    status: str
    created_at: str
    items: list[OrderItemResponse] = []


class PaymentCallbackRequest(BaseModel):
    order_id: int = Field(..., gt=0)
    payment_status: str = Field(..., pattern="^(success|failed)$")
    transaction_id: str = Field(..., min_length=1)


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    error_code: str | None = None
