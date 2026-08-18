from sqlalchemy import Column, Integer, Float, String
from database import Base


class Product(Base):
    """A product item in the inventory system."""

    __tablename__ = 'products'

    # Each product has a unique numeric id.
    id = Column(Integer, primary_key=True, index=True)

    # Product name should be a string.
    name = Column(String)

    # Short description of the product.
    description = Column(String)

    # Price is stored as a float to allow decimal values like 19.99.
    price = Column(Float)

    # Quantity shows how many items are available in stock.
    quantity = Column(Integer)