"""NEXUS Local configuration.

All settings resolve to local resources. There is no cloud default anywhere.
Offline modes:
  - AIR_GAPPED: Network Guard blocks every outbound connection except loopback.
  - OFFLINE_READY: setup-time downloads permitted; Network Guard still logs.
"""
from __future__ import annotations

import enum
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OfflineMode(str, enum.Enum):
    AIR_GAPPED = "air_gapped"
    OFFLINE_READY = "offline_ready"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NEXUS_", env_file=".env", extra="ignore")

    workspace_dir: Path = Field(default=Path.home() / ".nexus-local")
    offline_mode: OfflineMode = OfflineMode.AIR_GAPPED
    network_guard_enabled: bool = True

    # Retrieval defaults (conservative for 6 GB VRAM machines; embedder is CPU).
    chunk_size_chars: int = 1200
    chunk_overlap_chars: int = 200
    retrieval_top_k: int = 8
    rrf_k: int = 60
    context_token_budget: int = 2048

    # Ingestion safety limits.
    max_file_size_bytes: int = 50 * 1024 * 1024
    allowed_extensions: tuple[str, ...] = (
        ".pdf", ".docx", ".txt", ".md", ".csv", ".json", ".jsonl",
        ".py", ".js", ".ts", ".ipynb", ".html",
    )

    # Model runtime. "mock" ships for tests; "ollama" for real local inference.
    llm_runtime: str = "mock"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:3b-instruct"  # fits 6 GB VRAM comfortably
    embedder: str = "hashing"  # "hashing" (zero-download) | "sentence-transformers"

    @property
    def db_path(self) -> Path:
        return self.workspace_dir / "nexus.db"

    def ensure_dirs(self) -> None:
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        (self.workspace_dir / "documents").mkdir(exist_ok=True)
        (self.workspace_dir / "indexes").mkdir(exist_ok=True)
        (self.workspace_dir / "exports").mkdir(exist_ok=True)


settings = Settings()
