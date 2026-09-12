"""test_980 — viện dẫn phép kiểm trong mã LLM phải trỏ tới ĐÚNG MỘT tệp.

Dải **980–989** cấp cho chương trình MASTER UPGRADE của LTT LLM (2026-09-09).
Xem `docs/LLM_UPGRADE_MASTER_PLAN.md`.

═══════════════════════════════════════════════════════════════════════════
 KHUYẾT TẬT ĐÃ SINH RA TỆP NÀY
═══════════════════════════════════════════════════════════════════════════

`llm_gateway/config.py` từng viết:

    "số ở đây là bản sao, và `tests/test_312` đỏ ngay khi hai bên lệch."

`tests/test_312_vps_khoa_dich_vu.py` là **khoá dịch vụ VPS**. Nó không biết gì
về trần token của máy B. Phép kiểm thật là `test_334_ngan_sach_ltt_llm.py` và
`test_250_llm_gateway.py` — cả hai đều có, nên hằng số **vẫn được bảo vệ**; thứ
hỏng là **lời hứa**, không phải hàng rào.

⛔ VÀ NÓ ĐÃ ĐƯỢC PHÁT HIỆN MỘT LẦN RỒI.
   `docs/VLM_NOI_BO/RA_SOAT_THAM_SO_LTT_LLM.md` §559 ghi *"③ Số test trùng.
   `test_312` bị hai phiên dùng cùng lúc"*. Bản vá lúc ấy sửa **tài liệu** và bỏ
   quên **chú thích trong mã**. Sửa một triệu chứng thì triệu chứng kia sống tiếp.

═══════════════════════════════════════════════════════════════════════════
 CƠ CHẾ GỐC: SỐ HIỆU TEST BỊ TRÙNG, VÀ TRÙNG NHIỀU
═══════════════════════════════════════════════════════════════════════════

Đếm ngày 09/09 trên `tests/`: **22** số hiệu bị hai tệp trở lên dùng chung.
Nặng nhất:

    test_250 -> cong_render · llm_gateway · nexus_sso          (BA tệp)
    test_251 -> ban_dich_sai_nghia · cong_vlm · dich_gemini · vps_ha_tang (BỐN)
    test_252 -> dieu_phoi · gia_token · vps_giao_dien          (BA tệp)

⇒ Viết `test_250` trong một chú thích là **không nói được điều gì cả**. Người
  đọc phải đoán một trong ba, và cả ba đều tồn tại nên không có gì báo họ sai.

═══════════════════════════════════════════════════════════════════════════
 MỘT PHÉP KIỂM MẠNH HƠN ĐÃ BỊ TỪ CHỐI — VÀ ĐÂY LÀ LÝ DO
═══════════════════════════════════════════════════════════════════════════

Bản thiết kế đầu của tôi là **đối chiếu ngược**: nếu `A.py` bảo `test_X` giữ nó
thì `test_X` phải nhắc lại `A.py`. Nó **bắt được** đúng lỗi gốc — đo thật:

    llm_gateway/config.py -> test_312_vps_khoa_dich_vu.py : KHONG nhac lai  (ĐỎ ✓)

Nhưng nó cũng **báo động nhầm**, và tôi đo được ca đó trước khi viết:

    apps/ltt_llm/features.py -> test_212_coverage_certification.py : KHONG nhac lai

`test_212` là viện dẫn **đúng**. Nó chứng nhận mọi tool/alias bằng cách **duyệt
registry**, nên nó không bao giờ gõ chữ `ltt_llm` — chính vì nó tổng quát mà nó
có giá trị. Một phép kiểm tổng quát không nêu tên thứ nó bảo vệ, và đó là tính
chất chứ không phải khuyết tật.

⛔ Nên bản đối chiếu ngược sẽ phạt đúng những phép kiểm viết tốt nhất, rồi người
   ta thêm miễn trừ cho tới khi danh sách miễn trừ **chính là** danh sách cần
   kiểm. Một hàng rào báo động nhầm tệ hơn không có hàng rào: nó dạy người ta
   bấm bỏ qua.

⭐ Nên tệp này chốt thứ **hẹp hơn mà đúng tuyệt đối**: một viện dẫn phải **xác
   định được**. Nó không hứa bắt được mọi viện dẫn sai — nó bắt được lớp viện
   dẫn mà người đọc **không thể tự kiểm chứng**, và đó chính là lớp đã làm
   `test_312` sống sót.

⚠️ NÓI ĐÚNG PHẠM VI: chốt này **không** bắt được ca `test_312` gốc (số ấy chỉ
   trỏ tới một tệp — xác định, nhưng sai). Thứ bắt ca ấy là con người đọc lại,
   và nó đã xảy ra. Cái tệp này ngăn là ca **kế tiếp**, vốn nguy hiểm hơn vì
   không ai kiểm chứng được nó bằng mắt.
"""
from __future__ import annotations

import pathlib
import re

GOC = pathlib.Path(__file__).resolve().parents[1]
THU_MUC_TEST = GOC / "tests"

#: Mã do chương trình MASTER UPGRADE sở hữu. Cố ý **không** quét cả kho:
#: đo ngày 09/09 có **307** viện dẫn `test_NNN` trong mã nguồn, phần lớn ở dạng
#: số trần. Quét cả kho là mở một đợt sửa hàng trăm chú thích thuộc phiên khác —
#: ngoài phạm vi, và trái luật 12/13 của `CLAUDE.md`.
#:
#: ⭐ Mở rộng phạm vi là một QUYẾT ĐỊNH RIÊNG, không phải một bước dọn dẹp. Ai
#:    mở thì phải đếm lại trước (`docs/LLM_UPGRADE_BASELINE.md` §G-05).
PHAM_VI = (
    "llm_gateway/config.py",
    "llm_gateway/api.py",
    "llm_gateway/catalog.py",
    "llm_gateway/main.py",
    "llm_gateway/ngan_sach.py",
    "apps/ltt_llm/ngan_sach.py",
    "apps/ltt_llm/manifest.py",
    "apps/ltt_llm/features.py",
    "platform_core/llm/thanh_toan.py",
    "platform_core/llm/cong_vlm.py",
    "platform_core/llm/dieu_phoi.py",
    "platform_core/public_api/config.py",
)

