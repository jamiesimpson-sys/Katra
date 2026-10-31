import uuid
from typing import Protocol


class BlobStorage(Protocol):
    """File storage, scoped by project. The encrypted local implementation arrives in M3."""

    def put(self, project_id: uuid.UUID, data: bytes) -> str:
        """Store bytes and return a blob key."""
        ...

    def get(self, project_id: uuid.UUID, key: str) -> bytes: ...

    def delete_project(self, project_id: uuid.UUID) -> None: ...
