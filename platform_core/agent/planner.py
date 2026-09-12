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

#: ⛔ `_TAI_NGUYEN_MAC_DINH` ĐÃ GỠ (multijob 2.2). Nó là một hằng số chết —
#:    không dòng nào đọc — và là đúng "bản sao thứ hai của bản khai" mà chú
#:    thích của chính nó cảnh báo. Mặc định thật sống MỘT bản ở
#:    `platform_core/llm/canonical.py::_TAI_NGUYEN_MAC_DINH`, và từ 2.2 nó là
#:    `AdmissionModel`, không còn là bộ đôi `(resource, slots)`.


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

    🔴 D09 (dual-model 2.4) DOI CACH CHON, KHONG DOI BAT BIEN.

       Ban truoc chon "model text dau tien KHONG co co `vision`". Phep chon ay
       hong o hai chieu, va ca hai deu that:

       (a) **No khong tra loi dung cau hoi.** Tu 11/09 may B chay HAI model tren
           HAI card. Lap ke hoach la viec **noi bo**, nen model cua no la thu
           `MODEL_NOI_BO_MAC_DINH` khai (`ltt-3.5`, 5060 Ti) — khong phai "cai
           dau tien khong doc anh". Truoc 2.4 phep chon ay tra ve `qwen38-api`
           trong khi `_goi_model` giu suat cua... cung `MODEL_MAC_DINH`, nen hai
           ve trung nhau **do trung hop**, khong do thiet ke.

       (b) **No tu vo o Task 3.3.** Khi `qwen38-api` nap mmproj va khai
           `vision: True`, ca hai model deu co co ⇒ vong lap khong tra ve gi ⇒
           `PlannerError("registry khong khai model text nao")`, va planner
           chet han. Cung lop loi ma `apps/auto_scan_video/ai.py::model_cho`
           dang mang (bao cao 2.3 §1.2), o mot tep khac.

    ⇒ Nay: hoi **ban khai** lay bi danh, doi bi danh sang id noi bo, roi **van
      doi chieu voi registry** — id khong co trong registry thi tra `""`, giu
      nguyen thong diep loi cu. Phan "hoi registry" khong mat; phan "doan bang
      mot co" thi mat.
    """
    from platform_core import providers
    from platform_core.llm import canonical

    id_nha = canonical.ALIAS_SANG_ID.get(canonical.MODEL_NOI_BO_MAC_DINH, "")
    if not id_nha:
        return ""
    co_that = {m.id for m in providers.models_for("ltt_llm", APIKEY_CAT_CHAT)}
    return id_nha if id_nha in co_that else ""


#: ⛔ BÍ DANH, không phải định nghĩa. Chuyển lên `platform_core/llm/canonical.py`
#:    ở pha 05.4 vì **bốn app** sắp di trú sang máy B cũng cần đúng hàm này —
#:    mỗi nơi tự chép sẽ thành bốn bản sao của cùng một quyết định.
from platform_core.llm.canonical import tai_nguyen_nha as _tai_nguyen_nha


class PlannerError(RuntimeError):
    pass


def _luat_cho_planner(prompt: str) -> dict:
    """Tham số đa lượt của một lượt LẬP KẾ HOẠCH: lớp `noi_bo` + đặt chỗ KV. (spec §6)

    ⭐ Lớp `noi_bo` là nửa quan trọng hơn. Không khai lớp thì lease đi đường
       `tuong_tac` — tức việc nội bộ của nền tảng tranh chỗ **ngang hàng** với
       một khách đang trả tiền và đang nhìn màn hình. Luật 3 của `luat_nhan`
       tồn tại để chặn đúng chuyện đó, và nó chỉ chặn được thứ nó **nhìn thấy**.

    ⛔ Ước hỏng ⇒ đặt chỗ CẢ POOL — cùng hướng an toàn với job nền: một lease
       không mang số token là một lease **vô hình** với sổ ngân sách KV, và hai
       đường cộng lại vượt pool thì llama.cpp giết mọi slot.
    """
    import logging

    from platform_core.llm import canonical, luat_nhan, tham_so_da_luot

    try:
        tool = canonical.tool_nha()
    except Exception:                                          # noqa: BLE001
        logging.getLogger(__name__).exception(
            "khong doc duoc ban khai model nha de dat cho KV")
        return {}
    # ⛔ Ngân sách KV lấy từ `admission_cho(model)`, KHÔNG từ `admission_token_pool`
    #    (multijob 2.2): một tool khai `admission_theo_model` có trường tĩnh ấy
    #    RỖNG, nên đọc thẳng nó sẽ ra 0 ⇒ `{}` ⇒ lease **vô hình** với sổ ngân
    #    sách KV, đúng cái hướng an toàn ở dưới sinh ra để tránh.
    try:
        # D09: việc lập kế hoạch là việc NỘI BỘ ⇒ ngân sách KV của model nội bộ
        # (`ltt-3.5`), không phải của model mặc định bán cho khách (`ltt-3.8`).
        suc = tool.admission_cho(canonical.MODEL_NOI_BO_MAC_DINH) if tool else None
    except KeyError:
        logging.getLogger(__name__).exception(
            "model nha %r khong co trong ban khai admission cua tool",
            canonical.MODEL_NOI_BO_MAC_DINH)
        return {}
    pool = int(suc.token_pool) if suc else 0
    if pool <= 0:
        return {}
    try:
        from platform_core.public_api.executor import for_tool

        ex = for_tool(tool)
        tin = [{"role": "user", "content": prompt}]
        vao = int(ex.estimate_input(tin))
        ra = int(ex.mac_dinh_cho("job"))
        ra = min(ra, int(ex.context_output_cap(vao)))
        return tham_so_da_luot.luat_cho(pool, lop=luat_nhan.NOI_BO,
                                        token_vao_uoc=vao, xin_ra=ra)
    except Exception:                                          # noqa: BLE001
        logging.getLogger(__name__).exception(
            "khong uoc duoc token cua luot lap ke hoach - dat cho CA POOL")
        return dict(lop=luat_nhan.NOI_BO, token_pool=pool, token_dat_truoc=pool)


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

    from platform_core.llm import admission, canonical, dieu_phoi

    thu_tu = list(PLANNER_PROVIDERS)
    ban_do: dict[str, str] = {}
    id_nha = _model_nha()
    ve = None
    # D09: suất giành phải là suất của model SẮP GỌI (`_model_nha()` đọc cùng
    # một hằng), nếu không thì lease nằm ở pool KV của card kia — và một suất
    # giành sai pool không bảo vệ gì.
    suc = _tai_nguyen_nha(canonical.MODEL_NOI_BO_MAC_DINH)

    if id_nha:
        ve = admission.acquire(
            db, resource=suc.resource, slots=suc.slots, user_id="he-thong:planner",
            mode="job", holder_id="planner:" + _uuid.uuid4().hex[:12],
            **_luat_cho_planner(prompt))
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
