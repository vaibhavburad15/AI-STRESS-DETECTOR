import secrets
from datetime import datetime, timedelta
from typing import Optional

# In-memory storage for verification tokens (use Redis in production)
verification_tokens = {}

def generate_verification_token() -> str:
    """Generate a secure random verification token"""
    return secrets.token_urlsafe(32)

def store_verification_token(email: str, token: str, user_type: str, expires_in_hours: int = 24) -> bool:
    """Store verification token with expiration"""
    try:
        verification_tokens[email] = {
            "token": token,
            "user_type": user_type,
            "expires_at": datetime.utcnow() + timedelta(hours=expires_in_hours),
            "created_at": datetime.utcnow()
        }
        return True
    except Exception as e:
        print(f"Failed to store verification token: {e}")
        return False

def verify_token(email: str, token: str) -> Optional[dict]:
    """Verify token and return user_type if valid"""
    if email not in verification_tokens:
        return None
    
    stored_data = verification_tokens[email]
    
    # Check if token matches
    if stored_data["token"] != token:
        return None
    
    # Check if token expired
    if datetime.utcnow() > stored_data["expires_at"]:
        del verification_tokens[email]
        return None
    
    # Token is valid
    user_type = stored_data["user_type"]
    
    # Remove token after successful verification (one-time use)
    del verification_tokens[email]
    
    return {"user_type": user_type, "email": email}

def cleanup_expired_tokens():
    """Remove expired tokens (call this periodically)"""
    current_time = datetime.utcnow()
    expired_emails = [
        email for email, data in verification_tokens.items()
        if current_time > data["expires_at"]
    ]
    
    for email in expired_emails:
        del verification_tokens[email]
    
    if expired_emails:
        print(f"Cleaned up {len(expired_emails)} expired verification tokens")