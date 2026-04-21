from datetime import datetime, timezone

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.memory import MemoryEntryModel, VectorMemoryModel


class MemoryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def put(
        self,
        namespace: str,
        key: str,
        text: str,
        metadata: dict,
        *,
        scope,
        memory_type,
        source_ref: str | None,
        expires_at,
    ) -> MemoryEntryModel:
        row = MemoryEntryModel(
            namespace=namespace,
            key=key,
            text=text,
            metadata_json=metadata,
            scope=scope,
            memory_type=memory_type,
            source_ref=source_ref,
            expires_at=expires_at,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_by_namespace(self, namespace: str) -> list[MemoryEntryModel]:
        now = datetime.now(timezone.utc)
        return (
            self.db.query(MemoryEntryModel)
            .filter(MemoryEntryModel.namespace == namespace)
            .filter(MemoryEntryModel.superseded_by_id.is_(None))
            .filter(or_(MemoryEntryModel.expires_at.is_(None), MemoryEntryModel.expires_at > now))
            .all()
        )

    def get(self, entry_id: int) -> MemoryEntryModel | None:
        return self.db.get(MemoryEntryModel, entry_id)

    def mark_superseded(self, entry: MemoryEntryModel, replacement_id: int) -> MemoryEntryModel:
        entry.superseded_by_id = replacement_id
        self.db.commit()
        self.db.refresh(entry)
        return entry


class VectorMemoryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, namespace: str, text: str, embedding: list[float], metadata: dict | None = None) -> VectorMemoryModel:
        row = VectorMemoryModel(namespace=namespace, text=text, embedding=embedding)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_by_namespace(self, namespace: str) -> list[VectorMemoryModel]:
        return self.db.query(VectorMemoryModel).filter(VectorMemoryModel.namespace == namespace).all()
