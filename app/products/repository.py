"""
Products — Repository
======================
Database operations for AgriculturalProduct.
"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.products.model import AgriculturalProduct, ProductCategory


class ProductRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(self, product: AgriculturalProduct) -> AgriculturalProduct:
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    def get_by_id(self, product_id: UUID) -> AgriculturalProduct | None:
        return self.db.query(AgriculturalProduct).filter(
            AgriculturalProduct.id == product_id
        ).first()

    def get_all(
        self,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AgriculturalProduct]:
        query = self.db.query(AgriculturalProduct)
        if active_only:
            query = query.filter(AgriculturalProduct.is_active == True)
        return query.order_by(AgriculturalProduct.product_name).offset(offset).limit(limit).all()

    def get_by_category(
        self,
        category: ProductCategory,
        active_only: bool = True,
    ) -> list[AgriculturalProduct]:
        query = self.db.query(AgriculturalProduct).filter(
            AgriculturalProduct.category == category
        )
        if active_only:
            query = query.filter(AgriculturalProduct.is_active == True)
        return query.order_by(AgriculturalProduct.product_name).all()

    def update(self, product: AgriculturalProduct) -> AgriculturalProduct:
        self.db.commit()
        self.db.refresh(product)
        return product

    def delete(self, product: AgriculturalProduct) -> None:
        self.db.delete(product)
        self.db.commit()
