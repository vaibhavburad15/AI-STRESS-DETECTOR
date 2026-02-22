from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra='ignore'  # Ignore extra fields from .env
    )
    
    mongodb_url: str = "mongodb://localhost:27017/aistressdetector"
    
    # Email Configuration
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""  # Set in .env file
    smtp_password: str = ""  # Set in .env file (use App Password for Gmail)
    from_email: str = ""  # Set in .env file
    
    # OTP Configuration
    otp_expiry_minutes: int = 5
    otp_length: int = 6

settings = Settings()