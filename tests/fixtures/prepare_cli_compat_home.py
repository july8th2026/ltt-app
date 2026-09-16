"""Prepare an isolated HOME using the connector's real config writers."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOME = Path(sys.argv[1]).resolve()
MODEL = sys.argv[2]
BASE_URL = sys.argv[3]

spec = importlib.util.spec_from_file_location("cam_cli_smoke", ROOT / "tools" / "cam_cli.py")
cam = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(cam)
cam.NHA = HOME
cam.TEP_TRANG_THAI = HOME / ".ltt" / "cam_cli_trang_thai.json"
cam.TEP_CATALOG = HOME / ".codex" / "ltt_model_catalog.json"
cam.TEP_NHAT_KY = HOME / "AppData" / "Local" / "LTTStudios" / "cam-cli.log"

state = {"model": MODEL}
captured_env: dict[str, str] = {}
cam._setx = lambda name, value: (captured_env.__setitem__(name, value), True)[1]
cam._doc_env_nguoi_dung = lambda name: captured_env.get(name)
cam.cam_codex(BASE_URL, state, cho_vscode=False)
cam.cam_claude(BASE_URL, state, toan_cuc=True)
(HOME / "claude_env.json").write_text(
    json.dumps(captured_env, indent=2), encoding="utf-8", newline="\n")
print(json.dumps({"home": str(HOME), "model": MODEL,
                  "context": cam.hs_cua(MODEL).cua_so,
                  "compact": cam.hs_cua(MODEL).nen,
                  "claude_env": str(HOME / "claude_env.json")}))
