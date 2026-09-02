"""
Simple JWT-authenticated FastAPI example with roles and password hashing.

This module provides a minimal demonstration of registration, login
and role-based authorization for educational purposes. It is **not**
meant for production as-is — secrets and configuration are kept inline
for clarity. See comments on each section for implementation notes and
security tradeoffs.
"""

from fastapi import FastAPI, Depends, HTTPException, status
from typing import Dict, Optional
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from database import Base, engine, session
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import Session


app = FastAPI(title = 'JWT Auth Demo')

class User(Base):
    """Basic ORM model representing a user.

    Columns:
    - `username`: primary key, used as the JWT subject.
    - `password`: stores the password hash (never store plaintext).
    - `role`: simple role string used for authorization checks.

    Note: In a production app you'd typically use an integer PK and
    stricter column types/lengths. This simplified model keeps the
    tutorial focused on auth flow.
    """

    __tablename__ = 'users'

    username = Column(String, primary_key = True, index = True)
    password = Column(String)
    role = Column(String, default = 'user')  # allowed: 'user', 'admin', 'moderator'

# Create tables for any models that don't exist yet. This uses
# SQLAlchemy's metadata.create_all which is safe for simple demos but
# not an alternative to a real migration system (Alembic) for
# production schemas.
Base.metadata.create_all(bind = engine)

# Backfill: ensure `role` column exists on older DBs where `users`
# may have been created before the `role` column was added. We try a
# Postgres-friendly `ALTER TABLE ... IF NOT EXISTS` inside a
# transaction and swallow errors from other DBs (SQLite, MySQL
# dialects may behave differently). This keeps startup resilient in
# local demos but a proper migration should be used in real apps.
from sqlalchemy import text
try:
    with engine.begin() as conn:
        conn.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR DEFAULT 'user'")
        )
except Exception:
    # Ignore failures here: the app will still function if the column
    # is already present or the DB doesn't support this SQL syntax.
    pass

# JWT configuration - keep these secret and configurable via env in
# real deployments. The `ACCESS_TOKEN_EXPIRE_MINUTES` controls token
# lifetime; shorter is more secure but requires more frequent refresh.
SECRET_KEY = 'IUTit589t45vtp945utnpciutir8tp86pv896P7676p667O&V^&L&O%&CL'
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing: use a modern KDF. The original tutorial used
# bcrypt; here we explicitly configure `pbkdf2_sha256` which avoids
# bcrypt's 72-byte input limit and reduces env-specific backend
# issues in local development. In production you may prefer bcrypt or
# argon2 after evaluating your environment and dependencies.
pwd_context = CryptContext(schemes=['pbkdf2_sha256'], deprecated='auto')

# OAuth2 scheme for token retrieval (login endpoint).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/auth/login')

class UserCreate(BaseModel):
    """Request model used for user registration.

    Validation rules keep usernames and passwords within reasonable
    bounds for the tutorial. Role defaults to `user` but tests or
    admin UIs could set it otherwise.
    """

    username: str = Field(..., min_length = 5, max_length = 50)
    password: str = Field(..., min_length = 8)
    role: str = Field(default = 'user')

class UserOut(BaseModel):
    """Response model returned after registration or when querying
    the authenticated user's info. Exposes only non-sensitive fields.
    """

    username: str
    role: str

class Token(BaseModel):
    access_token: str
    token_type: str = 'Bearer'

def get_db():
    """Dependency that yields a SQLAlchemy `Session` and ensures the
    session is closed after the request completes.

    Using a generator `yield` makes this function suitable as a
    FastAPI dependency (cleanup happens after response).
    """

    db = session()
    try:
        yield db
    finally:
        db.close()

def hash_password(password: str):
        """Hash a plaintext password using the configured KDF.

        Notes:
        - We defensively truncate to 72 bytes (UTF-8) to avoid hitting
            bcrypt's historical input limit if the backend changes to
            `bcrypt` later. Truncation happens on bytes and decodes with
            `errors='ignore'` to avoid breaking on partial multi-byte
            characters.
        - The function returns the encoded hash string produced by
            `passlib`'s CryptContext.
        """

        pw_bytes = password.encode('utf-8')
        if len(pw_bytes) > 72:
                # Truncate defensively; documentable trade-off: truncation can
                # reduce entropy for extremely long passwords, but avoids
                # runtime errors with bcrypt backends. For production, prefer
                # consistent policy and strong KDF selection.
                password = pw_bytes[:72].decode('utf-8', errors='ignore')
        return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored hash.

    `passlib` handles appropriate verification depending on the
    hash scheme stored in `hashed_password`.
    """

    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(username: str):
    """Create a short-lived JWT access token for `username`.

    The token payload uses the `sub` claim to store the username and
    sets an expiration (`exp`). The returned value is the encoded JWT
    string suitable for use as a Bearer token.
    """

    expire = datetime.utcnow() + timedelta(minutes = ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": username,
        "exp": expire 
    }

    return jwt.encode(payload, SECRET_KEY, algorithm = ALGORITHM)

def get_user_from_db(username: str, db: Session = Depends(get_db)):
    """Simple lookup helper to fetch a `User` by username.

    Using this function as a dependency makes it easy to mock or
    replace DB access in unit tests.
    """

    db_user = db.query(User).filter(User.username == username).first()
    return db_user

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Dependency that returns the authenticated `User` for the
    incoming request.

    Steps:
    1. Decode and validate the JWT token from the `Authorization`
       header using the configured `SECRET_KEY` and `ALGORITHM`.
    2. Extract the `sub` claim (username) and fetch the user from
       the database. If decoding fails or the user doesn't exist,
       raise 401 Unauthorized.
    """

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = get_user_from_db(username, db)
    if user is None:
        raise credentials_exception

    return user

