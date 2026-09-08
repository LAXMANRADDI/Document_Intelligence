from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    DATABASE_URL: str = "sqlite:///./data/app.db"

    class Config:
        env_file = ".env"


settings = Settings()
