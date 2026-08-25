"""Bo cuc cong lap trinh vien: THANH BEN CO NHOM, khong phai 16 tab phang.

🔴 VI SAO CO TEP NAY. Chu san pham 25/08: *"toi thay co qua nhieu tab du thua .
   nhu : Project , Playground"* va *"giao dien hien thi van qua basic"*. Chan
   doan: 16 muc phang tren mot dai cuon ngang, va chung tron BA NGHE khac nhau
   — cam vao cong cu / tra cuu API / xem tai khoan — vao cung mot hang ngang cap.

⭐ Nhung tinh chat duoi day la thu de TROI NGUOC lai nhat: them mot trang moi
   thi phan xa dau tien luon la them mot dong vao thanh dieu huong. Test nay
   lam viec do thanh mot cong: muc cap cao nhat phai nam trong mot nhom, va so
   muc cap cao nhat co tran cung.
"""
from __future__ import annotations

import re
import uuid

import pytest

from tests.test_197_developer_api_tab import _register, portal  # noqa: F401


#: Tran muc cap cao nhat. Khong phai con so tuy tien: qua muc nay thi thanh ben
#: khong con quet mot luot duoc, va do dung la trang thai ta vua thoat ra khoi.
TRAN_MUC = 12


def _thanh_ben(text: str) -> str:
    khoi = re.search(r'<nav class="app-side".*?</nav>', text, re.S)
    assert khoi, "khong tim thay thanh ben"
    return khoi.group(0)


def test_thanh_ben_gom_theo_nhom_chu_khong_phang(portal):  # noqa: F811
    _register(portal, f"nhom-{uuid.uuid4().hex[:6]}@example.com")
    ben = _thanh_ben(portal.get("/developers").text)

    nhom = re.findall(r'<div class="nhom">([^<]+)</div>', ben)
    assert len(nhom) >= 3, f"can it nhat ba nhom, thay {nhom}"

    # Moi muc phai nam DUOI mot tieu de nhom. Mot muc mo coi la dau hieu ai do
    # them route roi nho dan vao thanh dieu huong ma khong xep nhom.
    truoc_nhom_dau = ben[:ben.index('<div class="nhom">')]
    assert "<a href=" not in truoc_nhom_dau, "co muc nam ngoai moi nhom"


def test_so_muc_cap_cao_nhat_co_tran(portal):  # noqa: F811
    """Chot chinh: khong de thanh ben troi ve lai 16 muc phang."""
    _register(portal, f"tran-{uuid.uuid4().hex[:6]}@example.com")
    ben = _thanh_ben(portal.get("/developers").text)
    muc = re.findall(r'<a href="(/developers[^"]*)"', ben)
    assert len(muc) <= TRAN_MUC, f"{len(muc)} muc cap cao nhat: {muc}"
    # Va khong trung: hai duong dan giong nhau la mot muc bi khai hai lan.
    assert len(set(muc)) == len(muc), muc


@pytest.mark.parametrize("con,cha", [
    ("/developers/projects", "/developers/keys"),
    ("/developers/playground", "/developers/tools"),
    ("/developers/jobs", "/developers/logs"),
    ("/developers/quickstart", "/developers/cli"),
    ("/developers/privacy", "/developers/settings"),
    ("/developers/notifications", "/developers"),
])
def test_trang_bi_ha_cap_van_song_va_van_tim_lai_duoc(portal, con, cha):  # noqa: F811
    """⛔ HA KHOI THANH DIEU HUONG != XOA.

    Sau muc bi ha cap 25/08 van con nguyen route. Mot URL da di vao dau trang,
    tin nhan ho tro va anh chup man hinh thi viec no 404 la thiet hai THAT, con
    viec no roi khoi thanh dieu huong thi khong.

    Va no phai TIM LAI DUOC: dung o trang cha thi dai muc con phai co no.
    """
    _register(portal, f"con-{uuid.uuid4().hex[:6]}@example.com")
    assert portal.get(con).status_code == 200, con

    # Dai muc con cua CHA phai tro toi con.
    dai = re.search(r'<nav class="dev-sub".*?</nav>', portal.get(cha).text, re.S)
    assert dai, f"{cha} khong co dai muc con"
    assert f'href="{con}"' in dai.group(0), f"{cha} khong tro toi {con}"


