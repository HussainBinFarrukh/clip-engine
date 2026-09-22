import hashlib
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import BinaryIO

from app.core.config import settings

_CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True)
class StoredObject:
    storage_key: str
    byte_size: int
    checksum_sha256: str


class StorageProvider(ABC):
    @abstractmethod
    def put_bytes(self, asset_id: str, stream: BinaryIO, suffix: str) -> StoredObject: ...

    @abstractmethod
    def put_file(self, asset_id: str, source_path: Path, suffix: str) -> StoredObject: ...

    @abstractmethod
    def open_read(self, storage_key: str) -> BinaryIO: ...

    @abstractmethod
    def exists(self, storage_key: str) -> bool: ...

    @abstractmethod
    def delete(self, storage_key: str) -> None: ...

    @abstractmethod
    def resolve_path(self, storage_key: str) -> Path:
        """Return a local filesystem path for tools (ffprobe, etc.) that need one.

        Adapters that are not disk-backed (e.g. a future S3 adapter) must
        download to a temporary file and return that path.
        """
        ...


class LocalDiskStorageProvider(StorageProvider):
    def __init__(self, root: Path):
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    def _storage_key(self, asset_id: str, suffix: str) -> str:
        return f"{asset_id[:2]}/{asset_id}{suffix}"

    def _path_for(self, storage_key: str) -> Path:
        return self._root / storage_key

    def put_bytes(self, asset_id: str, stream: BinaryIO, suffix: str) -> StoredObject:
        storage_key = self._storage_key(asset_id, suffix)
        destination = self._path_for(storage_key)
        destination.parent.mkdir(parents=True, exist_ok=True)

        digest = hashlib.sha256()
        byte_size = 0
        with destination.open("wb") as out_file:
            while chunk := stream.read(_CHUNK_SIZE):
                digest.update(chunk)
                byte_size += len(chunk)
                out_file.write(chunk)

        return StoredObject(
            storage_key=storage_key, byte_size=byte_size, checksum_sha256=digest.hexdigest()
        )

    def put_file(self, asset_id: str, source_path: Path, suffix: str) -> StoredObject:
        storage_key = self._storage_key(asset_id, suffix)
        destination = self._path_for(storage_key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source_path), str(destination))

        digest = hashlib.sha256()
        byte_size = 0
        with destination.open("rb") as in_file:
            while chunk := in_file.read(_CHUNK_SIZE):
                digest.update(chunk)
                byte_size += len(chunk)

        return StoredObject(
            storage_key=storage_key, byte_size=byte_size, checksum_sha256=digest.hexdigest()
        )

    def open_read(self, storage_key: str) -> BinaryIO:
        return self._path_for(storage_key).open("rb")

    def exists(self, storage_key: str) -> bool:
        return self._path_for(storage_key).exists()

    def delete(self, storage_key: str) -> None:
        self._path_for(storage_key).unlink(missing_ok=True)

    def resolve_path(self, storage_key: str) -> Path:
        return self._path_for(storage_key)


@lru_cache
def get_storage_provider() -> StorageProvider:
    return LocalDiskStorageProvider(Path(settings.storage_root))
