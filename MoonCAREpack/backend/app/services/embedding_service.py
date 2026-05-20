try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SentenceTransformer = None
    SENTENCE_TRANSFORMERS_AVAILABLE = False


class EmbeddingService:
    def __init__(self):
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError("sentence-transformers not installed. Please run: pip install sentence-transformers")
        self._model = None
        self._model_loading_failed = False
        self._loading_tried = False

    def _ensure_model(self):
        if self._loading_tried:
            return
        self._loading_tried = True

        if self._model is None and not self._model_loading_failed:
            try:
                # Only try once, no retries
                self._model = SentenceTransformer("all-MiniLM-L6-v2")
            except Exception as e:
                print(f"[EmbeddingService] 模型加载失败: {e}")
                self._model_loading_failed = True
                self._model = None

    def embed(self, text: str) -> list[float]:
        self._ensure_model()
        if self._model is None:
            raise RuntimeError("Embedding model not available")
        return self._model.encode(text).tolist()