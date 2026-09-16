"""test_393 — bộ kiểm `kiem_truoc_khi_cam.py` phải dùng được TRÊN MỘT MÁY TRẮNG.

Tệp công cụ đó tồn tại để **chép sang máy khác** trước khi cắm Codex. Cái giá
của việc chép đi là: mọi giả định về môi trường đều sai. Nên ba tính chất dưới
đây không phải chuyện phong cách — chúng quyết định tệp có được chạy hay không.

⛔ VÀ MỘT TÍNH CHẤT THỨ TƯ, ĐẮT NHẤT: **mỗi phép đo phải có đối chứng.** Bài học
   của đợt 31/08–01/09 là tám lần một dụng cụ cho kết quả đẹp vì nó không đo gì
   cả. Một bộ kiểm "đường gọi thông" mà không thể báo *không thông* thì tệ hơn
   không có — nó biến một sự cố thành một dấu tích xanh.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

TEP = pathlib.Path(__file__).resolve().parents[1] / "tools" / "kiem_truoc_khi_cam.py"
VAN = TEP.read_text(encoding="utf-8")
CAY = ast.parse(VAN)


# ── 1. Chạy được trên một máy chưa cài gì ───────────────────────────────────

def test_CHI_dung_thu_vien_chuan():
    """Máy đích có thể chưa có `requests`, chưa có kho này, chưa có gì.

    ⛔ Một bộ kiểm đòi `pip install` là một bộ kiểm sẽ không được chạy — người
       ta sẽ bỏ qua nó và cắm thẳng, rồi gặp lỗi ở chỗ khó chẩn đoán hơn.
    """
    chuan = {"argparse", "json", "os", "sys", "time", "urllib", "typing",
             "__future__", "dataclasses", "pathlib", "ssl", "http", "re"}
    ngoai = set()
    for n in ast.walk(CAY):
        if isinstance(n, ast.Import):
            ngoai |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
            ngoai.add(n.module.split(".")[0])
    la = ngoai - chuan
    assert not la, f"import ngoai thu vien chuan: {sorted(la)}"


def test_KHONG_phu_thuoc_vao_kho_nay():
    """Nó bị chép đi MỘT MÌNH. Import `platform_core`/`apps` là chép hụt."""
    for cam in ("platform_core", "apps.", "server."):
        assert f"import {cam}" not in VAN and f"from {cam}" not in VAN, (
            f"phu thuoc {cam} — tep nay se vo khi chep sang may khac")


def test_KHONG_goi_dia_chi_noi_bo():
    """Đo ở loopback là đo một thứ khác. `CLAUDE.md` quy tắc 5b đã trả giá:
    trang đẹp ở `127.0.0.1` mà **vỡ với người dùng thật** vì Cloudflare phục vụ
    bản cũ. Máy khách không có loopback của ta."""
    for cam in ("127.0.0.1", "localhost", "192.168."):
        assert cam not in VAN, f"co dia chi noi bo `{cam}` — may khach khong toi duoc"


# ── 2. Nó phải ĐỎ được ──────────────────────────────────────────────────────

def test_moi_phep_do_QUAN_TRONG_deu_co_doi_chung():
    """Ba đối chứng bắt buộc, mỗi cái chặn một kiểu 'xanh vì lý do sai'.

    - khoá SAI phải bị từ chối  → nếu không, "khoá dùng được" đúng tầm thường
    - một lượt gọi thật phải TRỪ TIỀN → nếu không, ta đang đo một đường không
      tính tiền, và mọi kết luận về đường gọi đều vô nghĩa
    - bẫy `Python-urllib` phải còn → nó là thứ khách tự viết sẽ vấp
    """
    for dau in ("doi chung", "CO tru tien", "Python-urllib"):
        assert dau in VAN, f"thieu doi chung: {dau}"

    # 🔴 VÀ ĐỐI CHỨNG KHOÁ SAI PHẢI LÀ MỘT LỜI GỌI THẬT, không phải một nhãn.
    #
    #    Bản đầu của phép kiểm này chỉ tìm chuỗi `"khoa SAI"` trong tệp. Đột
    #    biến cho thấy nó vô dụng: thay cả lời gọi bằng `ma_sai = 401` thì nhãn
    #    vẫn còn, phép kiểm vẫn xanh, và đối chứng đã biến mất.
    #
    # ⭐ Cùng hình dạng với thứ tệp này sinh ra để chống. Nên nay đọc AST và đòi
    #    có ít nhất một lời gọi `_goi` mang một khoá **đã bị sửa** — tức thật sự
    #    hỏi máy chủ bằng một khoá không hợp lệ.
    goi_khoa_sai = []
    for n in ast.walk(CAY):
        if not (isinstance(n, ast.Call) and getattr(n.func, "id", "") == "_goi"):
            continue
        for tham in n.args[1:2]:
            # `a.khoa` tran thi la khoa that; bat ky phep toan nao tren no
            # (noi chuoi, cat bot) deu la mot khoa CO Y lam sai.
            if isinstance(tham, ast.BinOp):
                goi_khoa_sai.append(n.lineno)
    assert goi_khoa_sai, (
        "khong co loi goi nao dung mot khoa DA BI SUA — doi chung 'khoa sai bi "
        "tu choi' chi con la mot nhan, khong con la mot phep do")


def test_DUNG_HAN_khi_doi_chung_tien_truot():
    """Nếu khoá đúng và khoá sai **cùng** được nhận, bộ kiểm phải DỪNG chứ không
    báo đạt — chính nó đang hỏng, và một dụng cụ hỏng nói 'đạt' là ca tệ nhất."""
    assert "DOI CHUNG TRUOT" in VAN
    assert "DUNG doc ket qua duoi day" in VAN


def test_ba_ma_thoat_phan_biet_duoc():
    """0 thông · 1 có mục hỏng · 2 không đo được. Một bộ kiểm luôn trả 0 thì
    không tự động hoá được, và sẽ bị đọc bằng mắt rồi bỏ qua."""
    ma = {n.value.value for n in ast.walk(CAY)
          if isinstance(n, ast.Return) and isinstance(n.value, ast.Constant)
          and isinstance(n.value.value, int)}
    assert {0, 1, 2} <= ma, f"chi thay ma thoat {sorted(ma)}"


# ── 3. Cấu hình nó in ra phải là cấu hình ĐÚNG ──────────────────────────────

def test_KHONG_phat_ra_mot_ban_sao_cau_hinh():
    """🔴 BÁNH CÓC CHO MỘT LỖI ĐÃ GÂY HẬU QUẢ THẬT (02/09).

    Bản đầu của bộ kiểm **in ra một khối `config.toml` tự gõ**. Khối đó thiếu
    `stream_idle_timeout_ms`, `model_reasoning_effort` và `model_catalog_json`
    — ba thứ mà `platform_core/public_api/examples.py` đã có từ trước, mỗi thứ
    kèm lý do đã trả giá.

    ⛔ Hậu quả đo được: một khách dùng bản cấu hình đó bị **cắt luồng ở đúng
       62,0 giây** (`STREAM KHACH-NGAT dur=62.0s`), rồi Codex thử lại và ăn
       `429/503` vì lượt bị bỏ vẫn đang giữ suất.

    ⭐ Đây đúng luật mà kho này đã viết ra ở chỗ khác: *"a second copy of a legal
       promise is a second promise, and the two will differ"*. Một cấu hình cũng
       là một lời hứa. Nên bộ kiểm **đọc** cấu hình, và **chỉ đường** tới công cụ
       chính thức; nó không được tự phát ra một bản.
    """
    for cam in ('[model_providers.', 'wire_api = "responses"',
                'env_key = "LTT_API_KEY"'):
        assert cam not in VAN, (
            f"bo kiem dang PHAT RA cau hinh ({cam!r}). No phai DOC cau hinh va "
            f"chi duong toi cong cu chinh thuc, khong tao ban sao thu hai")


def test_khoa_bat_buoc_KHOP_cau_hinh_chinh_thuc():
    """Danh sách khoá bộ kiểm đòi phải là khoá cấu hình chính thức **thật sự có**.

    ⛔ Không import được `examples.py` từ trong công cụ (nó phải chạy trên máy
       trắng), nên thứ ghép hai đầu là **phép kiểm này** — đúng khuôn
       `test_334::TestBanSaoConLai` của kho.
    """
    import re

    from platform_core.public_api import examples

    chinh_thuc = (examples.codex_config("https://app.lttstudios.com")
                  + chr(10) + examples.codex_profile())
    m = re.search("KHOA_BAT_BUOC = " + chr(123) + "(.*?)" + chr(10)
                  + chr(125), VAN, re.S)
    assert m, "khong tim thay KHOA_BAT_BUOC"
    khoa = re.findall(r'"([a-z_]+)":', m.group(1))
    assert khoa, "danh sach khoa rong"
    thieu = [k for k in khoa if k not in chinh_thuc]
    assert not thieu, (
        f"bo kiem doi khoa {thieu} nhung cau hinh chinh thuc khong he co chung "
        f"— mot trong hai ben da troi")


@pytest.mark.parametrize("khoa", ["request_max_retries", "stream_max_retries",
                                  "stream_idle_timeout_ms", "model_catalog_json"])
def test_doi_dung_khoa_anh_huong_truc_tiep_den_duong_goi(khoa):
    """Các khoá này có mặt vì ảnh hưởng hành vi, không phải vì cho đủ bộ.

    - hai khoá retry: thiếu ⇒ client dùng mặc định upstream và khuếch đại tải
    - `stream_idle_timeout_ms`: thiếu ⇒ luồng bị cắt ở ~62 giây (đo 02/09)
    - `model_catalog_json`: thiếu ⇒ Codex mượn tên một model OpenAI cho lượt
      phụ, cổng ta từ chối, khách thấy "im lặng"
    """
    assert khoa in VAN


def test_CHI_DUONG_toi_cong_cu_chinh_thuc():
    """Bảo người ta "sửa tay cho đúng" là mời lại đúng lỗi vừa xảy ra."""
    assert "/huong-dan/cong-cu" in VAN
    assert "dung sua tay" in VAN or "dung go tay" in VAN


def test_NOI_DUNG_ve_canh_bao_metadata_cua_Codex():
    """🔴 SỬA MỘT CÂU TÔI ĐÃ NÓI SAI VỚI KHÁCH (01/09).

    Bản đầu của bộ kiểm in: *"Codex sẽ in `Model metadata not found`… cảnh báo
    không chặn việc chạy"*, và tôi bảo khách kệ nó. Tôi rút ra kết luận đó từ
    một phép đo đúng (Codex **không** gọi `/api/v1/models`) nhưng suy sai sang
    một kết luận rộng hơn: rằng không có cách nào dập.

    ⛔ Có cách, và nền tảng đã có sẵn từ trước: `model_catalog_json` khai model
       **tại máy khách**. Thiếu nó thì Codex không chỉ cảnh báo — nó **mượn tên
       một model OpenAI** cho lượt phụ, cổng của ta từ chối (fail-closed), và
       khách thấy "im lặng" ở hội thoại dài.

    ⭐ Bài học: *"Codex không gọi /models"* và *"cảnh báo không dập được"* là hai
       mệnh đề khác nhau. Tôi đo được cái thứ nhất rồi công bố cái thứ hai.
    """
    assert "model_catalog_json" in VAN
    assert "MUON TEN" in VAN, (
        "phai noi ro hau qua THAT (muon ten model OpenAI cho luot phu), "
        "khong chi noi 'co mot canh bao'")


@pytest.mark.parametrize("muc", ["Mang va Cloudflare", "Khoa API", "Model",
                                 "/responses", "Tien"])
def test_phu_du_nam_chang_cua_duong_goi(muc):
    """Thiếu một chặng thì bộ kiểm nói 'thông' về một đường nó chưa đi hết."""
    assert muc in VAN

# ── 4. Tài liệu công khai phải MANG ĐỦ, không được rụng ─────────────────────

CAU_HINH_PHAI_CO = {
    "stream_idle_timeout_ms": "luong bi CAT o ~62 giay khi model im tieng (do 02/09)",
    "model_reasoning_effort": "model tieu phan lon max_tokens de suy nghi truoc khi tra loi",
    "model_reasoning_summary": "kem theo reasoning_effort",
    "model_context_window": "khong nen ngu canh kip => 413",
    "model_catalog_json": "Codex muon ten model OpenAI cho luot phu => cong ta tu choi",
    "wire_api": "Codex chi hieu `responses`",
    "base_url": "phai tan cung /api/v1",
    "env_key": "khoa doc tu bien moi truong, khong nhung vao tep",
}


@pytest.mark.parametrize("khoa", sorted(CAU_HINH_PHAI_CO))
def test_cau_hinh_CHINH_THUC_khong_duoc_rung_khoa_nao(khoa):
    """🔴 CHIỀU NGƯỢC LẠI, và nó quan trọng hơn.

    `test_khoa_bat_buoc_KHOP_cau_hinh_chinh_thuc` chốt rằng bộ kiểm không đòi
    khoá lạ. Phép kiểm này chốt điều ngược lại: **cấu hình chính thức không được
    lặng lẽ rụng một khoá**.

    ⛔ Vì sao nó đắt hơn: rụng một khoá thì không có gì đỏ — trang vẫn render,
       khách vẫn cắm được, và hỏng chỉ hiện ra vài phút sau dưới dạng một luồng
       bị cắt hoặc một câu "im lặng". Đó đúng là hình dạng sự cố 02/09.

    Mỗi khoá ở đây có một sự cố thật đứng sau; xem giá trị trong `CAU_HINH_PHAI_CO`.
    """
    from platform_core.public_api import examples

    ca = (examples.codex_config("https://app.lttstudios.com") + chr(10)
          + examples.codex_profile())
    assert khoa in ca, (
        f"cau hinh chinh thuc da rung `{khoa}`. Hau qua da biet: "
        f"{CAU_HINH_PHAI_CO[khoa]}")


def test_cong_cu_chinh_thuc_biet_lam_rieng_cho_VS_Code():
    """Tiện ích VS Code và CLI là **hai bộ đọc khác nhau** — bài học 30/08.

    ⛔ Bộ mặc định của `cam_cli` **không** gồm Codex-VS-Code, nên ai chạy công cụ
       với tuỳ chọn mặc định rồi dùng tiện ích sẽ thiếu cấu hình. Phép kiểm này
       giữ cho lối đi riêng ấy tồn tại.
    """
    import pathlib

    van = (pathlib.Path(__file__).resolve().parents[1]
           / "tools" / "cam_cli.py").read_text(encoding="utf-8")
    assert "MUC_CODEX_VSCODE" in van
    assert "--vscode" in van
