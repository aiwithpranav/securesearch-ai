from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Required in .env (the env doctor checks these) ---
    app_env: str = "CHANGE_ME"
    app_secret_key: str = "CHANGE_ME"
    jwt_secret_key: str = "CHANGE_ME"
    postgres_user: str = "CHANGE_ME"
    postgres_password: str = "CHANGE_ME"
    postgres_db: str = "CHANGE_ME"
    database_url: str = "CHANGE_ME"
    redis_url: str = "CHANGE_ME"
    smtp_host: str = "CHANGE_ME"
    smtp_port: str = "CHANGE_ME"
    frontend_origin: str = "http://localhost:3000"

    # --- Object storage for uploaded files (Phase 3). Required, checked by the env doctor ---
    s3_endpoint_url: str = "CHANGE_ME"
    s3_access_key: str = "CHANGE_ME"
    s3_secret_key: str = "CHANGE_ME"
    s3_bucket: str = "CHANGE_ME"

    # --- Phase 3 tuning knobs. Safe defaults. ---
    s3_region: str = "us-east-1"  # SeaweedFS ignores it, but S3 signing needs some value
    embedding_model_path: str = "/opt/models/bge-small-en-v1.5"  # baked into the image at build time
    embedding_model_name: str = "BAAI/bge-small-en-v1.5"
    embedding_model_revision: str = "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"
    embedding_dimensions: int = 384
    embedding_batch_size: int = 16

    # --- Phase 5 retrieval knobs (blueprint: allow-list, full-text 30, vector 30, RRF k=60, rerank 20, keep 5 to 8) ---
    retrieval_mode: str = "hybrid"  # keyword | vector | hybrid
    retrieval_fts_limit: int = 30
    retrieval_vector_limit: int = 30
    retrieval_rrf_k: int = 60
    retrieval_rerank_candidates: int = 20
    retrieval_final_k: int = 8
    reranker_model_path: str = "/opt/models/bge-reranker-base"  # baked into the image at build time
    reranker_model_name: str = "BAAI/bge-reranker-base"
    reranker_model_revision: str = "2cfc18c9415c912f9d8155881c133215df768a70"
    search_limit_per_minute: int = 30  # NFR-03: per signed-in user
    search_concurrency: int = 2  # searches running at once (models use the CPU); others wait in line
    search_warmup: bool = True  # load both models in the background when the API starts

    # --- Phase 6 answers. The API key is optional: without it /ask answers 503 and everything else works. ---
    openai_api_key: str = ""  # set by the owner in .env only; never logged, never returned, never committed
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_timeout_seconds: int = 30
    llm_max_output_tokens: int = 500  # also the cost cap per answer
    answer_context_chunks: int = 6  # passages the model may read (blueprint: keep 5 to 8)
    chat_limit_per_minute: int = 10  # per person; every answer costs money at the provider
    preview_limit_per_minute: int = 60
    history_page_max: int = 50
    answer_min_score: float = 0.03  # provisional refusal threshold on the reranker score (ADR 028); tuned in Phase 7

    # --- Phase 3B upload and ingestion limits ---
    max_upload_bytes: int = 50 * 1024 * 1024  # NFR-03: 50 MB
    max_pdf_pages: int = 500
    max_docx_uncompressed_bytes: int = 200 * 1024 * 1024  # zip-bomb guard
    max_zip_ratio: int = 100  # one zip entry may not expand more than 100 times
    max_zip_entries: int = 5000
    max_extracted_chars: int = 5_000_000
    chunk_target_tokens: int = 450
    chunk_overlap_tokens: int = 50
    chunk_max_tokens: int = 500  # the model reads 512 tokens at most
    upload_limit_per_minute: int = 20
    ingest_time_limit_seconds: int = 600

    # --- Only needed by the demo-user seed script (Phase 2B) ---
    seed_user_password: str = ""

    # --- Auth tuning knobs. Safe defaults; override in .env only if needed. ---
    access_token_minutes: int = 15  # short-lived access token
    refresh_session_hours: int = 24  # "Remember me" unchecked: server-side cap
    refresh_remember_days: int = 7  # "Remember me" checked (blueprint: default 7, max 30)
    reset_token_minutes: int = 30  # password reset link lifetime
    invite_token_hours: int = 72  # invite link lifetime
    login_max_failures: int = 5  # wrong passwords before temporary lockout
    login_lockout_minutes: int = 15
    login_ip_limit_per_minute: int = 30
    forgot_ip_limit_per_15min: int = 5
    min_password_length: int = 12
    mail_from: str = "SecureSearch AI <noreply@securesearch.local>"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
