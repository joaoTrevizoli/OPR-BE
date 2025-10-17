from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    API_VERSION: str = '/v1'
    SECRET_KEY: str = os.environ.get('SECRET_KEY')
    ALGORITHM: str = 'HS256'
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    # Email / Password reset (Brevo) - keep same env-driven configuration
    BREVO_API_KEY: str | None = os.environ.get('BREVO_API_KEY')
    BREVO_FROM_EMAIL: str = os.environ.get('BREVO_FROM_EMAIL', 'coccidiology@labmet.com.br')
    PASSWORD_RESET_URL: str = os.environ.get('PASSWORD_RESET_URL')
    PASSWORD_RESET_EXPIRE_MINUTES: int = int(os.environ.get('PASSWORD_RESET_EXPIRE_MINUTES', '60'))

    # MongoDB connection (copy to opr DB using provided SRV)
    MONGODB_SETTINGS: list = [
        {
            'db': 'opr',
            'alias': 'opr_db',
            'host': 'mongodb+srv://joao_db_user:vkyTwOUlfmMcqYsG@cluster0.54mx9a4.mongodb.net/opr?retryWrites=true&w=majority&appName=Cluster0'
        }
    ]

settings = Settings()
