"""Bounded one-shot planner using api_pool; execution never happens here."""
from __future__ import annotations

import json
import logging
from typing import Callable, Optional

from sqlalchemy.orm import Session as DbSession

from platform_core.agent.normalizer import normalize_plan
from platform_core.agent.tools import discover_tools, resolve_params_schema
from platform_core.models import APIKEY_CAT_CHAT

log = logging.getLogger(__name__)

#: Thu tu thu provider cho viec lap ke hoach. MOT phan tu, khong duong lui.
#:
#: 🔴 GO `"gemini"` NGAY 08/09/2026 — AI CLEAN REBUILD V2 pha 05.3.
#:
#:    Ban cu la `("ltt_llm", "gemini")` kem `PLANNER_MODEL = "gemini-2.5-flash"`
#:    va chu thich *"May B ban thi `dieu_phoi` tu di tiep sang Gemini"*. Do la
#:    mot **duong lui duoc thiet ke**, va no kich hoat dung luc khong ai nhin:
#:    chi khi may B ban. Hoa don xuat hien sau, khong gan voi luot nao.
#:
#: ⭐ DO TRUOC KHI GO, chu khong go roi hy vong. Log worker production, cua so
#:    28 ngay (11/08 -> 08/09), 41.622 dong:
#:
#:        ltt_llm.chat                      3.435 job
#:        hong vi "may B ban"                  38 job   (~1,1%)
#:        thong diep loi nguyen van:
#:            "khong provider nao phuc vu duoc: ltt_llm: ban"
#:                                              ^^^ danh sach CHI co ltt_llm
#:
#:    Gemini **khong he nam trong cascade** cua nhung luot hong ay ⇒ no khong
#:    dang do 1,1% kia ⇒ go no **khong tao ra mot che do hong moi**. No chi xoa
#:    mot duong lui dang khong duoc dung.
#:
#: ⛔ Dung them provider ngoai vao day. May B khong du nang luc thi cau tra loi
#:    la **nang nang luc may B**, khong phai lang le tra tien cho ben khac.
from platform_core.llm.canonical import THU_TU_PROVIDER as PLANNER_PROVIDERS

MAX_GOAL_CHARS = 8000

#: Tai nguyen admission cua model nha. Doc tu ban khai cua app chu KHONG go tay,
#: vi go tay o day la ban sao thu hai cua `admission_resource` trong manifest.
_TAI_NGUYEN_MAC_DINH = ("llm_remote", 1)


def _model_nha() -> str:
    """Id **noi bo** cua model text nha, hoi thang REGISTRY.

    🔴 DONG NAY TUNG LA `{"ltt_llm": "ltt_llm"}`, VA DO LA MOT LOI IM LANG.

       `ltt_llm` la **bi danh cong khai**, khong phai id model. Duong khach that
       (`apps/ltt_llm/features.py`) gui `ALIAS_SANG_ID[...]` = `qwen38-api`, con
       registry chi khai `qwen38-api` / `qwen38-vision`. Nen
       `api_pool.chon_key(model="ltt_llm")` **luon** nem `ThieuKeyError`,
       `dieu_phoi` doc do la "provider nay khong phuc vu duoc, di tiep", va
       **moi** luot lap ke hoach roi xuong Gemini — mot provider ngoai, tra tien.

       Do duoc bang `tools/kiem_ltt_llm.py`, trong MOT tien trinh, MOT phien DB:
           hoi KHONG kem model  -> cap duoc khoa
           hoi KEM model="ltt_llm" -> ThieuKeyError

    ⭐ Goc re la mot **chu thich**: docstring cua `dieu_phoi.goi` day sai quy uoc
       (`model_theo_provider={"ltt_llm": "ltt_llm", ...}`), va hai noi chep theo
       no — tep nay va `tools/kiem_ltt_llm.py`. Ca hai deu hong.

    ⛔ Dung go lai id o day. Doi GGUF ben duoi thi registry doi, va cho nay
       phai di theo -- do chinh la viec cua registry.
    """
    from platform_core import providers
    for m in providers.models_for("ltt_llm", APIKEY_CAT_CHAT):
        if not (getattr(m, "capabilities", None) or {}).get("vision"):
            return m.id
    return ""


