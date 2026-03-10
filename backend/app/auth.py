"""
Authentication utilities - JWT-based authentication.
Provides secure JW token creation, validation, and role-based access control.
"""
import bcrypt
import jwt
import os
from fastapi import Header, HTTPException, status, Depends
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from .database import users_collection, doctors_collection, admin_collection
from bson import ObjectId

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    """Hash password"""
    # Truncate password to 72 bytes if necessary (bcrypt limitation)
    password_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def create_access_token(user_id: str, role: str, email: str) -> str:
    """Create JWT access token"""
    payload = {
        "user_id": user_id,
        "role": role,
        "email": email,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow()
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token

def verify_token(token: str) -> Dict[str, Any]:
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

def get_user_from_id(user_id: str) -> Optional[dict]:
    """Get user by ID from any collection"""
    try:
        # Try users collection
        user = users_collection.find_one({"_id": ObjectId(user_id)})
        if user:
            user["role"] = "user"
            return user
        
        # Try doctors collection
        user = doctors_collection.find_one({"_id": ObjectId(user_id)})
        if user:
            user["role"] = "doctor"
            return user
        
        # Try admin collection
        user = admin_collection.find_one({"_id": ObjectId(user_id)})
        if user:
            user["role"] = "admin"
            return user
            
        return None
    except Exception:
        return None

def require_role(allowed_roles: List[str]):
    """
    Dependency for requiring specific roles.
    Validates JWT token from Authorization header.
    """
    async def role_checker(authorization: Optional[str] = Header(None)):
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header required"
            )
        
        # Extract token from "Bearer <token>"
        try:
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                raise ValueError("Invalid auth scheme")
        except (ValueError, IndexError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format"
            )
        
        # Verify token
        payload = verify_token(token)
        
        user_id: Optional[str] = payload.get("user_id")
        role: Optional[str] = payload.get("role")
        
        if not user_id or not role:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Verify user still exists
        user = get_user_from_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Check role
        if role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(allowed_roles)}"
            )
        
        # Return user info for use in the endpoint
        return {"user_id": user_id, "role": role, "email": payload.get("email")}
    
    return role_checker

def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Get current authenticated user from JWT token"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required"
        )
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError("Invalid auth scheme")
    except (ValueError, IndexError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )
    
    payload = verify_token(token)
    user_id: Optional[str] = payload.get("user_id")
    role: Optional[str] = payload.get("role")
    
    if not user_id or not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Verify user still exists
    user = get_user_from_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return {"user_id": user_id, "role": payload.get("role"), "email": payload.get("email")}
