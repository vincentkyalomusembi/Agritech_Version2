"""
Products — API Routes
======================
Endpoints:
  POST   /products                       → create product
  GET    /products                       → list all products
  GET    /products/{product_id}          → get one product
  GET    /products/category/{category}   → filter by category
  PATCH  /products/{product_id}          → update product
  DELETE /products/{product_id}          → delete product
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.sessions import get_db
from app.products.model import ProductCategory
from app.products.schema import ProductCreate, ProductUpdate, ProductResponse
from app.products.service import ProductService

router = APIRouter(
    prefix="/products",
    tags=["Products"],
)


@router.post(
    "/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an agricultural product",
)
def create_product(
    data: ProductCreate,
    db: Session = Depends(get_db),
):
    return ProductService(db).create(data)


@router.get(
    "/",
    response_model=list[ProductResponse],
    summary="List all products",
)
def list_products(
    active_only: bool = True,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    return ProductService(db).get_all(active_only=active_only, limit=limit, offset=offset)


@router.get(
    "/category/{category}",
    response_model=list[ProductResponse],
    summary="Get products by category",
)
def get_by_category(
    category: ProductCategory,
    db: Session = Depends(get_db),
):
    return ProductService(db).get_by_category(category)


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Get a single product",
)
def get_product(
    product_id: UUID,
    db: Session = Depends(get_db),
):
    return ProductService(db).get_by_id(product_id)


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Update a product",
)
def update_product(
    product_id: UUID,
    data: ProductUpdate,
    db: Session = Depends(get_db),
):
    return ProductService(db).update(product_id, data)


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a product",
)
def delete_product(
    product_id: UUID,
    db: Session = Depends(get_db),
):
    ProductService(db).delete(product_id)