def _tai_nguyen_nha() -> tuple:
    """`(resource, slots)` cua model nha, lay tu ban khai cua app."""
    try:
        from platform_core.registry import discover
        for it in discover():
            if it.manifest.slug != "ltt_llm":
                continue
            for t in it.manifest.tools:
                r = getattr(t, "admission_resource", "")
                if r:
                    return r, int(getattr(t, "admission_slots", 1) or 1)
    except Exception:                                          # noqa: BLE001
        # ⛔ NOI RA. Roi ve mac dinh thi van chay duoc, nhung neu ban khai da doi
        #    ma cho nay khong doc duoc thi planner se gianh SAI tai nguyen — va
        #    mot suat gianh sai khong bao ve gi ca. Nuot im lang o day nghia la
        #    lop bao ve bien mat ma khong ai biet.
        log.warning("khong doc duoc ban khai ltt_llm; dung mac dinh %s",
                    _TAI_NGUYEN_MAC_DINH, exc_info=True)
    return _TAI_NGUYEN_MAC_DINH


class PlannerError(RuntimeError):
    pass


def build_prompt(goal: str, *, budget_max_credit: int, input_types: dict | None = None) -> str:
    tools = discover_tools()
    lines = ["[AVAILABLE TOOLS]"]
    for name, spec in sorted(tools.items()):
        schema = resolve_params_schema(name)
        compact = json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
        returns = json.dumps(spec.returns, ensure_ascii=False, separators=(",", ":"))
        lines.append(f"- {name}: {spec.description}\n  params={compact}\n  returns={returns}")
    lines.extend([
        "[INPUT PORTS] " + json.dumps(input_types or {}, ensure_ascii=False),
        f"[BUDGET] maximum {max(0, int(budget_max_credit))} credits",
        "[USER GOAL] " + (goal or "").strip()[:MAX_GOAL_CHARS],
        "[OUTPUT] Return one Plan JSON object, version=1. No markdown or commentary.",
    ])
    return "\n".join(lines)