#: `test_312` (số trần) hoặc `test_312_vps_khoa_dich_vu` (có tên).
MAU = re.compile(r"test_(\d{3})(_[a-z0-9_]+)?")


def _ung_vien(so: str) -> list[str]:
    """Mọi tệp test mang số hiệu `so`. Nhiều hơn một ⇒ số ấy không xác định."""
    return sorted(p.name for p in THU_MUC_TEST.glob("test_" + so + "_*.py"))


def _vien_dan(duong_dan: str) -> list[tuple[str, str]]:
    """`(so, duoi)` của mọi viện dẫn trong một tệp. `duoi` rỗng = số trần."""
    van = (GOC / duong_dan).read_text(encoding="utf-8")
    return [(m.group(1), m.group(2) or "") for m in MAU.finditer(van)]


def test_moi_vien_dan_co_ten_thi_tep_do_phai_ton_tai():
    """Viện dẫn có tên là một lời hứa cụ thể. Tệp không có ⇒ lời hứa rỗng."""
    thieu = []
    for tep in PHAM_VI:
        for so, duoi in _vien_dan(tep):
            if not duoi:
                continue
            ten = "test_" + so + duoi + ".py"
            if not (THU_MUC_TEST / ten).exists():
                thieu.append(tep + " -> " + ten)
    assert not thieu, "vien dan tro toi tep test khong ton tai:\n  " + "\n  ".join(thieu)


def test_vien_dan_bang_so_tran_phai_XAC_DINH():
    """Số trần chỉ được dùng khi nó trỏ tới **đúng một** tệp.

    Trùng số hiệu là chuyện có thật và phổ biến ở kho này (22 số, xem đầu tệp).
    Khi một số trỏ tới ba tệp, người đọc không có cách nào biết ý người viết là
    tệp nào — và cả ba đều tồn tại nên không công cụ nào kêu.
    """
    mo_ho = []
    for tep in PHAM_VI:
        for so, duoi in _vien_dan(tep):
            if duoi:
                continue                     # có tên rồi thì đã xác định
            uv = _ung_vien(so)
            if len(uv) > 1:
                mo_ho.append(tep + ": `test_" + so + "` co the la " + " | ".join(uv))
    assert not mo_ho, (
        "vien dan bang so tran nhung so ay trung nhieu tep — viet DAY DU TEN:\n  "
        + "\n  ".join(mo_ho))


def test_vien_dan_bang_so_tran_phai_TRO_TOI_MOT_TEP_CO_THAT():
    """Số trần không khớp tệp nào thì nó là một lời hứa với hư không."""
    treo = []
    for tep in PHAM_VI:
        for so, duoi in _vien_dan(tep):
            if duoi or _ung_vien(so):
                continue
            treo.append(tep + ": `test_" + so + "` khong khop tep test nao")
    assert not treo, "\n  ".join(treo)


# ══════════════════════════════════════════════════════════════════════════
#  ĐỐI CHỨNG — chốt này có thật sự ĐỎ được không?
# ══════════════════════════════════════════════════════════════════════════

def test_doi_chung_chot_mo_ho_that_su_do_duoc():
    """⛔ KHÔNG BỎ HÀM NÀY.

    Ba chốt trên hôm nay đều xanh, và **xanh-rỗng trông y hệt xanh-thật**. Bộ
    nhớ dự án ghi đúng lớp bẫy này: *"Không đối chứng thì số 0 không phải phát
    hiện"*. Nên ở đây ta tiêm một chuỗi đã biết là hỏng và đòi nó bị bắt.

    `test_250` là đối chứng THẬT chứ không phải bịa: nó trỏ tới ba tệp
    (`cong_render`, `llm_gateway`, `nexus_sso`), và `test_250_llm_gateway.py`
    lại đúng là phép kiểm chính của cổng — tức đây là cái tên mà một người viết
    chú thích **rất dễ** gõ trần.
    """
    uv = _ung_vien("250")
    assert len(uv) > 1, (
        "doi chung khong con hieu luc: `test_250` gio chi tro toi " + str(uv) +
        ". Chon mot so hieu con trung khac tu `ls tests/ | uniq -d`, dung bo ham nay.")

    gia = "chu thich noi rang tests/test_250 giu hang so nay"
    bat_duoc = [so for so, duoi in
                [(m.group(1), m.group(2) or "") for m in MAU.finditer(gia)]
                if not duoi and len(_ung_vien(so)) > 1]
    assert bat_duoc == ["250"], "chot mo ho KHONG bat duoc vien dan mo ho"


def test_doi_chung_chot_ten_that_su_do_duoc():
    """Cùng lý do: chốt "có tên thì phải tồn tại" cũng phải chứng minh nó cắn."""
    gia = "xem tests/test_999_khong_bao_gio_ton_tai.py"
    m = MAU.search(gia)
    assert m is not None and m.group(2), "mau khong bat duoc dang co ten"
    ten = "test_" + m.group(1) + m.group(2) + ".py"
    assert not (THU_MUC_TEST / ten).exists(), (
        "ai do vua tao " + ten + " that — doi ten trong doi chung nay")
