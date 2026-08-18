from pydantic import BaseModel


# ------------------------------------------------------------
# Pydantic model
# ------------------------------------------------------------
# A Pydantic model defines the structure of incoming or outgoing data.
# FastAPI uses it to validate requests and serialize responses.
#
# In simple words: if a client sends JSON with incorrect types or missing
# fields, FastAPI will reject the request before your endpoint logic runs.
class Product(BaseModel):
    """A product item in the inventory system."""

    # Each product has a unique numeric id.
    id: int

    # Product name should be a string.
    name: str

    # Short description of the product.
    description: str

    # Price is stored as a float to allow decimal values like 19.99.
    price: float

    # Quantity shows how many items are available in stock.
    quantity: int


# ------------------------------------------------------------
# Why use BaseModel?
# ------------------------------------------------------------
# BaseModel automatically gives us:
# - data validation
# - type checking
# - automatic conversion from JSON to Python objects
# - easy response formatting into JSON
#
# Without Pydantic, we would have to manually check every field and type.
# That would make the code longer, more repetitive, and easier to break.
#
# Example of a manual constructor (not used here):
#
# class Product:
#     def __init__(self, id, name, description, price, quantity):
#         self.id = id
#         self.name = name
#         self.description = description
#         self.price = price
#         self.quantity = quantity
#
# With BaseModel, FastAPI handles this validation automatically.

class ProductUpdate(BaseModel):
# Each product has a unique numeric id.
    id: int

    # Product name should be a string.
    name: str

    # Short description of the product.
    description: str

    # Price is stored as a float to allow decimal values like 19.99.
    price: float

    # Quantity shows how many items are available in stock.
    quantity: int    

class ProductResponse(BaseModel):
# Each product has a unique numeric id.
    id: int

    # Product name should be a string.
    name: str

    # Short description of the product.
    description: str

    # Price is stored as a float to allow decimal values like 19.99.
    price: float

    # Quantity shows how many items are available in stock.
    quantity: int    

class ProductCreate(BaseModel):
    # Product name should be a string.
    name: str

    # Short description of the product.
    description: str

    # Price is stored as a float to allow decimal values like 19.99.
    price: float

    # Quantity shows how many items are available in stock.
    quantity: int