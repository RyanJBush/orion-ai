import logging
import math
from collections import Counter

from sqlalchemy.orm import Session

from app.repositories.memory_repository import MemoryRepository, VectorMemoryRepository
from app.schemas.memory import MemoryResult, MemorySearchRequest, MemoryWriteRequest, VectorWriteRequest

logger = logging.getLogger(__name__)


class MemoryService:
    def __init__(self, db: Session) -> None:
        self.basic_repo = MemoryRepository(db)
        self.vector_repo = VectorMemoryRepository(db)

    @staticmethod
    def _embed(text: str) -> list[float]:
        tokens = [tok.lower() for tok in text.split() if tok.strip()]
        counts = Counter(tokens)
        vocabulary = ["task", "workflow", "agent", "memory", "tool", "run", "step", "error"]
        return [float(counts.get(token, 0)) for token in vocabulary]

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def write_basic(self, payload: MemoryWriteRequest) -> dict[str, str | int]:
        row = self.basic_repo.put(payload.namespace, payload.key, payload.text, payload.metadata)
        logger.info("memory.basic_written", extra={"memory_id": row.id, "namespace": row.namespace})
        return {"id": row.id, "namespace": row.namespace, "key": row.key}

    def write_vector(self, payload: VectorWriteRequest) -> dict[str, str | int]:
        embedding = self._embed(payload.text)
        row = self.vector_repo.add(payload.namespace, payload.text, embedding)
        logger.info("memory.vector_written", extra={"memory_id": row.id, "namespace": row.namespace})
        return {"id": row.id, "namespace": row.namespace}

    def search_vector(self, payload: MemorySearchRequest) -> list[MemoryResult]:
        query_embedding = self._embed(payload.query)
        rows = self.vector_repo.list_by_namespace(payload.namespace)
        scored = [
            MemoryResult(id=row.id, text=row.text, score=self._cosine(query_embedding, row.embedding))
            for row in rows
        ]
        return sorted(scored, key=lambda item: item.score, reverse=True)[:5]
