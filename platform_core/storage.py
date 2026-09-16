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

from platform_core.i18n import _ as _t
import logging
import os
import pathlib
import secrets
import shutil
import time
from dataclasses import dataclass
from typing import BinaryIO, Optional

log = logging.getLogger(__name__)

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

    def promote(self, staging_key: str, final_key: str,
                content_type: str = "application/octet-stream") -> StoredFile:
        """Chuyển artifact staging sang key bền vững rồi xóa bản staging.

        Backend có thể override bằng rename/copy server-side. Fallback này giữ
        contract đúng cho backend tùy biến, nhưng không tối ưu file lớn.
        """
        source = self.open(staging_key)
        try:
            stored = self.put(final_key, source, content_type=content_type)
        finally:
            source.close()
        self.delete(staging_key)
        return stored

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

    def local_path(self, key: str) -> Optional[str]:
        """Đường dẫn trên đĩa của `key`, hoặc None nếu backend không có đĩa.

        Cùng khuôn với `url_for()`: backend đối tượng (R2) trả None vì file
        không nằm trên máy này. Dùng cho công cụ NGOÀI tiến trình cần đọc file
        tại chỗ — ffprobe là ca thật — mà không phải sao chép qua `open()`.

        ⛔ Không dùng nó để đọc/ghi nội dung: đó là việc của `open()`/`put()`,
        và chỉ hai hàm đó mới đúng với mọi backend.
        """
        return None

    # ── Hai hàm dưới đây tồn tại để app KHÔNG phải tự bọc try/except ─────────
    #
    # Trước 2026-08-06, 14 chỗ gọi trong repo đều bọc `url_for`/`put_url` bằng
    # `except Exception:  # noqa: BLE001`, kèm chú thích "local storage has no
    # direct URL". Chú thích đó sai: backend cục bộ **trả None**, không ném.
    # Nên khối except ấy không hề bảo vệ thứ nó tự nhận — nó chỉ nuốt lỗi THẬT
    # của R2 (thiếu cấu hình, sai khoá, mất mạng) và lặng lẽ quay về phục vụ
    # file qua tunnel. Đúng thứ H10 sinh ra để tránh: người dùng vẫn tải được
    # cho tới khi gặp file lớn rồi đâm trần 100MB của Cloudflare, và không có
    # log nào chỉ ra vì sao.
    #
    # Ở đây vẫn degrade để một sự cố R2 tạm thời không làm hỏng cả trang, NHƯNG
    # ghi log ở mức exception để sự cố đó nhìn thấy được.
    def try_url_for(self, key: str, ttl_s: int = DEFAULT_TTL_S) -> Optional[str]:
        """`url_for()` nhưng không bao giờ ném. Thất bại bất ngờ được ghi log."""
        try:
            return self.url_for(key, ttl_s=ttl_s)
        except StorageError:
            return None                     # thiếu cấu hình / key sai: đã biết trước
        except Exception as exc:            # noqa: BLE001 - degrade nhưng phải thấy
            _log_storage_failure("Không tạo được URL tải trực tiếp", key, exc)
            return None

    def try_put_url(self, key: str, ttl_s: int = DEFAULT_TTL_S,
                    content_type: str = "application/octet-stream"
                    ) -> Optional[UploadTarget]:
        """`put_url()` nhưng không bao giờ ném. Thất bại bất ngờ được ghi log."""
        try:
            return self.put_url(key, ttl_s=ttl_s, content_type=content_type)
        except StorageError:
            return None
        except Exception as exc:            # noqa: BLE001 - degrade nhưng phải thấy
            _log_storage_failure("Không tạo được vé upload trực tiếp", key, exc)
            return None


def _log_storage_failure(message: str, key: str, exc: Exception) -> None:
    """Ghi lỗi storage có type/callsite nhưng không phát tán payload bí mật.

    ``logging.exception`` mặc định render nguyên message của exception. SDK
    provider có thể nhét credential/email vào đó, biến log thành kho secret.
    Ta vẫn đặt ``exc_info`` để hệ giám sát phân loại đây là exception, nhưng
    thay exception bằng bản đã lọc và không chuyển traceback chứa dữ liệu thô.
    """
    from platform_core.job_events import sanitize_text

    safe_key = sanitize_text(key, limit=500)
    safe_exc = RuntimeError(sanitize_text(
        f"{type(exc).__name__}: {exc}", limit=2000))
    log.error("%s cho %s", message, safe_key,
              exc_info=(type(safe_exc), safe_exc, None))


