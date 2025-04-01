from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    DATABASE: str
    USER_DB: str
    PASSWORD_DB: str
    HOST: str
    PORT: int

    DATABASE_URL: str

    # Selenium address
    SELENIUM_ADDRESS: str
    SELENIUM_PORT: int