def test_dung_o_muc_con_thi_muc_cha_sang(portal):  # noqa: F811
    """Khong co trang nao lam thanh ben trong rong khong co gi duoc chon."""
    _register(portal, f"sang-{uuid.uuid4().hex[:6]}@example.com")
    ben = _thanh_ben(portal.get("/developers/projects").text)
    assert 'href="/developers/keys"' in ben
    dang_mo = re.findall(r'<a href="([^"]+)"[^>]*class="active"', ben)
    assert dang_mo == ["/developers/keys"], dang_mo


def test_chi_co_dung_mot_aria_current_page(portal):  # noqa: F811
    """`aria-current="page"` tra loi "day la trang hien tai" — hai cau tra loi
    cho mot cau hoi thi trinh doc man hinh khong biet tin cai nao.

    Trang co dai muc con thi dai DO mang `page`; thanh ben chi noi "nhanh nay
    dang mo" bang `aria-current="true"`.
    """
    _register(portal, f"aria-{uuid.uuid4().hex[:6]}@example.com")
    for duong in ("/developers", "/developers/keys", "/developers/projects",
                  "/developers/usage", "/developers/webhooks"):
        text = portal.get(duong).text
        assert text.count('aria-current="page"') == 1, duong


def test_cong_cu_cam_exe_co_mat_trong_cong_lap_trinh_vien(portal):  # noqa: F811
    """🔴 Chu san pham 25/08: *"tool ho tro gan len claude va codex chua day len
       trang"*.

    Do that: bo cai da nam tren may chu va `/tai/cong-cu-cam` tra 200, nhung
    KHONG mot trang nao trong khu `/developers` tro toi no — nen voi nguoi da
    dang nhap, cong cu coi nhu khong ton tai. Nguoi vua tao khoa xong dang dung
    dung o `/developers/cli`, va do la thoi diem duy nhat cau "de toi ghi cau
    hinh ho" co gia tri.
    """
    _register(portal, f"exe-{uuid.uuid4().hex[:6]}@example.com")
    assert 'href="/tai/cong-cu-cam"' in portal.get("/developers/cli").text


def test_moi_che_do_chay_deu_co_lop_mau_trong_css():
    """Nhãn chế độ chạy phải có lớp CSS khớp CHÍNH XÁC tên chế độ.

    🔴 LỖI ĐÃ MẮC 25/08. Template sinh `che-do-{{ execution_mode | lower }}`.
       Chế độ thật là `ASYNC_JOB` → lớp `che-do-async_job`, nhưng CSS viết
       `.che-do-async`. Nhãn vẫn hiện, chỉ là **màu xám mặc định**.

    ⛔ Nó hỏng IM LẶNG: trang vẫn đúng, không lỗi console, không request hỏng —
       chỉ mất đúng thứ mà nhãn màu được thêm vào để làm (nói ngay cho khách
       biết họ phải viết mã kiểu gì: đợi rồi hỏi lại, hay nhận ngay).

    ⭐ Bắt được bằng cách đo `getComputedStyle(...).color` trên trang render,
       KHÔNG bằng cách đọc HTML — HTML có lớp đúng như template khai; thứ sai
       là bảng kiểu không có lớp đó. Đọc một trong hai bên không thấy gì.
    """
    import pathlib

    from platform_core.public_api import protocol

    goc = pathlib.Path(__file__).resolve().parent.parent
    css = (goc / "server" / "static" / "ltt.css").read_text(encoding="utf-8")

    thieu = [che_do for che_do in protocol.MODE_RULES
             if f".che-do-{che_do.lower()}" not in css]
    assert thieu == [], (
        f"{len(thieu)} che do chay khong co lop mau: {thieu}\n"
        "Template sinh `che-do-{execution_mode|lower}`, nen ten lop phai khop\n"
        "CHINH XAC. Sai ten thi nhan ve mau xam mac dinh va khong ai thay.")