def _goi_model(db: DbSession, prompt: str) -> str:
    """Gọi model lập kế hoạch qua `platform_core.llm.dieu_phoi`. (H38)

    ⭐ TRƯỚC ĐÂY hàm này tự dựng HTTP tới `generativelanguage.googleapis.com` và
       ghi cứng `thu_tu_provider=["gemini"]`. Hai hệ quả:

         1. Thêm một provider vào `REGISTRY` **không làm chỗ này dùng nó**;
         2. Cùng đoạn mã đó từng bị chép ở hai app khác nhau.

       `dieu_phoi` gom việc dịch giao thức về một chỗ, nên nay đổi nhà cung cấp là
       đổi **một danh sách**, không phải sửa ba tệp.

    ⭐ CHỈ MODEL NHÀ. Nó rẻ hơn nhiều, và prompt lập kế hoạch **không rời máy**.

    🔴 CẬP NHẬT 08/09/2026 — pha 05.3 GỠ đường lui sang Gemini.

       Đoạn này trước đây viết: *"Máy B bận thì `dieu_phoi` tự đi tiếp sang
       Gemini — và đó không phải 'đổi model sau lưng khách' (D-010)."* Lập luận
       D-010 ấy **vẫn đúng** (lập kế hoạch là việc nội bộ, khách không mua "một
       kế hoạch do model X sinh ra"), nhưng nó chỉ trả lời câu *"có được phép
       không"*, không trả lời câu *"có nên không"*.

       Câu thứ hai được trả lời bằng **phép đo**: trong 28 ngày, thông điệp lỗi
       thật ghi `khong provider nao phuc vu duoc: ltt_llm: ban` — danh sách
       **chỉ có `ltt_llm`**, tức đường lui ấy **không hề được dùng**. Nó là một
       nhánh mã chỉ chạy khi không ai nhìn, và hoá đơn xuất hiện sau.

    ⛔ Máy B bận thì **hỏng có tên** (xem đường suy biến ở thân hàm), không có
       provider ngoài nào phục vụ thay.

    🔴 VÀ PHẢI GIÀNH SUẤT ADMISSION TRƯỚC KHI CHẠM MÁY B (P08 F-06).

       Trước 01/09 hàm này gọi thẳng `dieu_phoi` — **đường duy nhất** tới máy B
       không đi qua `admission`. Ba đường còn lại (`streaming`, `chat`,
       `job_runner`) đều giành suất.

       Nó **vô hại cho tới hôm nay** chỉ vì một lỗi thứ hai che nó: nhánh
       `ltt_llm` không bao giờ cấp được khoá (xem `_model_nha`). Sửa lỗi kia mà
       không sửa lỗi này là **kích hoạt** một đường lách — nên hai bản vá đi
       cùng một lượt, không tách.

    ⭐ Không giành được suất thì **bỏ nhánh model nhà**, không xếp hàng chờ.
       Việc lập kế hoạch là việc nội bộ; để nó chen chỗ một request khách đang
       trả tiền là đổi thứ tự ưu tiên sai hướng.
    """
    import uuid as _uuid

    from platform_core.llm import admission, dieu_phoi

    thu_tu = list(PLANNER_PROVIDERS)
    ban_do: dict[str, str] = {}
    id_nha = _model_nha()
    ve = None
    tai_nguyen, suat = _tai_nguyen_nha()

    if id_nha:
        ve = admission.acquire(
            db, resource=tai_nguyen, slots=suat, user_id="he-thong:planner",
            mode="job", holder_id="planner:" + _uuid.uuid4().hex[:12])
        if ve is not None:
            ban_do["ltt_llm"] = id_nha

    # 🔴 DUONG SUY BIEN — PHAI NOI RA, KHONG DUOC TRONG NHU MOT LOI NGAU NHIEN.
    #
    #    Truoc pha 05.3, khong giành duoc suat thi `ltt_llm` bi loai khoi thu tu
    #    va Gemini phuc vu thay — **im lang**. Nay khong con provider sau, nen
    #    tinh huong ay la mot **that bai co ten**, khong phai mot danh sach rong
    #    truyen xuong `dieu_phoi` roi ne ra `KhongCoProviderNao` mo ho.
    #
    # ⭐ `AGENTS.md` §4c cau 2: *co y* phai phan biet duoc voi *tai nan*. Hai
    #    trang thai ay nhin tu ngoai giong het nhau neu ta khong viet ra.
    if "ltt_llm" not in ban_do:
        raise PlannerError(
            "Planner: model nha khong san sang "
            + ("(khong gianh duoc suat admission)" if id_nha else
               "(registry khong khai model text nao cho `ltt_llm`)")
            + ". Viec lap ke hoach KHONG co duong lui sang provider ngoai.")

    try:
        kq = dieu_phoi.goi(
            db,
            messages=[{"role": "user", "content": prompt}],
            category=APIKEY_CAT_CHAT,
            thu_tu_provider=tuple(thu_tu),
            model_theo_provider=ban_do,
            timeout_s=120.0,
        )
    except dieu_phoi.KhongCoProviderNao as exc:
        # ⛔ Mọi provider đều bận/không cấp được key. KHÔNG phải lỗi provider —
        #    `dieu_phoi` đã lo việc đánh dấu lỗi cho đúng trường hợp rồi.
        raise PlannerError(f"Planner: {exc}") from None
    finally:
        # Nhả suất dù đi đường nào — kể cả khi `dieu_phoi` ném trước lúc chạm
        # máy B (hết khoá, vượt ngân sách, provider báo bận). Giữ một suất không
        # dùng đúng bằng chiếm nó.
        #
        # ⚠️ Câu này trước 08/09 viết "kể cả khi `dieu_phoi` đã rơi sang Gemini".
        #    Đường đó đã bị gỡ ở pha 05.3; nhánh `finally` thì **không đổi** vì
        #    lý do thật của nó chưa bao giờ là Gemini — nó là *"có thể nhả một
        #    suất chưa từng được dùng"*, và điều đó vẫn đúng.
        if ve is not None:
            admission.release_by_id(ve.id)

    van = (kq.noi_dung or "").strip()
    if not van:
        raise PlannerError("Planner provider không trả text.")
    return van


def plan_once(db: DbSession, *, goal: str, budget_max_credit: int,
              input_types: Optional[dict] = None,
              llm_call: Optional[Callable[[str], object]] = None) -> dict:
    prompt = build_prompt(goal, budget_max_credit=budget_max_credit,
                          input_types=input_types)
    raw = llm_call(prompt) if llm_call is not None else _goi_model(db, prompt)
    return normalize_plan(raw, fallback_goal=goal, fallback_budget=budget_max_credit)
