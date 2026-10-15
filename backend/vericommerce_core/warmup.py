"""Explicit free public-model cache preparation, never paid inference."""

from .retrieval import RetrievalEngine
from .settings import get_settings


def warmup() -> None:
    settings = get_settings()
    if not settings.embedding_enabled or not settings.embedding_download_allowed:
        raise SystemExit("Warmup requires explicit embedding enablement and download allowance")
    engine = RetrievalEngine(settings)
    engine.load()
    if engine.model is None:
        raise SystemExit("Free model warmup failed: " + engine.reason)
    print("Pinned CPU embedding model warmed successfully.")


if __name__ == "__main__":
    warmup()
