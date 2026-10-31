import uuid


class InMemoryStorage:
    """Test double for BlobStorage."""

    def __init__(self) -> None:
        self._blobs: dict[tuple[uuid.UUID, str], bytes] = {}

    def put(self, project_id: uuid.UUID, data: bytes) -> str:
        key = uuid.uuid4().hex
        self._blobs[(project_id, key)] = data
        return key

    def get(self, project_id: uuid.UUID, key: str) -> bytes:
        return self._blobs[(project_id, key)]

    def delete_project(self, project_id: uuid.UUID) -> None:
        for k in [k for k in self._blobs if k[0] == project_id]:
            del self._blobs[k]