# ── Loi hua cot loi cua trang cam ───────────────────────────────────────────

def test_moi_khu_be_mat_chi_chua_dia_chi_CUA_NO():
    """Trong khu của một bề mặt, KHÔNG được xuất hiện địa chỉ của bề mặt khác.

    🔴 ĐÂY LÀ LÝ DO TRANG CẮM ĐƯỢC DỰNG LẠI, không phải thẩm mỹ. Bản xếp chồng
       cũ đặt hai giá trị dễ sai nhất của cả khu API cạnh nhau, cùng ở dạng
       chép được, không gì nói cái nào của ai:

           /api/v1   (Codex)   ><   /api   (Claude Code, Desktop)  — lệch 4 ký tự
           ltt_llm             ><   ltt-llm-claude-compat          — chỉ Desktop

       Chép nhầm thì Codex nhận `404`, hoặc nút gửi của Claude Desktop **im
       lặng không làm gì cả**. Cả hai triệu chứng đều vô dụng.

    ⭐ Đo thật 25/08 trên trang render: khu Claude Desktop có **0** lần
       `/api/v1`. Phép kiểm này giữ con số đó ở 0.

    ⚠️ Mục "chỗ hay vấp — chung cho mọi công cụ" ở CUỐI trang có nhắc cả hai
       địa chỉ, và đó là ĐÚNG: việc của nó là giải thích sự khác biệt. Nó nằm
       ngoài mọi khu, không có `<pre>` và không có nút Sao chép — nên nó là
       văn xuôi để đọc, không phải cấu hình để chép.
    """
    import re

    from platform_core.public_api import examples

    goc = "https://app.lttstudios.com"
    for be_mat in examples.be_mat_cam(goc):
        ma = " ".join(str(doan) for _ma, _tep, doan in be_mat["buoc"])

        # ⚠️ Một khu có thể khai NHIỀU địa chỉ (xem `dia_chi_theo`): `vscode`
        #    phục vụ cả tiện ích Claude Code lẫn tiện ích Codex, và chúng dùng
        #    hai giao thức khác nhau. Phép kiểm phải soi TẤT CẢ, nếu không nó
        #    sẽ báo đỏ trên một khu hoàn toàn đúng — và người sửa sẽ "chữa" một
        #    thứ không hỏng.
        khai = {d for _t, d, _m in be_mat.get("dia_chi_theo")
                or ((None, be_mat["dia_chi"], None),)}

        # `/api` là tiền tố của `/api/v1`, nên phải so có ranh giới.
        co_trong_ma = set()
        if re.search(re.escape(f"{goc}/api") + r"(?![/\w])", ma):
            co_trong_ma.add(f"{goc}/api")
        if f"{goc}/api/v1" in ma:
            co_trong_ma.add(f"{goc}/api/v1")

        lac = sorted(co_trong_ma - khai)
        assert lac == [], (
            f"khu `{be_mat['ma']}` khai {sorted(khai)} nhung doan ma trong khu "
            f"con dung {lac} — day dung la cai bay trang nay duoc dung lai de "
            f"dong. Neu khu nay THAT SU phuc vu nhieu cong cu thi khai them o "
            f"`dia_chi_theo`, dung bo phep kiem.")


def test_chi_claude_desktop_dung_ten_model_compat():
    """Tên model tương thích chỉ được xuất hiện ở đúng bề mặt cần nó.

    Nó KHÔNG phải tên sản phẩm — nó là tên tuyến của một cổng tương thích, tồn
    tại vì Claude Desktop lọc danh sách model trước khi vẽ ô chọn. Rò nó sang
    bề mặt khác là bán sai tên hàng.
    """
    from platform_core.public_api import examples

    for be_mat in examples.be_mat_cam("https://app.lttstudios.com"):
        dung_compat = be_mat["model"] == examples.DESKTOP_MODEL
        assert dung_compat == (be_mat["ma"] == "desktop"), (
            f"khu `{be_mat['ma']}` dung model `{be_mat['model']}`; chi be mat "
            f"`desktop` duoc dung `{examples.DESKTOP_MODEL}`")
