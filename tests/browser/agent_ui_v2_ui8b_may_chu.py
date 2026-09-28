"""May chu CO LAP de nghiem thu UI-8b (Agent Designer XEM TRUOC) — che do A.

⛔ KHONG chay tren cong 8100: may nay LA production. Cong **8211** rieng cho
   lan UI-8b — 8201-8210 da cap cho cac lan truoc (xem bang cong trong
   `docs/architecture/agent_ui_v2/00_SO_TIEN_DO.md`).

Khuon lay tu `tests/browser/agent_ui_v2_ui11_may_chu.py` (cung kho), ⛔ khong
tu bia — chi khac MOT dieu, ghi tai cho.

## Chay

    set AGENT_UI8B_FIXTURE_ROOT=<thu muc ngoai kho>
    python -m uvicorn tests.browser.agent_ui_v2_ui8b_may_chu:app ^
           --host 127.0.0.1 --port 8211

⚠️ Moi duong dan phai TUYET DOI va NGOAI kho — mot script dev neo theo `.` de
   rac vao chinh cay dang do.

## 🔴 KHAC MOT — khong goi LLM that

`POST /agent/api/v3/workflows/{id}/soan` (`agent_v3.py::v3_soan`) goi
`ke_hoach_v3.soan_draft` -> `planner.goi_model` -> dong co LLM noi bo that (may
B). Mot may chu THU cho GIAO DIEN khong can, va khong nen, keo mot lan goi that:
no ton hang doi + quota that ma khong lam UI-8b (mot lop hien thi THUAN o
client) dung hay sai hon. Thay `planner.goi_model` bang mot ham TAT DINH tra ve
DUNG mot do thi hai node co dinh — cung mot cach vitest da mock `soanWorkflowV3`
o tang frontend (`tests/CanvasShell.test.tsx`), chi khac tang: o day mock o
BIEN GIOI THAP NHAT co the (mot ham, khong phai ca tuyen HTTP), nen duong di
that CUA CODE (route -> soan_draft -> chuan_hoa -> bien_dich -> JSON tra ve)
van chay THAT — chi dau vao cua no la gia.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(os.environ["AGENT_UI8B_FIXTURE_ROOT"]).resolve()
ROOT.mkdir(parents=True, exist_ok=True)

os.environ["LTT_DATABASE_URL"] = f"sqlite:///{(ROOT / 'agent-ui8b.db').as_posix()}"
os.environ["LTT_DATA_DIR"] = str(ROOT / "data")
os.environ["LTT_ENV"] = "development"
os.environ["LTT_SESSION_SECRET"] = "agent-ui8b-browser-fixture"

config = ROOT / "config.json"
config.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1}),
                  encoding="utf-8")

#: Tai khoan fixture. Mat khau nam TRONG tep nay co chu dich: no la mot gia tri
#: thu, chi song trong sqlite cua thu muc scratchpad, va khong bao gio cham
#: production. Kich ban Playwright doc tu day, khong ai phai go tay.
EMAIL = "agent-ui8b@example.com"
PASSWORD = "Browser-ui8b-2026"

import platform_core.db as dbmod  # noqa: E402
import platform_core.models  # noqa: E402,F401
from platform_core.credit import cap_tay  # noqa: E402
from platform_core.models import User  # noqa: E402
from platform_core.users import tao_nguoi_dung  # noqa: E402

dbmod.Base.metadata.create_all(dbmod.get_engine())
gen = dbmod.get_session()
db = next(gen)
try:
    user = db.query(User).filter_by(email=EMAIL).one_or_none()
    if user is None:
        user = tao_nguoi_dung(db, email=EMAIL, password=PASSWORD,
                              is_verified=True)
        db.flush()
        cap_tay(db, user.id, 5000, by="fixture", note="UI-8b browser")
    db.commit()
finally:
    try:
        next(gen)
    except StopIteration:
        pass

# ── KHAC MOT: thay dong co LLM bang mot ham TAT DINH ────────────────────────
from platform_core.agent import planner  # noqa: E402


def _model_gia(_db, _prompt: str) -> str:
    """Tra mot do thi CO DINH: `text.chat` (giu) + `image.generate` (them) —
    du de lop xem truoc co ca "them" LAN "xoa" khi so voi mot canvas nguoi
    dung da tu dung tay (kich ban Playwright dung mot node `text.chat` khac,
    id khac, lam "buoc cu")."""
    # ⚠️ Id KHÔNG được có `-`: `bien_dich._doc_chuoi` phân tích tham chiếu
    #    `nodes.<id>.output.<cong>` bằng `ast.parse` (biểu thức Python thật) —
    #    `nodes.ai-n1.output.text` đọc thành `nodes.ai - n1.output.text` (một
    #    phép TRỪ), ⛔ không phải một tham chiếu. Bài học đo được 28/09 khi vá
    #    UI-8b: script kịch bản browser đầu tiên tự tạo lỗi này rồi tưởng là
    #    lỗi sản phẩm — id có gạch ngang là hợp lệ làm CanvasNode.id, nhưng
    #    KHÔNG hợp lệ khi bị TRÍCH DẪN trong một biểu thức tham số.
    return json.dumps({
        "nodes": [
            {"id": "ai_n1", "type": "app.text.chat",
             "params": {"prompt": "Tom tat noi dung"}},
            {"id": "ai_n2", "type": "app.image.generate",
             "params": {"prompt": "$ai_n1.text"}},
        ],
        "edges": [
            {"source": "ai_n1", "target": "ai_n2",
             "source_port": "text", "target_port": "prompt"},
        ],
    }, ensure_ascii=False)


planner.goi_model = _model_gia

from server.app import create_app  # noqa: E402

app = create_app(env={
    "LTT_ENV": "development",
    "LTT_CONFIG_PATH": str(config),
    "LTT_SESSION_SECRET": os.environ["LTT_SESSION_SECRET"],
    "LTT_ADMIN_USERNAME": "",
    "LTT_ADMIN_PASSWORD_HASH": "",
})
