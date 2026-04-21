from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import MemoryScope, MemoryType, TimestampMixin


class MemoryEntryModel(TimestampMixin, Base):
    __tablename__ = "memory_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    namespace: Mapped[str] = mapped_column(String(128), index=True)
    key: Mapped[str] = mapped_column(String(128), index=True)
    text: Mapped[str] = mapped_column(Text)
    scope: Mapped[MemoryScope] = mapped_column(Enum(MemoryScope), default=MemoryScope.short_term, nullable=False)
    memory_type: Mapped[MemoryType] = mapped_column(Enum(MemoryType), default=MemoryType.fact, nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(256), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    superseded_by_id: Mapped[int | None] = mapped_column(ForeignKey("memory_entries.id"), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class VectorMemoryModel(TimestampMixin, Base):
    __tablename__ = "vector_memory"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    namespace: Mapped[str] = mapped_column(String(128), index=True)
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(JSON)
