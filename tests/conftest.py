"""
Fixture dùng chung cho toàn bộ bộ test.

## Vì sao tệp này gần như trống, và đó là chủ ý

Trước 2026-08-25 ở đây có **ba fixture `autouse`**, tức chúng chạy trước và sau
**mọi** test trong kho — kể cả test của Public API, VPS, Nexus và các app GPU:

  1. trỏ singleton `core.content_history` sang một CSDL SQLite tạm,
  2. xoá sạch bảng đó sau mỗi test,
  3. reset `core.circuit_breaker` dùng chung.

Cả ba đều tồn tại vì **một** lý do: engine đăng bài của socialbot giữ trạng thái
toàn cục (lịch sử chống trùng bài, cầu dao ngắt mạch), nên test này rò sang test
kia. Ba fixture đó là phần vá cho một thiết kế đã bị gỡ.

⭐ Điều đáng ghi lại: chi phí của chúng **không nằm ở socialbot**. Mỗi test trong
   kho — hơn 3.700 test không liên quan gì tới Facebook — đều phải mở một kết
   nối SQLite và chạy một lệnh `DELETE` chỉ để dọn hộ một engine mà nó không
   dùng. Một fixture `autouse` là một khoản thuế thu trên toàn bộ, và nó không
   hiện ra ở đâu cả.

⛔ Nên đừng thêm `autouse` mới vào đây trừ khi nó thật sự đúng cho **mọi** test.
   Trạng thái dùng chung của một miền thì đặt fixture ở chính tệp test của miền
   đó.
"""
from __future__ import annotations

import pytest
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

# ⛔ BON TEN TREN PHAI o CAP MODULE, khong duoc import ben trong `_router_thu()`.
#
#    Tep nay co `from __future__ import annotations`, nen moi chu thich kieu
#    thanh CHUOI. FastAPI phai giai chuoi do bang `get_type_hints`, va no chi
#    nhin thay **globals cua module**. Import ben trong ham thi `Request` la mot
#    ten CUC BO — FastAPI khong giai duoc, va no doan `request` la mot tham so
#    QUERY:
#
#        GET /appthu -> 422
#        {"detail":[{"type":"missing","loc":["query","request"], ...}]}
#
#    Da dinh that 26/08, va trieu chung khong he chi vao nguyen nhan.


# ── App THỬ tổng hợp, thay cho `apps/demo` đã gỡ ─────────────────────────────
#
# ## Vì sao có thứ này, và vì sao nó KHÔNG nằm trong `apps/`
#
# Bốn bộ test hạ tầng — hàng đợi (`test_67`), sổ credit (`test_68`), giữ chỗ GPU
# (`test_151`), vòng đời upload (`test_173`) — cần **một app bất kỳ** để nộp job
# vào. Trước 2026-08-25 chúng dùng `apps/demo`, một app CÓ THẬT trong danh mục
# sản phẩm.
#
# ⛔ Đó là một sự phụ thuộc ngược: **hợp đồng của nền tảng không được dựa vào
#    một mặt hàng.** Nó biến `demo` thành thứ không xoá được — muốn dẹp một app
#    60 dòng thì phải viết lại phần nền của bốn bộ test. Đúng cái bẫy đã giữ
#    `core/` sống thêm ba tuần (Q10).
#
# ⭐ App thử ở đây **chỉ tồn tại trong bộ nhớ của một test**. Nó không có thư
#    mục, không có route, không lên catalog, không đi vào bản phát hành, và
#    không ai phải nhớ tắt nó ở production.
#
# Cách hoạt động: `registry.discover()` và `jobs.resolve_handler()` đều được tra
# **tại thời điểm gọi** từ globals của module chúng, nên `monkeypatch` là đủ —
# không phải sửa một dòng nào trong `platform_core/` cho việc test.

#: `job_type` của app thử. Đặt tên khác hẳn mọi app thật để một lượt grep nhầm
#: không bao giờ dẫn về đây.
APP_THU_SLUG = "appthu"
APP_THU_JOB = "appthu.dao_nguoc"


