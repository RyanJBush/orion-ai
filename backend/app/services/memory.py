from collections import defaultdict

from langchain_community.embeddings import FakeEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document


class MemoryService:
    def __init__(self) -> None:
        self._store: dict[int, list[str]] = defaultdict(list)
        self._embeddings = FakeEmbeddings(size=128)
        self._index = FAISS.from_texts(["bootstrap"], self._embeddings)

    def remember(self, task_id: int, content: str) -> None:
        self._store[task_id].append(content)
        self._index.add_documents([Document(page_content=content, metadata={"task_id": task_id})])

    def list_for_task(self, task_id: int) -> list[str]:
        return self._store.get(task_id, [])
