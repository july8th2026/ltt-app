"""Cụm v2 **không được quay lại qua đường frontend** — kể cả trong hàm chết.

No §5 cua `docs/superpowers/plans/2026-09-24-wf-v2-MASTER.md`, lan `p10-don`.
Doi ve may chu: `tests/test_2934_dong_cua_cum_v2.py` (P8 Task 5 da dong 15
route). Tep nay la ve **giao dien** cua cung mot phan quyet.

## ⭐ VI SAO CAN THEM MOT BAI, KHI DA CO `test_1728`

`test_1728` do theo **kha nang voi toi**: chi nhung ham ma giao dien that su
goi moi bi tinh. Do la mot lua chon co chu dich va no dung cho cau hoi *"giao
dien co dang moi nguoi dung lam mot viec se 404 khong"*.

Nhung no **khong tra loi** cau hoi thu hai: mot ham chet van nam trong
`workflowApi.ts`, tro vao mot cua **da bi go khoi may chu**, va chi cach song
lai dung MOT dong `import`. Do chinh la ly do `test_2934` doi xoa han
`assistant.py`/`sharing.py`/`library.py` chu khong chi go khoi `__init__`:

    "Go khoi `__init__` ma de lai tep la de mot khau sung da nap dan trong
     kho: mot `import` vo tinh du mo lai ca cum."

⇒ Hai bai o day do **moi duong `/agent/...` viet trong `src/**`**, khong loc
  theo kha nang voi toi.

## 🔑 NGUON, KHONG PHAI BAN CHEP

- Bang dinh tuyen: `apps.agent.routes.router` **that**.
- Danh sach cua da dong: `test_2934.DA_DONG` — import thang, khong chep lai.
- Bo doc duong / cat chu thich / chuan hoa: dung lai cua `test_1728`.

Ba nguon ay deu la thu nguoi khac phai sua khi ho doi y; khong co danh sach
ten ham nao go cung trong tep nay.

## ⚠️ Pham vi hep hon loi tuyen bo

So **duong dan**, khong so **phuong thuc** (y het `test_1728`). Va no doc
`src/**` — mot ban dung cu con trong `server/static/agent-canvas/assets/`
khong bi tinh; thu chan chuyen ay la buoc build lai o cuoi phien.
"""
from __future__ import annotations

import pathlib

import pytest

from tests.test_1728_canvas_khong_goi_duong_chet import (
    TIEN_TO, _DUONG, bo_chu_thich, chuan_hoa)
from tests.test_2934_dong_cua_cum_v2 import DA_DONG

GOC = pathlib.Path(__file__).resolve().parent.parent
SRC = GOC / "frontend" / "agent-canvas" / "src"


def _duong_trong(nguon: str) -> set[str]:
    return {chuan_hoa(d) for d in _DUONG.findall(bo_chu_thich(nguon))}


@pytest.fixture(scope="module")
def duong_viet_trong_src() -> dict[str, list[str]]:
    """{đường: [tệp:dòng]} cho MỌI đường `/agent/...` viết trong `src/**`."""
    ra: dict[str, list[str]] = {}
    for tep in sorted(SRC.rglob("*.ts*")):
        sach = bo_chu_thich(tep.read_text(encoding="utf-8"))
        for i, dong in enumerate(sach.splitlines(), 1):
            for d in _DUONG.findall(dong):
                ra.setdefault(chuan_hoa(d), []).append(
                    f"{tep.relative_to(SRC)}:{i}")
    return ra


@pytest.fixture(scope="module")
def bang_dinh_tuyen() -> set[str]:
    from apps.agent.routes import router
    return {chuan_hoa(TIEN_TO + getattr(r, "path", "")) for r in router.routes}


#: Cửa đã đóng, ở hình dạng đường dẫn mà frontend viết ra.
CUA_DA_DONG = {chuan_hoa(TIEN_TO + duong) for _pt, duong in DA_DONG}


def test_KHONG_ham_nao_trong_src_con_tro_vao_cum_v2_da_dong(
        duong_viet_trong_src):
    """⛔ Bài 1 — cụm v2 không được còn một đầu dây nào ở frontend.

    Kể cả trong một hàm không ai gọi: đó là khẩu súng đã nạp đạn.
    """
    gay = {d: noi for d, noi in sorted(duong_viet_trong_src.items())
           if d in CUA_DA_DONG}
    assert not gay, (
        "Frontend van giu loi goi vao cum v2 DA DONG (`test_2934`):\n"
        + "\n".join(f"  {d}   <- {', '.join(noi)}" for d, noi in gay.items())
        + "\nXOA han ham do khoi `src/`, dung sua header cho no.")


#: 🔴 MỐC — đường `/agent/...` viết trong `src/**` mà máy chủ **không còn có**.
#:
#: Đo ngày 24/09/2026, sau khi lằn `p10-don` gỡ cụm v2: chín đường thuộc
#: **cụm run v2** (`agent_runs`) còn nằm chết trong `workflowApi.ts` (không
#: ai gọi — `tests/test_1728` bỏ qua đúng vì thế).
#:
#: ⭐ HẠ MỐC 25/09 (lằn `wfa`, plan `2026-09-25-wf-v2-VAN-HANH.md` task A6):
#:    cả chín hàm (`createRun`/`approveRun`/`tickRun`/`cancelRun`/`runAgain`/
#:    `restoreRunAsWorkflow`/`loadRunHistory`/`loadRun`/`validateWorkflow`) đã
#:    bị XOÁ khỏi `workflowApi.ts` — không còn một dòng `/agent/api/runs...`
#:    hay `/agent/api/workflows/{}/validate` nào trong `src/**` để đo. Mốc vì
#:    vậy hạ xuống RỖNG; `tests/workflowApi.test.ts` đã viết lại theo (cụm v3
#:    `saveWorkflowV3`/`publishWorkflowV3`/`createRunV3` thay cho các bài kiểm
#:    CSRF/If-Match/409/422 từng đi qua cụm v2). Bánh cóc TẬP HỢP hàm còn sống
#:    trong `workflowApi.ts`: `tests/test_4105_wf_v2_pa_don_ma_chet.py`.
#:
#: ⛔ **Tập này chỉ được phép CO LẠI.** Cùng khuôn `tools/check_so_test.py`:
#:    không dọn quá khứ, chặn tương lai. Ai gỡ được một đường thì xoá nó khỏi
#:    đây, và lần xoá ấy hiện ra trong diff.
MOC_DUONG_CHET: set[str] = set()


