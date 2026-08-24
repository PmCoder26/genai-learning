from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import Base, engine, session
from database_models import Product


# ------------------------------------------------------------
# FastAPI app setup
# ------------------------------------------------------------
# FastAPI is a Python framework used to build REST APIs.
# REST APIs are web services that allow different software systems to
# communicate with each other over HTTP.
#
# app = FastAPI(...) creates the main application object.
# This object owns all the routes, validation logic, and request handling.
#
# title="..." is just metadata shown in the built-in docs.
# You can think of it as the API's display name.
app = FastAPI(title="Simple Advanced FastAPI Demo")

# Base.metadata.create_all(bind=engine)
# This tells SQLAlchemy to create tables in the database based on the ORM models.
# In simple terms: "if the table does not exist, create it automatically."
# This is helpful for learning and simple projects, but real apps often use
# migration tools like Alembic for database changes.
Base.metadata.create_all(bind=engine)


# ------------------------------------------------------------
# Database dependency
# ------------------------------------------------------------
# Depends(get_db) is one of the most important FastAPI features.
# It gives each route access to a database session without writing the session
# creation logic inside every endpoint.
#
# In FastAPI, a dependency is a reusable function that provides something
# required by a route, such as a database session, auth user, configuration,
# or shared logic.
#
# Here, get_db() creates a SQLAlchemy session before the request runs and closes
# it after the request completes. This prevents open database connections.
#
# yield is used in a generator function.
# It means: "create the resource, give it to the route, then clean it up later."
#
# Why use this pattern?
# - avoids repeating database session setup in every endpoint
# - keeps the code clean and reusable
# - ensures sessions are closed even if an error occurs

def get_db():
    db = session()
    try:
        yield db
    finally:
        db.close()


# ------------------------------------------------------------
# Pydantic models for request validation
# ------------------------------------------------------------
# Pydantic is a data validation library used by FastAPI.
# Its job is to check whether incoming data matches the expected structure.
# If the JSON body is invalid, FastAPI automatically returns a validation error
# before the endpoint logic even runs.
#
# BaseModel is a base class for creating request/response schemas.
# A schema is simply the expected shape of the data.
#
# Example:
# ProductCreate(name="Laptop", price=999.99)
# will be accepted only if the name is a string and price is a number > 0.

class ProductCreate(BaseModel):
    # Field(...) means the field is required.
    # It must be provided in the request body.
    # min_length and max_length validate string length.
    # gt=0 means the value must be greater than zero.
    name: str = Field(..., min_length=2, max_length=100)
    description: str = Field(..., min_length=5)
    price: float = Field(..., gt=0)
    quantity: int = Field(..., gt=0)


class ProductUpdate(BaseModel):
    # Optional[...] means the field may be missing from the request.
    # This is useful for PATCH or PUT update requests where the client sends
    # only the fields they want to change.
    #
    # default=None means if the field is not sent, its value is None.
    # min_length, max_length, gt=0 are validation rules that apply only when
    # the field is provided.
    name: Optional[str] = Field(default=None, min_length=3, max_length=100)
    description: Optional[str] = Field(default=None, min_length=5)
    price: Optional[float] = Field(default=None, gt=0)
    quantity: Optional[int] = Field(default=None, gt=0)


class ProductOut(BaseModel):
    # ProductOut defines the schema for the response returned to the client.
    # It tells FastAPI exactly what JSON shape to serialize.
    #
    # If the database model has extra fields, response_model lets you hide them
    # and return only the fields you want to expose.
    id: int
    name: str
    description: str
    price: float
    quantity: int


# ------------------------------------------------------------
# Root endpoint
# ------------------------------------------------------------
# @app.get("/") creates an HTTP GET route at the root path.
# A route is a combination of:
# - URL path (for example: "/")
# - HTTP method (GET, POST, PUT, DELETE, etc.)
#
# In simple terms: this is the homepage of the API.
# When a client visits http://localhost:8000/, the function below runs.
@app.get("/")
async def home():
    """Return a welcome message for the API."""
    return {"message": "Welcome to the FastAPI Advanced Routes Demo!"}


