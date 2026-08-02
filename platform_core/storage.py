"""
storage.py — lớp bọc lưu file. Đổi được nơi lưu mà không sửa app nào.

Vì sao cần lớp này ngay từ đầu, dù hiện tại chỉ lưu ở đĩa máy chủ:

Cloudflare Tunnel chặn request body ở **100 MB** (Free/Pro). Hôm nay các app
xử lý file nhỏ thì không sao. Khi có app video, file vượt 100 MB là Cloudflare
trả HTTP 413 TRƯỚC KHI tới máy chủ — lúc đó phải chuyển sang cho trình duyệt
upload trực tiếp lên object storage (R2/S3) bằng presigned URL.

Nếu app gọi thẳng `open()` hay `boto3` thì lần chuyển đó phải sửa mọi app.
Nếu app chỉ gọi `storage.put()` / `storage.url_for()` thì chỉ cần thêm một
backend ở file này. Chi phí bây giờ: gần như bằng 0.

Hôm nay: LocalStorage (đĩa máy chủ, phục vụ qua route có kiểm tra quyền).
Sau này: R2Storage (presigned URL, trình duyệt tải trực tiếp từ CDN).
"""
from __future__ import annotations

import os
import pathlib
import secrets
import shutil
import time
from dataclasses import dataclass
from typing import BinaryIO, Optional

# Trần của Cloudflare Free/Pro cho request body. Kiểm ở tầng app để trả lỗi
# nói rõ nguyên nhân, thay vì để Cloudflare trả 413 trống không.
CLOUDFLARE_BODY_LIMIT = 100 * 1024 * 1024

DEFAULT_TTL_S = 15 * 60


@dataclass(frozen=True)
class StoredFile:
    key: str                  # đường dẫn logic, ví dụ "jobs/abc123/output.mp4"
    size: int
    content_type: str = "application/octet-stream"


@dataclass(frozen=True)
class UploadTarget:
    """Vé upload TRỰC TIẾP browser→storage (H10/P1). Backend R2 trả presigned
    PUT: trình duyệt tải file THẲNG lên R2, KHÔNG đi qua tunnel → né trần 100MB
    của Cloudflare. Backend cục bộ trả None → app tự nhận multipart qua route."""
    url: str
    key: str
    method: str = "PUT"
    headers: Optional[dict] = None


class StorageError(Exception):
    pass


class Storage:
    """Giao diện chung. App chỉ dùng những phương thức ở đây."""

    def put(self, key: str, stream: BinaryIO,
            content_type: str = "application/octet-stream") -> StoredFile:
        raise NotImplementedError

    def open(self, key: str) -> BinaryIO:
        raise NotImplementedError

    def delete(self, key: str) -> None:
        raise NotImplementedError

    def exists(self, key: str) -> bool:
        raise NotImplementedError

    def size(self, key: str) -> int:
        raise NotImplementedError

    def download_token(self, key: str, ttl_s: int = DEFAULT_TTL_S) -> str:
        """Vé tải file có hạn. Với R2 sau này đây sẽ là presigned URL."""
        raise NotImplementedError

    def resolve_token(self, token: str) -> Optional[str]:
        """token -> key, hoặc None nếu sai/hết hạn."""
        raise NotImplementedError

    def url_for(self, key: str, ttl_s: int = DEFAULT_TTL_S) -> Optional[str]:
        """URL tải TRỰC TIẾP file (H10). Backend đối tượng (R2) trả **presigned URL**
        để trình duyệt tải thẳng từ CDN — KHÔNG proxy qua tunnel (né trần 100MB).
        Backend cục bộ trả None → app tự serve qua route riêng như hiện tại."""
        return None

    def put_url(self, key: str, ttl_s: int = DEFAULT_TTL_S,
                content_type: str = "application/octet-stream") -> Optional[UploadTarget]:
        """Vé upload TRỰC TIẾP browser→storage (H10/P1). Backend R2 trả presigned
        PUT (trình duyệt PUT thẳng lên R2, né trần 100MB). Backend cục bộ trả
        None → app nhận multipart qua route như cũ (chỉ hợp file nhỏ)."""
        return None


