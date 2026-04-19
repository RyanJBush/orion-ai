from sqlalchemy.orm import Session

from app.models.memory import MemoryEntryModel, VectorMemoryModel


class MemoryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def put(self, namespace: str, key: str, text: str, metadata: dict) -> MemoryEntryModel:
        row = MemoryEntryModel(namespace=namespace, key=key, text=text, metadata_json=metadata)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_by_namespace(self, namespace: str) -> list[MemoryEntryModel]:
        return self.db.query(MemoryEntryModel).filter(MemoryEntryModel.namespace == namespace).all()


class VectorMemoryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, namespace: str, text: str, embedding: list[float]) -> VectorMemoryModel:
        row = VectorMemoryModel(namespace=namespace, text=text, embedding=embedding)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_by_namespace(self, namespace: str) -> list[VectorMemoryModel]:
        return self.db.query(VectorMemoryModel).filter(VectorMemoryModel.namespace == namespace).all()
