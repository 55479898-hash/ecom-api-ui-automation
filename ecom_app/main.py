from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database import init_db
from schemas import CartItemRequest, LoginRequest, LoginResponse, OrderResponse, PaymentCallbackRequest, ProductResponse
from services import (
    add_to_cart,
    authenticate_user,
    cancel_order,
    create_order,
    create_token,
    get_cart,
    get_orders,
    get_user_id_from_token,
    process_payment_callback,
    search_products,
)

BASE_DIR = Path(__file__).parent
app = FastAPI(title="E-commerce Demo", version="1.0.0")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def require_auth(authorization: str | None) -> int:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"success": False, "message": "Unauthorized", "error_code": "UNAUTHORIZED"})
    token = authorization.removeprefix("Bearer ").strip()
    user_id = get_user_id_from_token(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail={"success": False, "message": "Invalid token", "error_code": "INVALID_TOKEN"})
    return user_id


# ── API Routes ──

@app.post("/api/auth/login", response_model=LoginResponse)
def api_login(body: LoginRequest):
    if not body.username.strip():
        return JSONResponse(status_code=400, content={"success": False, "message": "Username is required", "error_code": "INVALID_USERNAME"})
    if not body.password.strip():
        return JSONResponse(status_code=400, content={"success": False, "message": "Password is required", "error_code": "INVALID_PASSWORD"})

    user = authenticate_user(body.username.strip(), body.password)
    if user is None:
        return JSONResponse(status_code=401, content={"success": False, "message": "Invalid username or password", "error_code": "AUTH_FAILED"})

    token = create_token(user["id"])
    return LoginResponse(success=True, message="Login successful", token=token, user_id=user["id"], username=user["username"])


@app.get("/api/products", response_model=list[ProductResponse])
def api_products(
    q: str | None = Query(None, description="Search keyword"),
    category: str | None = Query(None, description="Product category"),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
):
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(status_code=400, detail={"success": False, "message": "min_price cannot exceed max_price", "error_code": "INVALID_PRICE_RANGE"})

    products = search_products(q=q, category=category, min_price=min_price, max_price=max_price)
    return products


@app.post("/api/cart/items")
def api_add_cart(body: CartItemRequest, authorization: str | None = Header(None)):
    user_id = require_auth(authorization)
    result = add_to_cart(user_id, body.product_id, body.quantity)
    if not result["success"]:
        status = 404 if result.get("error_code") == "PRODUCT_NOT_FOUND" else 400
        return JSONResponse(status_code=status, content=result)
    return result


@app.get("/api/cart")
def api_get_cart(authorization: str | None = Header(None)):
    user_id = require_auth(authorization)
    return {"success": True, "items": get_cart(user_id)}


@app.post("/api/orders")
def api_create_order(authorization: str | None = Header(None)):
    user_id = require_auth(authorization)
    result = create_order(user_id)
    if not result["success"]:
        return JSONResponse(status_code=400, content=result)
    orders = get_orders(user_id, result["order_id"])
    return {"success": True, "message": result["message"], "order": orders[0] if orders else None}


@app.get("/api/orders", response_model=list[OrderResponse])
def api_list_orders(authorization: str | None = Header(None)):
    user_id = require_auth(authorization)
    return get_orders(user_id)


@app.get("/api/orders/{order_id}", response_model=OrderResponse)
def api_get_order(order_id: int, authorization: str | None = Header(None)):
    user_id = require_auth(authorization)
    if order_id <= 0:
        raise HTTPException(status_code=400, detail={"success": False, "message": "Invalid order id", "error_code": "INVALID_ORDER_ID"})
    orders = get_orders(user_id, order_id)
    if not orders:
        raise HTTPException(status_code=404, detail={"success": False, "message": "Order not found", "error_code": "ORDER_NOT_FOUND"})
    return orders[0]


@app.post("/api/payments/callback")
def api_payment_callback(body: PaymentCallbackRequest):
    result = process_payment_callback(body.order_id, body.payment_status, body.transaction_id)
    if not result["success"]:
        status = 404 if result.get("error_code") == "ORDER_NOT_FOUND" else 400
        return JSONResponse(status_code=status, content=result)
    return result


@app.post("/api/orders/{order_id}/cancel")
def api_cancel_order(order_id: int, authorization: str | None = Header(None)):
    user_id = require_auth(authorization)
    if order_id <= 0:
        raise HTTPException(status_code=400, detail={"success": False, "message": "Invalid order id", "error_code": "INVALID_ORDER_ID"})
    result = cancel_order(user_id, order_id)
    if not result["success"]:
        status = 404 if result.get("error_code") == "ORDER_NOT_FOUND" else 400
        return JSONResponse(status_code=status, content=result)
    return result


# ── UI Pages ──

@app.get("/", response_class=HTMLResponse)
def page_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
def page_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/products", response_class=HTMLResponse)
def page_products(request: Request):
    return templates.TemplateResponse("products.html", {"request": request})


@app.get("/cart", response_class=HTMLResponse)
def page_cart(request: Request):
    return templates.TemplateResponse("cart.html", {"request": request})


@app.get("/orders", response_class=HTMLResponse)
def page_orders(request: Request):
    return templates.TemplateResponse("orders.html", {"request": request})