# Authorization: check if user has required role
async def require_role(required_role: str):
    """Factory that returns a FastAPI dependency enforcing a single
    required role.

    Usage: `Depends(require_role('admin'))` on a route to restrict it
    to admins.
    """

    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {required_role}"
            )
        return current_user

    return role_checker

# Authorization: check if user has any of the required roles
async def require_any_role(required_roles: list):
    """Factory returning a dependency that allows access when the
    current user's role is in `required_roles`.

    Useful when multiple role levels may access the same endpoint
    (e.g. moderators and admins).
    """

    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {required_roles}"
            )
        return current_user

    return role_checker

@app.post('/auth/register', response_model = UserOut)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user.

    Workflow:
    - Ensure username is not already taken (409 Conflict when it is).
    - Hash the supplied password and store the user record.
    - Return the created user's public-facing info.

    Important: In production you'd typically:
    - Send a verification email before enabling the account.
    - Enforce stronger password policies and rate-limiting.
    """

    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user is not None:
        raise HTTPException(
            status_code = status.HTTP_409_CONFLICT,
            detail = 'User already registered, please login instead'
        )

    new_user = User(
        username = user.username,
        password = hash_password(user.password),
        role = user.role
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return { 'username': new_user.username, 'role': new_user.role }

@app.post('/auth/login', response_model = Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Authenticate a user and return a JWT access token.

    Uses `OAuth2PasswordRequestForm` so the endpoint is compatible with
    the OpenAPI OAuth2 password flow in the docs UI.
    """

    user = get_user_from_db(form_data.username, db)
    if user is None:
        # Avoid leaking which part failed (username vs password)
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = 'Incorrect username or password'
        )

    if not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = 'Incorrect username or password'
        )

    token = create_access_token(user.username)

    return { 'access_token': token, 'token_type': 'Bearer' }

# Protected routes with different authorization levels

@app.get('/users/me', response_model = UserOut)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Return public info for the currently authenticated user.

    Requires a valid JWT; FastAPI will surface a 401 response if the
    token is missing or invalid.
    """

    return { 'username': current_user.username, 'role': current_user.role }

@app.get('/admin/panel')
async def admin_panel(current_user: User = Depends(get_current_user)):
    """Example admin-only route. Checks `current_user.role` and
    returns 403 if the role is not `admin`.

    In a larger app prefer `Depends(require_role('admin'))` to centralize
    the authorization logic.
    """

    if current_user.role != 'admin':
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail = 'Only admins can access this resource'
        )
    return {
        'message': f'Welcome admin {current_user.username}',
        'admin_data': 'sensitive admin information',
        'users_count': 42
    }

@app.get('/moderator/reports')
async def moderator_reports(current_user: User = Depends(get_current_user)):
    """Reports accessible to moderators and admins.

    Demonstrates simple role checks allowing multiple roles.
    """

    if current_user.role not in ['admin', 'moderator']:
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail = 'Only moderators and admins can access this resource'
        )
    return {
        'message': f'Welcome {current_user.role} {current_user.username}',
        'reports': ['report1', 'report2', 'report3']
    }

@app.get('/products')
async def get_products(current_user: User = Depends(get_current_user)):
    """Example endpoint available to any authenticated user.

    Returns a static product list for demonstration purposes.
    """

    return {
        'message': f'Hello {current_user.username}',
        'products': [
            {'id': 1, 'name': 'Laptop', 'price': 999.99},
            {'id': 2, 'name': 'Phone', 'price': 699.99},
            {'id': 3, 'name': 'Tablet', 'price': 499.99}
        ]
    }

@app.delete('/admin/users/{username}')
async def delete_user(username: str, current_user: User = Depends(get_current_user)):
    """Admin-only user deletion example.

    This route demonstrates additional business logic checks such as
    preventing an admin from deleting their own account. Real deletion
    would remove the record from the database and handle referential
    integrity.
    """

    if current_user.role != 'admin':
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail = 'Only admins can delete users'
        )
    if current_user.username == username:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = 'Cannot delete your own account'
        )
    return { 'message': f'User {username} deleted successfully' }

@app.get('/user/profile')
async def user_profile(current_user: User = Depends(get_current_user)):
    """Return a small profile for the authenticated user."""

    return {
        'username': current_user.username,
        'role': current_user.role,
        'message': f'Profile of {current_user.username}'
    }

# Run the app
if __name__ == '__main__':
    import uvicorn
    uvicorn.run('fastapi_with_authentication_and_authorization:app', host='127.0.0.1', port=8000, reload=True)