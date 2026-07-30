"""
Test driver chạy thủ công — đăng video thật lên FB Page + TikTok Draft.

Mục đích: kiểm tra end-to-end pipeline mà không cần GUI. Capture log đầy đủ
ra file, in stdout, và trả về exit code.

Cách dùng:
    python scripts/_manual_test_run.py                # chạy cả FB + TT
    python scripts/_manual_test_run.py --tiktok-only  # chỉ TT
    python scripts/_manual_test_run.py --fb-only      # chỉ FB
"""
from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

# ── Setup ──────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

LOG_PATH = ROOT / "data" / "manual_test_run.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

# Buộc UTF-8 cho mọi stream để khỏi crash unicode trên Windows CMD
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

_log_lines: list[str] = []


def _emit(prefix: str, msg: str, level: str = "info"):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] [{prefix:<8}] [{level:<7}] {msg}"
    _log_lines.append(line)
    print(line)


def _flush_log():
    LOG_PATH.write_text("\n".join(_log_lines) + "\n", encoding="utf-8")


# Wire python logging to capture engine internals too
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)


# ── Test parameters ───────────────────────────────────────────────────────────

DOWNLOADS = Path(r"C:\Users\KENLY\Downloads")

FB_VIDEO = DOWNLOADS / "Tạo_Video_Chim_Ruồi_Quay_Chậm.mp4"
FB_PAGE  = "KL Closet"
FB_TITLE = "[TEST] Chim ruồi quay chậm"
FB_DESC  = (
    "Bot upload test — video chim ruồi siêu thực, slow motion 8s.\n"
    "Đây là post test tự động từ LTTStudio VideoBot.\n"
    "#test #slowmotion #bot"
)

TT_VIDEO = DOWNLOADS / "014-scene_id-14-video_duration-8s-visual_style-premium-05342013.mp4"
TT_OPEN_ID_DISPLAY = "klcloset96"
TT_TITLE = "Bot health-check — premium 8s"
TT_DESC  = "#test #bot #healthcheck"


# ── Config loader ─────────────────────────────────────────────────────────────

def load_config() -> dict:
    cfg_path = ROOT / "data" / "config.json"
    with cfg_path.open("r", encoding="utf-8") as f:
        return json.load(f)


# ── FB test ───────────────────────────────────────────────────────────────────

def run_fb_test(config: dict) -> bool:
    _emit("FB", f"Bắt đầu test Facebook upload → page='{FB_PAGE}'")
    if not FB_VIDEO.exists():
        _emit("FB", f"❌ FILE KHÔNG TỒN TẠI: {FB_VIDEO}", "error")
        return False

    from core.upload_engine import UploadEngine
    from server.services.ui_constants import PRIVACY_OPTIONS

    stop_event = threading.Event()
    result_status = {"value": None, "link": ""}

    def _on_log(msg, level="info"):
        _emit("FB-eng", str(msg), str(level))

    def _on_status(msg):
        _emit("FB-eng", f"status: {msg}", "info")

    def _on_result(task, status, link):
        result_status["value"] = status
        result_status["link"]  = link or ""
        _emit("FB", f"on_result: status={status}  link={link}", "info")

    def _on_done():
        _emit("FB", "on_done fired", "info")

    def _on_error(msg):
        _emit("FB", f"on_error: {msg}", "error")

    engine = UploadEngine(
        config     = config,
        stop_event = stop_event,
        on_log     = _on_log,
        on_status  = _on_status,
        on_result  = _on_result,
        on_done    = _on_done,
        on_error   = _on_error,
    )

    task = {
        "video_path":  str(FB_VIDEO),
        "page":        FB_PAGE,
        "title":       FB_TITLE,
        "description": FB_DESC,
        "thumbnail":   "",
        "privacy":     PRIVACY_OPTIONS["Công khai"],  # Page posts đều public
        "schedule":    "",
    }

    t0 = time.time()
    try:
        engine.run(task)
    except Exception as exc:
        _emit("FB", f"engine.run raised: {exc}\n{traceback.format_exc()}", "error")
        return False
    elapsed = time.time() - t0
    _emit("FB", f"Hoàn tất sau {elapsed:.1f}s", "info")
    return result_status["value"] == "success"


# ── TT test ───────────────────────────────────────────────────────────────────

def run_tt_test(config: dict) -> bool:
    _emit("TT", f"Bắt đầu test TikTok Draft upload → account='{TT_OPEN_ID_DISPLAY}'")
    if not TT_VIDEO.exists():
        _emit("TT", f"❌ FILE KHÔNG TỒN TẠI: {TT_VIDEO}", "error")
        return False

    from core.tiktok.publisher_service import TikTokPublisher
    from core.tiktok.token_store import get_default_store as get_tt

    # Lookup open_id từ display_name
    store = get_tt()
    open_id = None
    for a in store.all_accounts():
        if a.display_name == TT_OPEN_ID_DISPLAY:
            open_id = a.open_id
            break
    if not open_id:
        _emit("TT", f"❌ Không tìm thấy TT account '{TT_OPEN_ID_DISPLAY}'", "error")
        return False
    _emit("TT", f"Resolved open_id={open_id[:16]}…", "info")

    stop_event = threading.Event()

    def _on_log(msg, level="info"):
        _emit("TT-pub", str(msg), str(level))

    def _on_status(msg):
        _emit("TT-pub", f"status: {msg}", "info")

    task = {
        "video_path":       str(TT_VIDEO),
        "account":          open_id,
        "title":            TT_TITLE,
        "description":      TT_DESC,
        "post_type":        "tiktok_draft",
        "privacy_level":    "",
        # user_confirmed_at: dùng UTC ISO (advisory check trong compliance_guard)
        "user_confirmed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    publisher = TikTokPublisher(
        config     = config,
        stop_event = stop_event,
        on_log     = _on_log,
        on_status  = _on_status,
    )

    t0 = time.time()
    try:
        result = publisher.publish(task)
        elapsed = time.time() - t0
        _emit(
            "TT",
            f"✅ result: publish_id={result.external_post_id}  "
            f"status={result.status}  ({elapsed:.1f}s)",
            "success",
        )
        return True
    except Exception as exc:
        _emit("TT", f"❌ publish() raised: {exc}", "error")
        _emit("TT", traceback.format_exc(), "debug")
        return False


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    run_fb = True
    run_tt = True
    if "--fb-only" in args:
        run_tt = False
    if "--tiktok-only" in args:
        run_fb = False

    _emit("MAIN", "===== Manual test driver bắt đầu =====")
    try:
        config = load_config()
        _emit("MAIN", f"Loaded config — graph_api={config.get('graph_api_version')}")
    except Exception as exc:
        _emit("MAIN", f"❌ Không đọc được config: {exc}", "error")
        _flush_log()
        sys.exit(2)

    results = {}
    if run_tt:
        _emit("MAIN", "─" * 60)
        results["tiktok"] = run_tt_test(config)
    if run_fb:
        _emit("MAIN", "─" * 60)
        results["facebook"] = run_fb_test(config)

    _emit("MAIN", "─" * 60)
    _emit("MAIN", f"Kết quả: {results}")
    _flush_log()

    # Exit code: 0 nếu tất cả pass
    sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        _emit("MAIN", "Người dùng ngắt (Ctrl+C)", "warning")
        _flush_log()
        sys.exit(130)