def _safe_key(key: str) -> str:
    """Chặn path traversal.

    Một route tải file nhận key từ người dùng là đường rò kinh điển:
    `../../secrets/app.env` đọc được khoá mã hoá token. Chuẩn hoá và từ chối
    mọi thứ đi lên trên.
    """
    cleaned = key.replace("\\", "/").strip("/")
    if not cleaned:
        raise StorageError(_t('key rỗng'))
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

    def local_path(self, key: str) -> Optional[str]:
        path = self._path(key)
        return str(path) if path.exists() else None

    def promote(self, staging_key: str, final_key: str,
                content_type: str = "application/octet-stream") -> StoredFile:
        source = self._path(staging_key)
        target = self._path(final_key)
        if not source.exists():
            raise StorageError(_t('không có file staging: {key}').format(
                key=staging_key))
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(source, target)
        return StoredFile(key=_safe_key(final_key), size=target.stat().st_size,
                          content_type=content_type)

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

    def promote(self, staging_key: str, final_key: str,
                content_type: str = "application/octet-stream") -> StoredFile:
        source = _safe_key(staging_key); target = _safe_key(final_key)
        self._c().copy_object(
            Bucket=self.bucket, Key=target,
            CopySource={"Bucket": self.bucket, "Key": source},
            MetadataDirective="COPY",
        )
        self._c().delete_object(Bucket=self.bucket, Key=source)
        return StoredFile(key=target, size=self.size(target), content_type=content_type)

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
        raise StorageError(_t('R2 dùng url_for(), không dùng download_token'))

    def resolve_token(self, token: str) -> Optional[str]:
        return None


class RoutedStorage(Storage):
    """Định tuyến theo TIỀN TỐ khoá: vài tiền tố ở đĩa máy chủ, còn lại ở backend chính.

    🔴 VÌ SAO (đo 15–16/09/2026, `docs/LTT_VOICE/GUI_DOI_SOAT_VA_PLAN_V2.md` W-KHO):

       · bucket R2 xoá object quá ~7 ngày (luật vòng đời ngoài ứng dụng) — nó đã
         xoá 56/58 tệp sinh trắc của 29 hồ sơ giọng, thứ phải sống vĩnh viễn;
       · toàn bucket lúc đo chỉ 37 object / 46 MB ⇒ R2 gần như không tốn tiền,
         nhưng cũng không mang lợi ích nào cho những tiền tố chỉ máy A đọc/ghi và
         chỉ phục vụ qua route của app (không `url_for`, không máy B).

    ⭐ Nền tảng KHÔNG biết tên app: tiền tố đến từ cấu hình
       (`LTT_STORAGE_LOCAL_PREFIXES`), không gõ cứng ở đây.

    ⛔ Chỉ đặt vào đây tiền tố mà KHÔNG nơi nào cần `url_for`/`put_url` (máy B,
       tải trực tiếp trình duyệt ↔ R2, ModelArk). Với khoá cục bộ hai hàm đó trả
       `None` — đúng hợp đồng Local, và bên gọi đã có đường lùi, nhưng một tiền tố
       sai sẽ âm thầm đẩy tệp lớn qua tunnel.
    """

    def __init__(self, *, chinh: Storage, cuc_bo: Storage, tien_to):
        self.chinh = chinh
        self.cuc_bo = cuc_bo
        self.tien_to = tuple(tien_to)

    def la_cuc_bo(self, key: str) -> bool:
        k = (key or "").replace("\\", "/").lstrip("/")
        return any(k.startswith(p) for p in self.tien_to)

    def _chon(self, key: str) -> Storage:
        return self.cuc_bo if self.la_cuc_bo(key) else self.chinh

    def put(self, key: str, stream: BinaryIO,
            content_type: str = "application/octet-stream") -> StoredFile:
        return self._chon(key).put(key, stream, content_type=content_type)

    def open(self, key: str) -> BinaryIO:
        return self._chon(key).open(key)

    def delete(self, key: str) -> None:
        self._chon(key).delete(key)

    def exists(self, key: str) -> bool:
        return self._chon(key).exists(key)

    def size(self, key: str) -> int:
        return self._chon(key).size(key)

    def promote(self, staging_key: str, final_key: str,
                content_type: str = "application/octet-stream") -> StoredFile:
        nguon, dich = self._chon(staging_key), self._chon(final_key)
        if nguon is dich:
            return nguon.promote(staging_key, final_key, content_type=content_type)
        # Khác backend: không có rename/copy phía server — chép qua luồng.
        return Storage.promote(self, staging_key, final_key, content_type=content_type)

    def download_token(self, key: str, ttl_s: int = DEFAULT_TTL_S) -> str:
        return self._chon(key).download_token(key, ttl_s=ttl_s)

    def resolve_token(self, token: str) -> Optional[str]:
        return self.cuc_bo.resolve_token(token) or self.chinh.resolve_token(token)

    def url_for(self, key: str, ttl_s: int = DEFAULT_TTL_S) -> Optional[str]:
        return self._chon(key).url_for(key, ttl_s=ttl_s)

    def put_url(self, key: str, ttl_s: int = DEFAULT_TTL_S,
                content_type: str = "application/octet-stream") -> Optional[UploadTarget]:
        return self._chon(key).put_url(key, ttl_s=ttl_s, content_type=content_type)

    def local_path(self, key: str) -> Optional[str]:
        return self._chon(key).local_path(key)


