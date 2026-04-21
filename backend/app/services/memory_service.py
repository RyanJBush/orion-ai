import logging
import math
from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.common import MemoryScope, MemoryType
from app.repositories.memory_repository import MemoryRepository, VectorMemoryRepository
from app.schemas.memory import (
    MemoryCorrectionRequest,
    MemoryResult,
    MemorySearchRequest,
    MemorySummaryResponse,
    MemoryWriteRequest,
    MemoryWriteResponse,
    VectorWriteRequest,
)

logger = logging.getLogger(__name__)
SHORT_TERM_DEFAULT_TTL_SECONDS = 24 * 60 * 60


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

    @staticmethod
    def _resolve_expiry(scope: MemoryScope, ttl_seconds: int | None) -> datetime | None:
        if scope == MemoryScope.long_term:
            return None
        ttl = ttl_seconds if ttl_seconds is not None else SHORT_TERM_DEFAULT_TTL_SECONDS
        return datetime.now(timezone.utc) + timedelta(seconds=max(ttl, 1))

    def write_basic(self, payload: MemoryWriteRequest) -> MemoryWriteResponse:
        row = self.basic_repo.put(
            payload.namespace,
            payload.key,
            payload.text,
            payload.metadata,
            scope=payload.scope,
            memory_type=payload.memory_type,
            source_ref=payload.source_ref,
            expires_at=self._resolve_expiry(payload.scope, payload.ttl_seconds),
        )
        logger.info("memory.basic_written", extra={"memory_id": row.id, "namespace": row.namespace})
        return MemoryWriteResponse(
            id=row.id,
            namespace=row.namespace,
            key=row.key,
            scope=row.scope,
            memory_type=row.memory_type,
            expires_at=row.expires_at,
        )

    def write_vector(self, payload: VectorWriteRequest) -> MemoryWriteResponse:
        embedding = self._embed(payload.text)
        row = self.vector_repo.add(payload.namespace, payload.text, embedding)
        logger.info("memory.vector_written", extra={"memory_id": row.id, "namespace": row.namespace})
        return MemoryWriteResponse(
            id=row.id,
            namespace=row.namespace,
            key=None,
            scope=payload.scope,
            memory_type=payload.memory_type,
            expires_at=self._resolve_expiry(payload.scope, payload.ttl_seconds),
        )

    def search_vector(self, payload: MemorySearchRequest) -> list[MemoryResult]:
        query_embedding = self._embed(payload.query)
        rows = self.vector_repo.list_by_namespace(payload.namespace)
        scored = [
            MemoryResult(
                id=row.id,
                text=row.text,
                score=self._cosine(query_embedding, row.embedding),
                scope=payload.scope,
                memory_type=payload.memory_type,
            )
            for row in rows
        ]
        return sorted(scored, key=lambda item: item.score, reverse=True)[:5]

    def correct_basic_memory(self, entry_id: int, payload: MemoryCorrectionRequest) -> MemoryWriteResponse | None:
        existing = self.basic_repo.get(entry_id)
        if existing is None:
            return None
        replacement = self.basic_repo.put(
            existing.namespace,
            existing.key,
            payload.replacement_text,
            existing.metadata_json,
            scope=existing.scope,
            memory_type=existing.memory_type,
            source_ref=payload.source_ref or existing.source_ref,
            expires_at=existing.expires_at,
        )
        self.basic_repo.mark_superseded(existing, replacement.id)
        return MemoryWriteResponse(
            id=replacement.id,
            namespace=replacement.namespace,
            key=replacement.key,
            scope=replacement.scope,
            memory_type=replacement.memory_type,
            expires_at=replacement.expires_at,
        )

    def summarize_namespace(self, namespace: str) -> MemorySummaryResponse:
        rows = self.basic_repo.list_by_namespace(namespace)
        by_scope: dict[str, int] = {scope.value: 0 for scope in MemoryScope}
        by_type: dict[str, int] = {memory_type.value: 0 for memory_type in MemoryType}
        for row in rows:
            by_scope[row.scope.value] += 1
            by_type[row.memory_type.value] += 1
        latest_texts = [row.text for row in sorted(rows, key=lambda item: item.id, reverse=True)[:5]]
        return MemorySummaryResponse(
            namespace=namespace,
            total_entries=len(rows),
            by_scope=by_scope,
            by_type=by_type,
            latest_texts=latest_texts,
        )
