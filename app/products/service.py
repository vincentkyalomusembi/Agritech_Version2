"""
Products — Service Layer
"""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.products.model import AgriculturalProduct, ProductCategory
from app.products.repository import ProductRepository
from app.products.schema import ProductCreate, ProductUpdate


class ProductService:

    def __init__(self, db: Session):
        self.db = db
        self.repo = ProductRepository(db)

    def create(self, data: ProductCreate) -> AgriculturalProduct:
        product = AgriculturalProduct(
            product_name=data.product_name,
            category=data.category,
            description=data.description,
            manufacturer=data.manufacturer,
            is_active=data.is_active,
            target_type=data.target_type,
        )
        return self.repo.create(product)

    def get_all(
        self,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AgriculturalProduct]:
        return self.repo.get_all(active_only=active_only, limit=limit, offset=offset)

    def get_by_id(self, product_id: UUID) -> AgriculturalProduct:
        product = self.repo.get_by_id(product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product {product_id} not found.",
            )
        return product

    def get_by_category(self, category: ProductCategory) -> list[AgriculturalProduct]:
        return self.repo.get_by_category(category)

    def update(self, product_id: UUID, data: ProductUpdate) -> AgriculturalProduct:
        product = self.get_by_id(product_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(product, field, value)
        return self.repo.update(product)

    def delete(self, product_id: UUID) -> None:
        product = self.get_by_id(product_id)
        self.repo.delete(product)
