from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LEARN_", env_file=".env")

    db_url: str = "sqlite:///learning.db"
    anki_url: str = "http://localhost:8765"
    anki_deck: str = "Learning Engine"
    anki_model: str = "Basic"


settings = Settings()