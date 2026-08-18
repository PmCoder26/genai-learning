from typing import Generator, List

from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database_models import Product
from database import Base, engine, session
from models import ProductUpdate, ProductResponse, ProductCreate


app = FastAPI(
    title="Simple Products API",
    description="An example FastAPI app using SQLAlchemy for a small product inventory.",
)


# Ensure database tables are created from SQLAlchemy models.
Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Create a database session for a request and ensure it is closed.

    Yields:
        Session: SQLAlchemy session bound to the engine.
    """
    db = session()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Populate the database with sample products if empty.

    This helper is intended for development and testing only.
    It checks whether any products exist and inserts a small sample set
    the first time the application starts.
    """
    db = session()
    try:
        # If the table is empty, add some example rows for manual testing.
        if db.query(Product).count() == 0:
            products = [
                Product(id=1, name="Phone", description="A smartphone", price=699.99, quantity=50),
                Product(id=2, name="Laptop", description="A powerful laptop", price=999.99, quantity=30),
                Product(id=5, name="Pen", description="A blue ink pen", price=1.99, quantity=100),
                Product(id=6, name="Table", description="A wooden table", price=199.99, quantity=20),
            ]
            for product in products:
                db.add(product)
            db.commit()
    except Exception:
        # Roll back on any failure and re-raise to surface the error.
        db.rollback()
        raise
    finally:
        db.close()


# Initialize sample data (safe no-op if already populated).
init_db()


# ----------------------
# API Endpoints
# ----------------------


@app.get("/", tags=["root"])
def greet() -> dict:
    """Return a friendly welcome message.

    Kept simple for the demo; returning a JSON object makes it easy
    for clients (and the auto-generated docs) to display.
    """
    return {"message": "Hello Developer, Welcome to FastAPI"}


@app.get("/products", response_model=List[ProductResponse])
def get_all_products(db: Session = Depends(get_db)) -> List[Product]:
    """Fetch and return all products from the database.

    Returns a list of `ProductResponse` objects which are Pydantic
    models that control the response shape and validation.
    """
    return db.query(Product).all()


@app.get("/products/{id}", response_model=ProductResponse)
def get_product_by_id(id: int, db: Session = Depends(get_db)) -> Product:
    """Return a single product by its numeric ID.

    Raises an HTTP 404 if the product does not exist.
    """
    product = db.query(Product).filter(Product.id == id).first()
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {id} not found.",
        )
    return product


@app.put("/products", response_model=ProductResponse)
def update_product(product: ProductUpdate, db: Session = Depends(get_db)) -> Product:
    """Update an existing product from the provided `ProductUpdate` model.

    If the product is not found, a 404 is raised. After updating, the
    endpoint returns the refreshed product instance.
    """
    db_product = db.query(Product).filter(Product.id == product.id).first()
    if db_product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product.id} not found.",
        )

    # Apply updates from the incoming model to the ORM instance.
    db_product.name = product.name
    db_product.description = product.description
    db_product.price = product.price
    db_product.quantity = product.quantity

    db.commit()
    db.refresh(db_product)
    return db_product


@app.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(product: ProductCreate, db: Session = Depends(get_db)) -> Product:
    """Create a new product from the provided `ProductCreate` model.

    The product `id` is assigned by the database (autoincrement) unless
    an explicit id is provided by the model/ORM. After commit we refresh
    to return the persisted object with its generated fields.
    """
    new_product = Product(
        name=product.name,
        description=product.description,
        price=product.price,
        quantity=product.quantity,
    )

    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product


@app.delete("/products/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product_by_id(id: int, db: Session = Depends(get_db)) -> None:
    """Delete a product by ID.

    Returns HTTP 204 No Content on success. If the product does not exist
    a 404 HTTPException is raised.
    """
    db_product = db.query(Product).filter(Product.id == id).first()
    if db_product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {id} not found.",
        )

    db.delete(db_product)
    db.commit()
    # 204 responses have no body so return None explicitly.
    return None