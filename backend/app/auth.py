"""
Authentication utilities - JWT removed.
Keeping password hashing and simple session-less auth functions.
"""
import bcrypt
from fastapi import Header, HTTPException, status
from typing import Optional, List
from .database import users_collection, doctors_collection, admin_collection

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

def get_user_from_id(user_id: str) -> Optional[dict]:
    """Get user by ID from any collection"""
    from bson import ObjectId
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
    Instead of JWT, this uses X-User-ID header for simple authentication.
    The frontend should send the user_id in the X-User-ID header.
    """
    async def role_checker(x_user_id: Optional[str] = Header(None)):
        if not x_user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="X-User-ID header required"
            )
        
        user = get_user_from_id(x_user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        if user.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(allowed_roles)}"
            )
        
        # Return user info for use in the endpoint
        return {"user_id": str(user["_id"]), "role": user["role"], "email": user.get("email")}
    
    return role_checker
