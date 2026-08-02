"""Local polling agent for Upscale Watch Folder.

No browser cookie or password is stored. Set LTT_UPSCALE_WATCH_TOKEN in the
agent process environment and keep its state directory outside the app install.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import time
from pathlib import Path

import httpx

ALLOWED = {".mp4", ".mov", ".mkv", ".avi", ".webm"}
MAX_BATCH = 3


def fingerprint(path: Path) -> str:
    stat = path.stat()
    raw = f"{path.resolve()}\0{stat.st_size}\0{stat.st_mtime_ns}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def stable_candidates(folder: Path, observations: dict, required: int = 2) -> list[Path]:
    ready = []
    present = set()
    for path in sorted(folder.iterdir()):
        if not path.is_file() or path.suffix.lower() not in ALLOWED:
            continue
        key = str(path.resolve()); present.add(key)
        stat = path.stat(); signature = [stat.st_size, stat.st_mtime_ns]
        old = observations.get(key, {})
        count = int(old.get("count", 0)) + 1 if old.get("signature") == signature else 1
        observations[key] = {"signature": signature, "count": count}
        if count >= required and stat.st_size > 0:
            ready.append(path)
    for key in list(observations):
        if key not in present:
            observations.pop(key, None)
    return ready[:MAX_BATCH]


def _move(path: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    destination = target / path.name
    if destination.exists():
        destination = target / f"{path.stem}-{int(time.time())}{path.suffix}"
    shutil.move(str(path), str(destination))


def submit_batch(base_url: str, token: str, paths: list[Path], timeout: float = 120.0) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    manifest = []
    files = []
    try:
        with httpx.Client(timeout=timeout) as client:
            status = client.get(base_url.rstrip("/") + "/upscalevideo/watch/status",
                                headers=headers)
            if status.status_code != 200 or not status.json().get("accepting"):
                return {"ok": False, "error": "Watch Agent paused by server",
                        "http_status": status.status_code if status.status_code != 200 else 402}
            for path in paths:
                ticket_response = client.post(
                    base_url.rstrip("/") + "/upscalevideo/watch/upload-url",
                    headers=headers, data={"filename": path.name,
                                           "content_type": "video/mp4"})
                ticket_response.raise_for_status(); ticket = ticket_response.json()
                key = ""
                if ticket.get("mode") == "direct":
                    with path.open("rb") as stream:
                        uploaded = client.request(ticket.get("method", "PUT"), ticket["url"],
                                                  headers=ticket.get("headers") or {},
                                                  content=stream)
                    uploaded.raise_for_status(); key = ticket["key"]
                else:
                    files.append(("videos", (path.name, path.open("rb"), "video/mp4")))
                manifest.append({"filename": path.name, "duration_s": 0,
                                 "request_id": fingerprint(path), "video_key": key})
            response = client.post(base_url.rstrip("/") + "/upscalevideo/watch/batch",
                                   headers=headers, data={"manifest": json.dumps(manifest)},
                                   files=files)
            data = response.json()
            data["http_status"] = response.status_code
            return data
    finally:
        for _, item in files:
            item[1].close()


def run_once(folder: Path, state_dir: Path, base_url: str, token: str) -> int:
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / "state.json"
    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        state = {"observations": {}}
    candidates = stable_candidates(folder, state.setdefault("observations", {}))
    temp = state_file.with_suffix(".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=True), encoding="utf-8")
    os.replace(temp, state_file)
    if not candidates:
        return 0
    try:
        result = submit_batch(base_url, token, candidates)
    except (httpx.HTTPError, OSError):
        return 2  # offline/transient: leave every source untouched
    if result.get("ok"):
        for path in candidates:
            _move(path, state_dir / "archive")
        return 0
    if int(result.get("http_status", 500)) in (401, 402, 429, 503):
        return 3  # revoked/insufficient/unavailable: pause, never quarantine
    for path in candidates:
        _move(path, state_dir / "quarantine")
    return 4


def main() -> int:
    parser = argparse.ArgumentParser(description="LTT Upscale Watch Agent")
    parser.add_argument("--folder", required=True)
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--interval", type=max_interval, default=5)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    token = os.environ.get("LTT_UPSCALE_WATCH_TOKEN", "").strip()
    if not token:
        raise SystemExit("LTT_UPSCALE_WATCH_TOKEN is required")
    folder, state_dir = Path(args.folder), Path(args.state_dir)
    if not folder.is_dir():
        raise SystemExit("Watch folder does not exist")
    while True:
        code = run_once(folder, state_dir, args.base_url, token)
        if args.once:
            return code
        time.sleep(args.interval)


def max_interval(value: str) -> int:
    return max(2, min(300, int(value)))


if __name__ == "__main__":
    raise SystemExit(main())
