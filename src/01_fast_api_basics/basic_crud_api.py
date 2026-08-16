from typing import Dict

from fastapi import FastAPI, HTTPException, status

from models import Product

# ------------------------------------------------------------
# FastAPI application setup
# ------------------------------------------------------------
# FastAPI is the primary framework used to build APIs in Python.
# The app object is the core of the application; it acts as the entry
# point for all routes (URLs) that clients call.
app = FastAPI(
    title="Product Inventory API",
    description="A simple CRUD API for learning FastAPI with an in-memory product database.",
    version="1.0.0",
)

# ------------------------------------------------------------
# In-memory storage
# ------------------------------------------------------------
# We use a Python dictionary here because this is a beginner example.
# In a real project, you would usually use a database such as SQLite,
# PostgreSQL, or MySQL. For now, this keeps everything simple and easy to
# understand.
#
# Key idea:
# - product_id is the dictionary key
# - Product object is the dictionary value
products_db: Dict[int, Product] = {}


# ------------------------------------------------------------
# Root endpoint
# ------------------------------------------------------------
# This route returns a welcome message so we can quickly check whether the
# API is running.
@app.get("/", tags=["General"])
async def home() -> dict:
    """Welcome message for the API."""
    return {"message": "Welcome to the Product Inventory API!"}


# ------------------------------------------------------------
# Read all products
# ------------------------------------------------------------
# GET requests are used to read or fetch data.
# response_model=list[Product] tells FastAPI that the output should match
# the Product schema and be serialized as JSON.
@app.get("/products", response_model=list[Product], tags=["Products"])
async def get_all_products() -> list[Product]:
    """Return all product records from the in-memory database."""
    return list(products_db.values())


# ------------------------------------------------------------
# Read one product by ID
# ------------------------------------------------------------
# URL parameter: /products/{product_id}
# Example: /products/1
@app.get("/products/{product_id}", response_model=Product, tags=["Products"])
async def get_product(product_id: int) -> Product:
    """Fetch a single product using its unique id."""
    product = products_db.get(product_id)

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} was not found.",
        )

    return product


# ------------------------------------------------------------
# Create a product
# ------------------------------------------------------------
# POST requests are used to create a new resource.
# The incoming request body is validated automatically according to the
# Product model before the function receives it.
@app.post(
    "/products",
    response_model=Product,
    status_code=status.HTTP_201_CREATED,
    tags=["Products"],
)
async def create_product(product: Product) -> Product:
    """Create a new product and save it in memory."""
    if product.id in products_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product with id {product.id} already exists.",
        )

    products_db[product.id] = product
    return product


# ------------------------------------------------------------
# Update an existing product
# ------------------------------------------------------------
# PUT is used to replace an existing resource with a new version.
# The route receives the product id from the URL and the new data from the body.
@app.put("/products/{product_id}", response_model=Product, tags=["Products"])
async def update_product(product_id: int, updated_product: Product) -> Product:
    """Replace the product data for the given id."""
    if product_id not in products_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} was not found.",
        )

    # Replace the old data stored under this id with the new Product.
    products_db[product_id] = updated_product
    return updated_product


# ------------------------------------------------------------
# Delete a product
# ------------------------------------------------------------
# DELETE removes a resource from the server.
@app.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Products"])
async def delete_product(product_id: int) -> None:
    """Delete a product from the storage dictionary."""
    if product_id not in products_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} was not found.",
        )

    del products_db[product_id]
    return None


# ------------------------------------------------------------
# Notes for learning CRUD
# ------------------------------------------------------------
# CRUD stands for:
#   Create -> POST
#   Read   -> GET
#   Update -> PUT
#   Delete -> DELETE
#
# Every endpoint below follows this pattern:
# 1. accept a request
# 2. validate the data
# 3. perform an operation on storage
# 4. return the output or raise an HTTP error
#
# Example flow:
# - POST /products -> create a product
# - GET /products -> list all products
# - GET /products/{id} -> fetch one product
# - PUT /products/{id} -> update one product
# - DELETE /products/{id} -> delete one product
#
# In actual applications, these operations connect to a database instead of
# a Python dictionary. This example is intentionally simple to teach the API
# pattern clearly.


# This block allows running the app directly with:
# python main.py
# and then using uvicorn to serve it.
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
