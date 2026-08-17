from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PFAI_", env_file=".env", extra="ignore")

    # Local dev default. Override with PFAI_DATABASE_URL in real deployments.
    database_url: str = "postgresql+psycopg2://finance:finance@127.0.0.1:5432/finance"

    # Dev-only default signing key. MUST be overridden via PFAI_SECRET_KEY in prod.
    secret_key: str = "dev-insecure-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24h

    # Seeded demo account so the dashboard has data on first login.
    demo_email: str = "demo@financeai.app"
    demo_password: str = "demo1234"

    # --- Phase 2: LLM-assisted extraction (AWS Bedrock) ---
    # Off by default so the app runs with no cloud credentials. When enabled and
    # AWS credentials are present, the PDF upload path falls back to Bedrock for
    # statements the heuristic parser cannot read.
    llm_enabled: bool = False
    bedrock_model_id: str = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    aws_region: str = "us-east-1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