def test_KHONG_them_duong_chet_nao_ngoai_MOC(duong_viet_trong_src,
                                             bang_dinh_tuyen):
    """⛔ Bài 2 — bánh cóc: tập đường chết chỉ được co lại.

    Rộng hơn bài 1 (bắt cả cửa bị gỡ vì lý do khác), nhưng không bắt lằn này
    dọn hết quá khứ trong một lượt.
    """
    chet = {d: noi for d, noi in sorted(duong_viet_trong_src.items())
            if d not in bang_dinh_tuyen}
    them = {d: noi for d, noi in chet.items() if d not in MOC_DUONG_CHET}
    assert not them, (
        "Duong `/agent/...` MOI viet trong src/ ma may chu KHONG co:\n"
        + "\n".join(f"  {d}   <- {', '.join(noi)}" for d, noi in them.items()))


def test_MOC_phai_duoc_HA_khi_don_duoc(duong_viet_trong_src, bang_dinh_tuyen):
    """🔑 Vế còn lại của một cái mốc.

    Một mốc không được nói dối theo chiều kia: gỡ xong một hàm mà quên xoá
    dòng tương ứng ở đây thì mốc thành một danh sách ma, và lần sau nó sẽ
    tha đúng đường ấy quay lại mà không ai đỏ.
    """
    chet = {d for d in duong_viet_trong_src if d not in bang_dinh_tuyen}
    thua = sorted(MOC_DUONG_CHET - chet)
    assert not thua, (
        f"MOC_DUONG_CHET con {thua} nhung `src/` khong con goi chung -- "
        "ha moc: xoa cac dong ay.")


# ── Đối chứng: một bộ dò hỏng làm CẢ HAI bài trên xanh ───────────────────

def test_bo_do_DOC_DUOC_du_nhieu_duong(duong_viet_trong_src):
    """🔑 Số 0 không đối chứng thì không phải phát hiện.

    Một `rglob` sai thư mục đọc ra 0 đường và cả hai bài trên xanh tuyệt đối.
    """
    assert len(duong_viet_trong_src) >= 12, (
        f"chi doc duoc {len(duong_viet_trong_src)} duong tu {SRC} - bo do hong?")


def test_danh_sach_CUA_DA_DONG_khong_rong_va_khop_may_chu(bang_dinh_tuyen):
    """🔑 Nếu `DA_DONG` rỗng (ai đó dọn nhầm), bài 1 xanh mà không đo gì.

    Vế thứ hai là đối chứng cho chính danh sách ấy: cửa đã đóng thì **không**
    được còn trong bảng định tuyến — nếu còn, `test_2934` mới là bài phải đỏ,
    và bài 1 ở đây đang đo một thứ đã sai từ gốc.
    """
    assert len(CUA_DA_DONG) >= 10
    assert not (CUA_DA_DONG & bang_dinh_tuyen)


def test_bo_do_BAT_DUOC_mot_ham_chet_duoc_tiem_vao():
    """🔑 TIÊM LỖI — vế quyết định.

    Dựng lại đúng thứ vừa gỡ: một hàm **không ai gọi** gọi vào
    `/assistant/preview`. Bộ dò phải thấy nó. `test_1728` thì không, và đó
    chính là khoảng trống tệp này lấp.
    """
    mau = ("export async function previewAssistant(w) {\n"
           "  return apiFetch(`/agent/api/workflows/${w.id}/assistant/preview`)\n"
           "}\n")
    thay = _duong_trong(mau)
    assert thay & CUA_DA_DONG, thay


def test_bo_do_KHONG_bao_mot_cua_con_song(bang_dinh_tuyen):
    """🔑 Vế ngược: một bộ dò báo *mọi thứ* cũng làm bài 1 'đúng' theo chiều
    sai, và người sau sẽ tắt nó đi."""
    mau = ("export const luu = (id, doc) =>\n"
           "  request(`/agent/api/v3/workflows/${id}`, { method: 'PUT' })\n")
    thay = _duong_trong(mau)
    assert thay and not (thay & CUA_DA_DONG)
    assert thay <= bang_dinh_tuyen


def test_bo_cat_chu_thich_KHONG_tinh_mot_duong_chi_duoc_NHAC_TEN():
    """`CanvasShell.tsx` cố ý **nhắc tên** cụm v2 trong chú thích ⛔ để người
    sau không import lại. Nhắc tên không phải gọi — tính nó vào là ép người ta
    xoá chính lời cảnh báo."""
    mau = ("// ⛔ KHONG import lai `/agent/api/workflows/${id}/assistant/preview`\n"
           "const x = request('/agent/api/v3/palette')\n")
    thay = _duong_trong(mau)
    assert thay == {"/agent/api/v3/palette"}
