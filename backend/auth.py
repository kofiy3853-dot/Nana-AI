import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv

load_dotenv()

# Security configuration
SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'CHANGE_THIS_IN_PRODUCTION_USE_STRONG_SECRET')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Default credentials (CHANGE THESE!)
DEFAULT_USERNAME = os.getenv('NANA_USERNAME', 'admin')
DEFAULT_PASSWORD_HASH = os.getenv('NANA_PASSWORD_HASH', None)

# If no password hash is set, create one for 'admin123' (INSECURE - CHANGE THIS!)
if not DEFAULT_PASSWORD_HASH:
    DEFAULT_PASSWORD_HASH = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    print("⚠️  WARNING: Using default password 'admin123'. Set NANA_PASSWORD_HASH in .env!")

security = HTTPBearer()

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """Verify JWT token and return payload"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

def authenticate_user(username: str, password: str) -> bool:
    """Authenticate a user with username and password"""
    if username != DEFAULT_USERNAME:
        return False
    return verify_password(password, DEFAULT_PASSWORD_HASH)

def generate_password_hash(password: str) -> str:
    """Helper function to generate a password hash for .env file"""
    return hash_password(password)