def _safe_key(key: str) -> str:
    """Chặn path traversal.

    Một route tải file nhận key từ người dùng là đường rò kinh điển:
    `../../secrets/app.env` đọc được khoá mã hoá token. Chuẩn hoá và từ chối
    mọi thứ đi lên trên.
    """
    cleaned = key.replace("\\", "/").strip("/")
    if not cleaned:
        raise StorageError("key rỗng")
    parts = []
    for part in cleaned.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            raise StorageError(f"key không hợp lệ (đi ra ngoài): {key!r}")
        if ":" in part or part.startswith("~"):
            raise StorageError(f"key không hợp lệ: {key!r}")
        parts.append(part)
    if not parts:
        raise StorageError(f"key không hợp lệ: {key!r}")
    return "/".join(parts)


class LocalStorage(Storage):
    """Lưu ở đĩa máy chủ. Dùng cho giai đoạn đầu và cho file nhỏ.

    Vé tải giữ trong RAM. Đúng khi chỉ có một tiến trình web (kiến trúc hiện
    tại). Nếu sau này chạy nhiều worker thì vé phải chuyển sang DB, hoặc
    chuyển hẳn sang R2 presigned URL — lúc đó vấn đề tự biến mất.
    """

    def __init__(self, root: str):
        self.root = pathlib.Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._tokens: dict = {}

    def _path(self, key: str) -> pathlib.Path:
        return self.root / _safe_key(key)

    def put(self, key: str, stream: BinaryIO,
            content_type: str = "application/octet-stream") -> StoredFile:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Ghi ra file tạm rồi đổi tên: một lần ghi bị ngắt giữa đường không
        # để lại file hỏng mà vẫn "tồn tại".
        tmp = path.with_suffix(path.suffix + f".part{os.getpid()}")
        try:
            with open(tmp, "wb") as fh:
                shutil.copyfileobj(stream, fh, length=1024 * 1024)
            os.replace(tmp, path)
        finally:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
        return StoredFile(key=_safe_key(key), size=path.stat().st_size,
                          content_type=content_type)

    def open(self, key: str) -> BinaryIO:
        path = self._path(key)
        if not path.exists():
            raise StorageError(f"không có file: {key}")
        return open(path, "rb")

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def size(self, key: str) -> int:
        return self._path(key).stat().st_size

    def download_token(self, key: str, ttl_s: int = DEFAULT_TTL_S) -> str:
        key = _safe_key(key)
        if not self.exists(key):
            raise StorageError(f"không có file: {key}")
        self._prune()
        token = secrets.token_urlsafe(32)
        self._tokens[token] = (key, time.time() + ttl_s)
        return token

    def resolve_token(self, token: str) -> Optional[str]:
        self._prune()
        entry = self._tokens.get(token)
        if entry is None:
            return None
        key, expires = entry
        return key if time.time() < expires else None

    def _prune(self) -> None:
        now = time.time()
        for t in [t for t, (_k, exp) in self._tokens.items() if exp < now]:
            self._tokens.pop(t, None)


_storage: Optional[Storage] = None