def _gia_thu(params: dict) -> int:
    """Giá của app thử: 1 credit cho mỗi 100 ký tự, tối thiểu 1.

    Giữ nguyên công thức của `apps/demo` cũ để các phép khẳng định về số tiền
    trong `test_68` vẫn nói về cùng một thứ (250 ký tự → 2 credit).
    """
    return max(1, len(str(params.get("text", ""))) // 100)


def _handler_thu(params: dict, ctx=None) -> dict:
    """Đảo ngược chuỗi. Ném khi rỗng — bộ test cần một đường THẤT BẠI có thật."""
    text = str(params.get("text", ""))
    if not text.strip():
        raise ValueError("text rong")
    return {"output": text[::-1]}


def _router_thu():
    """Be mat web toi thieu cua app THU: mot trang co CSRF + mot duong nop job.

    Du de kiem duong web that (CSRF, giu cho credit, chuyen trang sang `/jobs/`),
    khong hon. Moi thu khac deu la be mat that cua nen tang.
    """
    from server.auth.csrf import issue_csrf_token, verify_csrf_token
    from server.auth.session import require_login
    from server.deps import get_db, user_hien_tai

    router = APIRouter()

    @router.get("", response_class=HTMLResponse)
    def trang(request: Request, user: str = Depends(require_login)):
        return HTMLResponse(
            '<form method="post" action="/appthu/queue">'
            f'<input type="hidden" name="csrf_token" value="{issue_csrf_token(request)}">'
            '<input name="text"></form>')

    @router.post("/queue")
    def queue(request: Request, text: str = Form(""),
              csrf_token: str = Form(""), user: str = Depends(require_login),
              db=Depends(get_db)):
        from platform_core import credit
        from platform_core.job_submit import submit_with_credit

        if not verify_csrf_token(request, csrf_token):
            return RedirectResponse("/appthu", status_code=303)
        u = user_hien_tai(request)
        try:
            job = submit_with_credit(db, user_id=u.id, app_slug=APP_THU_SLUG,
                                     job_type=APP_THU_JOB, params={"text": text})
            db.commit()
        except credit.ThieuCreditError:
            db.rollback()
            return HTMLResponse("Khong du credit", status_code=402)
        return RedirectResponse(f"/jobs/{job.id}", status_code=303)

    return router


@pytest.fixture()
def app_thu(monkeypatch):
    """Đăng ký một app tổng hợp cho đúng một test. Trả về module-namespace nhỏ.

    Dùng:

        def test_gi_do(db, app_thu):
            job = submit_with_credit(db, user_id="u1", app_slug=app_thu.slug,
                                     job_type=app_thu.job_type,
                                     params={"text": "abc"})
    """
    from types import SimpleNamespace

    from platform_core import jobs as jobs_mod
    from platform_core import registry as reg

    manifest = reg.AppManifest(
        slug=APP_THU_SLUG,
        display_name="App thu (chi co trong test)",
        route_prefix=f"/{APP_THU_SLUG}",
        job_types=(APP_THU_JOB,),
        requires=("api",),
        credit_cost=_gia_thu,
        # Không bao giờ hiện ở đâu: đây là đồ dùng của test, không phải mặt hàng.
        enabled=False, public=False, surface="runtime", lifecycle="internal",
    )
    # ⭐ App THU co ROUTE, va day khong phai chi tiet thua.
    #
    #    Q109 go `apps/demo` va di tru bon bo test ha tang sang app THU nay.
    #    Nhung `test_69_web_jobs.py` kiem duong WEB — form -> job -> huy -> co
    #    lap chu so huu — va app THU luc do khong co route nao, nen 9 phep kiem
    #    do chet lang le. Chung van tro vao `/demo/queue`, mot duong 404.
    #
    # ⛔ Do la 9 phep kiem phu mot Golden Journey (nop job qua web + A khong doc
    #    duoc job cua B) NGUNG CHAY ma khong ai biet, cho toi luot `pytest` day
    #    du dau tien chay sau do (26/08).
    #
    # ⭐ KHONG tro chung sang mot app that: `CLAUDE.md` canh dung cai bay do
    #    ("chi doi chu no"), vi khi ay bo test lai phu thuoc vao mot mat hang.
    #    Dung cach la app THU co du be mat ma hop dong app co — ke ca route.
    #
    #    `mount_all` gan router BAT KE `enabled`, nen app nay van vo hinh trong
    #    catalog (`enabled=False`, `surface="runtime"`) ma route van chay.
    loaded = reg.LoadedApp(manifest=manifest, router=_router_thu())

    discover_that = reg.discover

    def discover_kem_app_thu(apps_dir=None):
        goc = discover_that() if apps_dir is None else discover_that(apps_dir)
        return list(goc) + [loaded]

    monkeypatch.setattr(reg, "discover", discover_kem_app_thu)

    resolve_that = jobs_mod.resolve_handler

    def resolve_kem_app_thu(job_type: str):
        if job_type == APP_THU_JOB:
            return _handler_thu
        return resolve_that(job_type)

    monkeypatch.setattr(jobs_mod, "resolve_handler", resolve_kem_app_thu)

    return SimpleNamespace(slug=APP_THU_SLUG, job_type=APP_THU_JOB,
                           manifest=manifest, handle=_handler_thu,
                           credit_cost=_gia_thu)


# ── Người dùng giả cho test (F-01, audit 2026-08-07) ─────────────────────────
def bao_dam_user(db, user_id: str):
    """Tạo người dùng thật mang đúng `user_id` nếu chưa có. Trả về id.

    Từ khi `credit.cap_tay()` kiểm người dùng tồn tại (F-01), test nạp credit cho
    một id bịa như `"u1"` sẽ bị từ chối — **đúng như thiết kế**. Trước đó chúng
    chạy được chỉ vì đang dựa vào chính lỗ P0 mà finding này bịt.

    Dùng hàm này thay vì nới lỏng `cap_tay`: nới lỏng là mở lại lỗ tiền chỉ để
    test xanh.
    """
    from platform_core.models import User
    if db.get(User, user_id) is None:
        db.add(User(id=user_id, email=f"{user_id}@test.local",
                    password_hash="x", is_verified=True))
        db.flush()
    return user_id


# ── Cắt test khỏi mặt phẳng claim GPU TOÀN MÁY ───────────────────────────────
#
# `platform_core/gpu_claims.py` đọc/ghi `C:\ProgramData\gpu_claims\claims\` —
# một thư mục dùng chung cho **mọi hộ trên máy**, không chỉ nền tảng này. Máy B
# có ba hộ dùng chung GPU (dự án video ở `E:\LTT AI`, LLM ở `H:\LTT_LLM`, và ta),
# nên thư mục đó gần như luôn có thứ gì đó trong nó.
#
# 🔴 VÌ SAO NÓ CHẢY VÀO TEST, đo được 2026-08-29. `gpu_lease.acquire()` trừ
#    `reserved_mb_by_gpu()` theo **chỉ số card**. Test dựng card GIẢ cũng mang
#    index 0, nên một claim THẬT trên GPU 0 bị trừ vào card giả:
#
#      test_chua_lai_headroom: card giả free_mb=6000, đòi acquire(4976)
#        bình thường : 6000        >= 4976 + 1024  ->  vừa đủ, XANH
#        khi có claim: 6000 - 7168 = -1168         ->  từ chối,  ĐỎ
#
# ⚠️ Và nó chỉ chảy khi claim còn MỚI (trong `_CUA_SO_NAP_MODEL_S` = 90 giây),
#    nên nó **không đỏ đều — nó đỏ tuỳ lúc**. Hai phiên chạy cách nhau vài phút
#    ra hai kết quả khác nhau, và cả hai đều đi tìm nguyên nhân ở chỗ khác
#    (`__pycache__`, "test tự chập chờn"). Một phép kiểm phụ thuộc việc ai đang
#    dựng video là một phép kiểm phụ thuộc môi trường đội lốt phép kiểm chức năng.
#
# ⭐ `_claims()` tự khai rằng trả `None` nghĩa là "chạy đúng như cũ", nên đây là
#    chốt cô lập có sẵn trong thiết kế, không phải một lỗ khoét thêm cho test.
#    Nó cũng chặn luôn chiều NGƯỢC LẠI: bộ test từng ghi claim thật vào
#    `C:\ProgramData` và để lại rác (đã thấy một tệp `job:"jx"` mồ côi).
#
# ⛔ KHÔNG đặt `autouse` ở đây — xem đầu tệp. Tệp test của miền GPU tự bọc nó
#    bằng một fixture `autouse` trong PHẠM VI TỆP, đúng như hướng dẫn đó nói.
@pytest.fixture()
def gpu_khong_claim_toan_may(monkeypatch):
    """Cho `gpu_lease` chạy như thể máy không có mặt phẳng claim dùng chung."""
    from platform_core import gpu_lease

    monkeypatch.setattr(gpu_lease, "_claims", lambda: None)