def tien_to_cuc_bo_tu_env() -> tuple:
    """`LTT_STORAGE_LOCAL_PREFIXES="voice/, abc/"` → `("voice/", "abc/")`.

    ⛔ Tiền tố PHẢI kết thúc bằng `/`. `voice` trần sẽ nuốt luôn `voiceover/…`
       của một app khác — bỏ qua và ghi log thay vì đoán ý.
    """
    import logging
    ra = []
    for phan in (os.environ.get("LTT_STORAGE_LOCAL_PREFIXES") or "").split(","):
        p = phan.strip().replace("\\", "/").lstrip("/")
        if not p:
            continue
        if not p.endswith("/") or ".." in p:
            logging.getLogger(__name__).error(
                "LTT_STORAGE_LOCAL_PREFIXES: bo qua tien to %r (phai ket thuc bang '/')", p)
            continue
        ra.append(p)
    return tuple(dict.fromkeys(ra))


def _r2_from_env() -> "R2Storage":
    acc = os.environ.get("LTT_R2_ACCOUNT_ID", "").strip()
    endpoint = (os.environ.get("LTT_R2_ENDPOINT", "").strip()
                or (f"https://{acc}.r2.cloudflarestorage.com" if acc else ""))
    akid = os.environ.get("LTT_R2_ACCESS_KEY_ID", "").strip()
    sk = os.environ.get("LTT_R2_SECRET_ACCESS_KEY", "").strip()
    bucket = os.environ.get("LTT_R2_BUCKET", "").strip()
    if not (endpoint and akid and sk and bucket):
        raise StorageError(_t('R2 thiếu cấu hình LTT_R2_* (endpoint/key/bucket)'))
    return R2Storage(bucket=bucket, endpoint_url=endpoint,
                     access_key_id=akid, secret_access_key=sk)


def _local() -> "LocalStorage":
    from platform_core.runtime_paths import resolve_runtime_paths
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
                # W-KHO: vài tiền tố ở đĩa máy chủ, xem `RoutedStorage`. Không
                # khai gì ⇒ giữ nguyên R2 cho mọi khoá như trước.
                tien_to = tien_to_cuc_bo_tu_env()
                if tien_to:
                    _storage = RoutedStorage(chinh=_storage, cuc_bo=_local(),
                                             tien_to=tien_to)
        else:
            _storage = _local()
    return _storage


def set_storage(storage: Storage) -> None:
    """Cho test thay backend."""
    global _storage
    _storage = storage
