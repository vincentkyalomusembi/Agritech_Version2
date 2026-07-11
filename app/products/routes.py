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


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(data: ProductCreate, db: Session = Depends(get_db)):
    """Add a new agricultural product to the catalogue."""
    return ProductService(db).create(data)


@router.get("/", response_model=list[ProductResponse])
def list_products(
    active_only: bool = True,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Return all products. Pass active_only=false to include deactivated ones."""
    return ProductService(db).get_all(active_only=active_only, limit=limit, offset=offset)


@router.get("/category/{category}", response_model=list[ProductResponse])
def get_by_category(category: ProductCategory, db: Session = Depends(get_db)):
    """Filter products by category (e.g. Fertilizer, Seed, Pesticide)."""
    return ProductService(db).get_by_category(category)


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: UUID, db: Session = Depends(get_db)):
    """Fetch a single product by its UUID."""
    return ProductService(db).get_by_id(product_id)


@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(product_id: UUID, data: ProductUpdate, db: Session = Depends(get_db)):
    """Partial update — only send the fields you want to change."""
    return ProductService(db).update(product_id, data)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: UUID, db: Session = Depends(get_db)):
    """Remove a product from the catalogue."""
    ProductService(db).delete(product_id)