# ------------------------------------------------------------
# Read all products with pagination
# ------------------------------------------------------------
# Query parameters are values passed in the URL after ?
# Example: /products?page=2&limit=10
#
# page and limit here are not part of the path. They are query params.
# This is a very common pattern for pagination and filtering.
#
# Query(...) lets FastAPI validate those query parameters.
# ge=1 means page must be greater than or equal to 1.
# ge=1 and le=100 means limit must be between 1 and 100.
#
# db: Session = Depends(get_db)
# means: use the database session dependency created earlier.
@app.get("/products", response_model=list[ProductOut])
async def get_products(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Return a page of products using offset-based pagination."""
    # start calculates how many rows to skip before returning current page.
    # Example: page=1 -> start=0, page=2 -> start=10, page=3 -> start=20
    start = (page - 1) * limit

    # offset(start) skips the first 'start' rows.
    # limit(limit) restricts the query to 'limit' number of rows.
    # all() executes the query and returns all matching rows as a Python list.
    products = db.query(Product).offset(start).limit(limit).all()
    return products


# ------------------------------------------------------------
# Read one product by ID
# ------------------------------------------------------------
# /products/{product_id} is a path parameter route.
# The value inside the URL is captured and passed to the function.
# Example: /products/5 -> product_id becomes 5.
#
# We validate the id using the function parameter type: int.
# FastAPI automatically converts the URL value to an integer.
@app.get("/products/{product_id}", response_model=ProductOut)
async def get_product_by_id(product_id: int, db: Session = Depends(get_db)):
    """Return one product matching the given product_id."""
    # db.query(Product) starts a SQLAlchemy query against the Product table.
    # .filter(Product.id == product_id) means "find the row where the id matches".
    # .first() returns only the first matching row, or None if no row exists.
    db_product = db.query(Product).filter(Product.id == product_id).first()

    if db_product is None:
        # HTTPException is used to return a custom error response.
        # 404 means "not found".
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found",
        )

    return db_product


# ------------------------------------------------------------
# Create a product
# ------------------------------------------------------------
# POST is used for creating a new resource.
# The client sends data in the request body as JSON.
# FastAPI validates that JSON against ProductCreate automatically.
#
# product: ProductCreate means the request body should match the ProductCreate schema.
# If a field is missing or invalid, FastAPI returns a 422 validation error.
@app.post("/products", response_model=ProductOut)
async def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    """Create a new product and save it in the database."""
    # Create a SQLAlchemy ORM object from the validated request data.
    new_product = Product(
        name=product.name,
        description=product.description,
        price=product.price,
        quantity=product.quantity,
    )

    # db.add(obj) adds the object to the current database session.
    db.add(new_product)

    # db.commit() saves the transaction to the database.
    db.commit()

    # db.refresh(obj) reloads the object from the database so any generated
    # database values, such as the auto-incremented ID, are present.
    db.refresh(new_product)

    return new_product


# ------------------------------------------------------------
# Update a product
# ------------------------------------------------------------
# PUT is typically used for replacing or updating an entire resource.
# Here, we support partial updates by using ProductUpdate, where most fields are
# optional. This means a client can send only the values it wants to change.
#
# Example valid update payload:
# {
#   "price": 899.99
# }
#
# This is useful because the user does not need to send every field again.
@app.put("/products/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: int,
    product: ProductUpdate,
    db: Session = Depends(get_db),
):
    """Update a product using only the values provided in the request body."""
    # Find the existing product in the database.
    db_product = db.query(Product).filter(Product.id == product_id).first()

    if db_product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # product.model_dump(exclude_unset=True)
    # converts the Pydantic model into a normal Python dictionary.
    # exclude_unset=True means: keep only the fields the client actually sent.
    # This makes partial updates possible.
    update_data = product.model_dump(exclude_unset=True)

    # Loop through the provided fields and update the ORM object.
    # setattr(obj, field_name, value) is like obj.field_name = value.
    for key, value in update_data.items():
        if value is not None:
            setattr(db_product, key, value)

    # Save changes to the database.
    db.commit()

    # Refresh the ORM object so it matches the database state exactly.
    db.refresh(db_product)

    return db_product


# ------------------------------------------------------------
# Delete a product
# ------------------------------------------------------------
# DELETE is used to remove a resource from the database.
# Here, we first find the product by id, then delete it.
@app.delete("/products/{product_id}")
async def delete_product_by_id(product_id: int, db: Session = Depends(get_db)):
    """Delete a product by its ID."""
    db_product = db.query(Product).filter(Product.id == product_id).first()

    if db_product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # db.delete(obj) marks the row for deletion.
    db.delete(db_product)

    # db.commit() permanently deletes it from the database.
    db.commit()

    return None


# ------------------------------------------------------------
# Important learning notes
# ------------------------------------------------------------
# 1. Query parameters are used for filtering and pagination.
#    Example: /products?page=2&limit=10
#
# 2. Path parameters identify a single resource.
#    Example: /products/5
#
# 3. Pydantic models validate incoming JSON before your endpoint runs.
#    This prevents bad or incomplete data.
#
# 4. Optional fields are useful for partial updates.
#    Example: you may send only the price to change.
#
# 5. model_dump(exclude_unset=True) keeps only the fields explicitly sent by the client.
#    This is very helpful when doing updates.
#
# 6. db.refresh(obj) reloads the object from the database after commit.
#    This ensures the object is in sync with the database.
#
# 7. Depends(get_db) is a powerful FastAPI concept that manages resources like
#    database sessions automatically.
#
# 8. SQLAlchemy ORM lets you work with Python objects instead of raw SQL.
#    db.query(Product) is a query to the Product table.
#
# 9. HTTPException is how you return custom errors like 404 Not Found.
#
# 10. Response_model tells FastAPI what JSON shape to return to the client.
#     This keeps your API consistent and easy to document.