class R2Storage(Storage):
    """Cloudflare R2 (S3-compatible) — H10. File lớn serve qua **presigned URL**
    (`url_for`): trình duyệt tải THẲNG từ R2, không proxy qua tunnel → né trần
    100MB. `boto3` nạp lười (không cài thì import storage.py vẫn chạy)."""

    def __init__(self, *, bucket: str, endpoint_url: str, access_key_id: str,
                 secret_access_key: str, region: str = "auto"):
        self.bucket = bucket
        self._endpoint = endpoint_url
        self._akid = access_key_id
        self._sk = secret_access_key
        self._region = region
        self._client = None

    def _c(self):
        if self._client is None:
            import boto3
            from botocore.config import Config
            self._client = boto3.client(
                "s3", endpoint_url=self._endpoint,
                aws_access_key_id=self._akid, aws_secret_access_key=self._sk,
                region_name=self._region, config=Config(signature_version="s3v4"))
        return self._client

    def put(self, key: str, stream: BinaryIO,
            content_type: str = "application/octet-stream") -> StoredFile:
        k = _safe_key(key)
        self._c().upload_fileobj(stream, self.bucket, k,
                                 ExtraArgs={"ContentType": content_type})
        return StoredFile(key=k, size=self.size(k), content_type=content_type)

    def open(self, key: str) -> BinaryIO:
        try:
            obj = self._c().get_object(Bucket=self.bucket, Key=_safe_key(key))
        except Exception as e:  # noqa: BLE001
            raise StorageError(f"R2 không đọc được: {key}") from e
        return obj["Body"]

    def delete(self, key: str) -> None:
        self._c().delete_object(Bucket=self.bucket, Key=_safe_key(key))

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError
        try:
            self._c().head_object(Bucket=self.bucket, Key=_safe_key(key))
            return True
        except ClientError:
            return False

    def size(self, key: str) -> int:
        return int(self._c().head_object(Bucket=self.bucket,
                                         Key=_safe_key(key))["ContentLength"])

    def url_for(self, key: str, ttl_s: int = DEFAULT_TTL_S) -> Optional[str]:
        return self._c().generate_presigned_url(
            "get_object", Params={"Bucket": self.bucket, "Key": _safe_key(key)},
            ExpiresIn=int(ttl_s))

    def put_url(self, key: str, ttl_s: int = DEFAULT_TTL_S,
                content_type: str = "application/octet-stream") -> Optional[UploadTarget]:
        # ContentType đưa vào Params -> presigned URL RÀNG BUỘC client phải gửi
        # đúng header Content-Type khi PUT, nếu không R2 trả 403 (chống lạm dụng vé).
        k = _safe_key(key)
        url = self._c().generate_presigned_url(
            "put_object",
            Params={"Bucket": self.bucket, "Key": k, "ContentType": content_type},
            ExpiresIn=int(ttl_s))
        return UploadTarget(url=url, key=k, method="PUT",
                            headers={"Content-Type": content_type})

    def download_token(self, key: str, ttl_s: int = DEFAULT_TTL_S) -> str:
        raise StorageError("R2 dùng url_for(), không dùng download_token")

    def resolve_token(self, token: str) -> Optional[str]:
        return None


def _r2_from_env() -> "R2Storage":
    acc = os.environ.get("LTT_R2_ACCOUNT_ID", "").strip()
    endpoint = (os.environ.get("LTT_R2_ENDPOINT", "").strip()
                or (f"https://{acc}.r2.cloudflarestorage.com" if acc else ""))
    akid = os.environ.get("LTT_R2_ACCESS_KEY_ID", "").strip()
    sk = os.environ.get("LTT_R2_SECRET_ACCESS_KEY", "").strip()
    bucket = os.environ.get("LTT_R2_BUCKET", "").strip()
    if not (endpoint and akid and sk and bucket):
        raise StorageError("R2 thiếu cấu hình LTT_R2_* (endpoint/key/bucket)")
    return R2Storage(bucket=bucket, endpoint_url=endpoint,
                     access_key_id=akid, secret_access_key=sk)


def _local() -> "LocalStorage":
    from core.runtime_paths import resolve_runtime_paths
    paths = resolve_runtime_paths()
    return LocalStorage(os.path.join(paths.data_dir, "files"))


def get_storage() -> Storage:
    """Storage dùng chung. `LTT_STORAGE=r2` + đủ `LTT_R2_*` → R2; ngược lại Local.
    R2 lỗi cấu hình → fallback Local (không làm sập app), có log."""
    global _storage
    if _storage is None:
        if os.environ.get("LTT_STORAGE", "").strip().lower() == "r2":
            try:
                _storage = _r2_from_env()
            except Exception as e:  # noqa: BLE001
                import logging
                logging.getLogger(__name__).error(
                    "R2 chưa cấu hình được, dùng LocalStorage: %s", e)
                _storage = _local()
        else:
            _storage = _local()
    return _storage


def set_storage(storage: Storage) -> None:
    """Cho test thay backend."""
    global _storage
    _storage = storage
