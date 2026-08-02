"""
runtime.py — tầng bọc Codex app-server cho SIDECAR (di trú từ BOT GEMINI
`app/providers/codex/runtime.py`, bản CHAT-ONLY).

Khác bản gốc:
- **Chỉ CHAT + ảnh**: ép sandbox `read-only` mọi lúc (bỏ work/plan/code/MCP/fork).
- **CODEX_HOME riêng của nền tảng** (`data/codex-home`) — KHÔNG đụng BOT GEMINI.
- Binary lấy từ gói pip `codex_cli_bin` (bundled, độc lập npm), env `CODEX_BIN` override.
- Auth: đăng nhập ChatGPT device-code HOẶC api key (người dùng chốt: ChatGPT OAuth).

Một AsyncCodex (một app-server) host nhiều thread; mỗi user/hội thoại một `cwd` riêng.
Chạy trong tiến trình sidecar (async) — web/worker gọi qua HTTP.
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import threading
from pathlib import Path
from typing import Optional

from openai_codex import AsyncCodex, CodexConfig, Sandbox, ApprovalMode

log = logging.getLogger(__name__)

try:
    from openai_codex.generated.v2_all import ReasoningEffort as _Effort
except Exception:  # noqa: BLE001
    _Effort = None
try:
    from openai_codex import TextInput as _TextInput, ImageInput as _ImageInput
except Exception:  # noqa: BLE001
    from openai_codex._inputs import TextInput as _TextInput, ImageInput as _ImageInput
try:
    from openai_codex import LocalImageInput as _LocalImageInput
except Exception:  # noqa: BLE001
    try:
        from openai_codex._inputs import LocalImageInput as _LocalImageInput
    except Exception:  # noqa: BLE001
        _LocalImageInput = None


def _data_dir() -> Path:
    """Thư mục data của nền tảng (dùng chung cách giải như storage.py)."""
    try:
        from core.runtime_paths import resolve_runtime_paths
        return Path(resolve_runtime_paths().data_dir)
    except Exception:  # noqa: BLE001
        return Path(os.environ.get("LTT_DATA_DIR") or ".").resolve()


CODEX_HOME = os.environ.get("CODEX_SERVER_HOME") or str(_data_dir() / "codex-home")
WORKSPACE_ROOT = Path(os.environ.get("CODEX_WORKSPACE_ROOT") or (_data_dir() / "codex-workspaces"))

DEFAULT_MODEL = os.environ.get("CODEX_MODEL", "gpt-5.6-sol")
APPROVAL_MODE = ApprovalMode.auto_review
CLIENT_NAME = "ltt-ai-studio"


class CodexNotConfigured(RuntimeError):
    """Runtime chưa sẵn sàng (chưa login / thiếu binary)."""


def _resolve_codex_bin() -> str:
    """codex.exe: env CODEX_BIN → gói pip codex_cli_bin (bundled) → npm-global fallback."""
    env_bin = os.environ.get("CODEX_BIN")
    if env_bin and Path(env_bin).exists():
        return env_bin
    try:
        import codex_cli_bin
        cand = Path(codex_cli_bin.__file__).resolve().parent / "bin" / (
            "codex.exe" if os.name == "nt" else "codex")
        if cand.exists():
            return str(cand)
    except Exception:  # noqa: BLE001
        pass
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        base = Path(appdata) / "npm" / "node_modules" / "@openai" / "codex"
        hits = list(base.glob("**/codex-win32-*/vendor/**/bin/codex.exe"))
        if hits:
            return str(hits[0])
    raise CodexNotConfigured("Không tìm thấy codex.exe (đặt env CODEX_BIN).")


_SAFE = re.compile(r"[^A-Za-z0-9_.-]")


def _safe(seg: str) -> str:
    s = _SAFE.sub("_", (seg or "").strip()).strip("._") or "default"
    return s[:80]


class CodexRuntime:
    """Một AsyncCodex (một app-server), host nhiều thread chat read-only."""

    def __init__(self) -> None:
        self._codex: Optional[AsyncCodex] = None
        self._bin: Optional[str] = None
        self._lock = threading.Lock()
        self._threads: dict = {}

    async def ensure_started(self) -> None:
        if self._codex is not None:
            return
        with self._lock:
            if self._codex is not None:
                return
            self._bin = _resolve_codex_bin()
            WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
            Path(CODEX_HOME).mkdir(parents=True, exist_ok=True)
            cfg = CodexConfig(codex_bin=self._bin,
                              env={**os.environ, "CODEX_HOME": CODEX_HOME},
                              experimental_api=True, client_name=CLIENT_NAME)
            self._codex = AsyncCodex(cfg)
            log.info("[codex] app-server started (bin=%s home=%s)", self._bin, CODEX_HOME)

    async def close(self) -> None:
        if self._codex is not None:
            try:
                await self._codex.close()
            except Exception:  # noqa: BLE001
                log.exception("[codex] close error")
            finally:
                self._codex = None

    def workspace_for(self, user_id: str, conv: str) -> Path:
        ws = WORKSPACE_ROOT / _safe(user_id) / _safe(conv)
        ws.mkdir(parents=True, exist_ok=True)
        return ws

    @staticmethod
    def effort_of(name: Optional[str]):
        if not name or _Effort is None:
            return None
        try:
            return _Effort(name)
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def build_turn_input(message: str, images: Optional[list] = None,
                         local_paths: Optional[list] = None):
        items = [_TextInput(message)]
        used_local = False
        if _LocalImageInput is not None:
            for p in (local_paths or []):
                if p:
                    items.append(_LocalImageInput(path=str(p)))
                    used_local = True
        if not used_local:
            for url in (images or []):
                if url:
                    items.append(_ImageInput(url=url))
        return items if len(items) > 1 else message

    @staticmethod
    def _developer_instructions(settings: dict) -> Optional[str]:
        # Chat thuần: nền tảng KHÔNG cho code. Chèn chỉ dẫn chat + custom của user.
        base = ("Bạn là trợ lý sáng tạo (chat + tạo ảnh). Trò chuyện, giải thích, tư "
                "vấn và tạo ảnh khi được yêu cầu. KHÔNG sửa file hệ thống, không chạy "
                "lệnh. Trả lời rõ ràng, thân thiện.")
        di = (settings.get("developer_instructions") or "").strip()
        return base + ("\n\n" + di if di else "")

    async def start_thread(self, user_id: str, conv: str, *, settings: Optional[dict] = None):
        await self.ensure_started()
        assert self._codex is not None
        settings = settings or {}
        ws = self.workspace_for(user_id, conv)
        th = await self._codex.thread_start(
            cwd=str(ws), sandbox=Sandbox("read-only"), approval_mode=APPROVAL_MODE,
            model=settings.get("model") or DEFAULT_MODEL,
            developer_instructions=self._developer_instructions(settings))
        self._threads[th.id] = th
        return th

    async def resume_thread(self, thread_id: str, user_id: str, conv: str,
                            *, settings: Optional[dict] = None):
        await self.ensure_started()
        assert self._codex is not None
        settings = settings or {}
        ws = self.workspace_for(user_id, conv)
        th = await self._codex.thread_resume(
            thread_id, cwd=str(ws), sandbox=Sandbox("read-only"),
            approval_mode=APPROVAL_MODE,
            developer_instructions=self._developer_instructions(settings))
        self._threads[thread_id] = th
        return th

    async def get_thread(self, thread_id: str, user_id: str, conv: str,
                         *, settings: Optional[dict] = None):
        th = self._threads.get(thread_id)
        if th is not None:
            return th
        return await self.resume_thread(thread_id, user_id, conv, settings=settings)

    def evict_thread(self, thread_id: str) -> None:
        self._threads.pop(thread_id, None)

    async def list_models(self) -> list:
        await self.ensure_started()
        assert self._codex is not None
        ml = await self._codex.models(include_hidden=False)
        out = []
        for m in ml.data:
            mods = [getattr(x, "value", str(x)) for x in (getattr(m, "input_modalities", None) or [])]
            out.append({"id": m.id, "display_name": getattr(m, "display_name", m.id),
                        "description": getattr(m, "description", "") or "",
                        "input_modalities": mods, "vision": "image" in mods})
        return out

    async def account(self) -> dict:
        await self.ensure_started()
        assert self._codex is not None
        acc = await self._codex.account()
        try:
            return acc.model_dump(mode="json") if hasattr(acc, "model_dump") else dict(acc)
        except Exception:  # noqa: BLE001
            return {"raw": str(acc), "requires_openai_auth": getattr(acc, "requires_openai_auth", None)}

    async def capabilities(self) -> dict:
        await self.ensure_started()
        assert self._codex is not None
        try:
            from openai_codex.generated.v2_all import ModelProviderCapabilitiesReadResponse
            caps = await self._codex._client.request(
                "modelProvider/capabilities/read", {},
                response_model=ModelProviderCapabilitiesReadResponse)
            d = caps.model_dump(mode="json")
            return {"image_generation": bool(d.get("image_generation")),
                    "web_search": bool(d.get("web_search"))}
        except Exception as e:  # noqa: BLE001
            log.warning("[codex] capabilities error: %s", e)
            return {"image_generation": False, "web_search": False}

    async def rate_limits(self) -> dict:
        await self.ensure_started()
        assert self._codex is not None
        try:
            from openai_codex.generated.v2_all import GetAccountRateLimitsResponse
            resp = await self._codex._client.request(
                "account/rateLimits/read", {}, response_model=GetAccountRateLimitsResponse)
            return resp.model_dump(mode="json")
        except Exception as e:  # noqa: BLE001
            return {"error": str(e)}

    # ── Login (device-code ChatGPT hoặc api key) ──────────────────────────────
    async def login_api_key(self, api_key: str) -> None:
        await self.ensure_started()
        assert self._codex is not None
        await self._codex.login_api_key(api_key)

    async def start_device_login(self):
        await self.ensure_started()
        assert self._codex is not None
        return await self._codex.login_chatgpt_device_code()

    async def logout(self) -> None:
        await self.ensure_started()
        assert self._codex is not None
        await self._codex.logout()

    async def reload(self) -> None:
        """Restart app-server (đọc auth.json mới)."""
        await self.close()
        self._threads.clear()
        await self.ensure_started()


_runtime: Optional[CodexRuntime] = None


def get_runtime() -> CodexRuntime:
    global _runtime
    if _runtime is None:
        _runtime = CodexRuntime()
    return _runtime
