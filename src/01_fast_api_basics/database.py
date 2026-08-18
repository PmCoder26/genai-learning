"""Database configuration for the tutorial FastAPI app.

This module exposes three names used elsewhere in the project:

- `engine`: SQLAlchemy Engine created from `DATABASE_URL`.
- `session`: a `sessionmaker` factory used to create DB sessions.
- `Base`: declarative base class for ORM models.

The file intentionally contains minimal logic — it reads `DATABASE_URL`
from the environment and builds the engine and session factory. No
fallbacks or extra runtime behavior are added here to keep the
configuration explicit and close to the original tutorial code.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base


# Read the database URL from the environment. The application using this
# module is expected to set `DATABASE_URL` (for example, a Postgres URL
# in production). If unset, `db_url` will be None and `create_engine`
# will raise an error — this matches the original tutorial behaviour.
db_url = os.getenv('DATABASE_URL')


# Create the SQLAlchemy engine from the URL. Keep the call simple so
# any environment-specific options (like `connect_args` for SQLite) can
# be applied by the developer when needed.
engine = create_engine(db_url)


# Configure the sessionmaker. The original code set `autoflush=False`
# and `autocommit=False`; we preserve those arguments exactly so the
# runtime behavior remains unchanged.
session = sessionmaker(autoflush=False, autocommit=False, bind=engine)


# Declarative base that ORM models should inherit from.
Base = declarative_base()