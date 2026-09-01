r"""
test_386 — bất biến của `tools/nhap_kho_giong_cu.py`.

Công cụ này phát **dữ liệu giọng của người thật cho mọi tài khoản**, nên những
thứ nó suy ra phải đúng, và phải sai theo cách ồn ào chứ không lặng lẽ.

Ba bất biến, mỗi cái đến từ một lỗi đã xảy ra:

  ① Làn suy từ **`engine`**, không từ TÊN.
  ② Tên hiển thị **duy nhất** — trùng là vòng lặp chết giữa chừng.
  ③ Thiếu tên thì **VỠ**, không sinh tên tự động.
"""
from __future__ import annotations

import ast
import collections
import pathlib

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]
TEP = GOC / "tools" / "nhap_kho_giong_cu.py"


def _hang(ten: str):
    """Đọc một hằng số cấp module bằng AST, KHÔNG import module.

    🔴 `nhap_kho_giong_cu.py` thay `sys.stdout` bằng một `TextIOWrapper` ngay ở
       cấp module (để đệm theo dòng khi log ra tệp — xem lý do ở chính tệp đó).
       Import nó trong pytest làm vỡ bộ bắt output của pytest:
       `ValueError: I/O operation on closed file` ở **mọi** phép kiểm trong tệp,
       kể cả những phép không đụng tới stdout.

    ⛔ Và nó vỡ ở `tempfile.py` với một thông điệp không nhắc gì tới stdout, nên
       nguyên nhân thật không nhìn ra được từ dấu vết. Bài học chung: một công
       cụ đổi trạng thái TOÀN CỤC lúc import thì không import được trong test —
       đọc mã nguồn của nó thay vì chạy nó.

    ⭐ Và với một phép kiểm về **bất biến của mã nguồn**, đọc AST vốn đã đúng hơn
       chạy: không phụ thuộc thư viện, không tác dụng phụ, không cần kho cũ.
    """
    cay = ast.parse(TEP.read_text(encoding="utf-8"))
    for n in cay.body:
        if isinstance(n, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == ten for t in n.targets):
            return ast.literal_eval(n.value)
    raise AssertionError(f"khong thay hang so `{ten}` o cap module")


def test_lan_suy_tu_ENGINE_chu_khong_tu_ten():
    """`f5tts` → `vi`, `xtts` → `en`. Không có đường thứ ba.

    🔴 Kho cũ có `hoathinh_female`, `meoquan_men`, `tamlyhoc_men`,
       `cg_huong_nam` — bốn cái tên tiếng Việt rành mạch, và cả bốn là người nói
       **tiếng Anh**. Chúng là tên kênh/nhân vật, không phải tên người nói.

    ⛔ Tôi đã đọc những cái tên ấy như dữ liệu một lần và viết vào tài liệu rằng
       nhãn ngôn ngữ của kho cũ "không đáng tin". Nó đáng tin: cột `engine` bên
       cạnh mang câu trả lời, và ASR xác nhận **25/25** khớp.
    """
    assert _hang("LAN_THEO_ENGINE") == {"f5tts": "vi", "xtts": "en"}


def test_KHONG_suy_lan_tu_ten_giong():
    """Không được có đường nào đọc tên để đoán làn.

    ⛔ Hỏi CÂY CÚ PHÁP, đừng khớp chuỗi — một bánh cóc khớp với chính lời giải
       thích của nó thì không chốt gì (đã mắc bốn lần trong dự án này).
    """
    cay = ast.parse(TEP.read_text(encoding="utf-8"))
    for n in ast.walk(cay):
        # `lan = ...` không được lấy từ bất cứ thứ gì tên có "ten"
        if isinstance(n, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "lan" for t in n.targets):
            nguon = ast.dump(n.value)
            assert "'ten'" not in nguon and '"ten"' not in nguon, (
                f"lan dang duoc suy tu ten: {ast.unparse(n)}")


def test_ten_hien_thi_KHONG_TRUNG_NHAU():
    """Trùng tên = vòng lặp nhập chết ở giữa, sau khi đã thu tiền vài lượt.

    `uq_voice_owner_ten` là ràng buộc DUY NHẤT theo (chủ, tên). Cả 25 giọng nhập
    dưới **một** tài khoản, nên hai tên giống nhau là cửa ghi danh trả lỗi ở
    lượt thứ hai — và mười lượt trước đó đã ghi danh xong, đã tính tiền, và đã
    nằm trong CSDL.
    """
    dem = collections.Counter(_hang("TEN").values())
    trung = {k: v for k, v in dem.items() if v > 1}
    assert not trung, f"ten hien thi trung nhau: {trung}"


def test_ten_khong_lap_lai_ngon_ngu():
    """Làn đã hiện thành một nhãn riêng — viết "EN" vào tên là nói hai lần.

    Tên cũ của hệ cũ đều đuôi "EN" (`Alex - Male Education EN`) vì hệ ấy không
    có chỗ nào khác để ghi. Hệ mới có `ngon_ngu` và một chip hiển thị, nên tên
    phải bỏ phần ấy đi.
    """
    xau = [t for t in _hang("TEN").values()
           if " EN" in t or " VI" in t or t.endswith("EN") or t.endswith("VI")]
    assert not xau, f"ten con lap lai ngon ngu: {xau}"


def test_thieu_ten_thi_VO_chu_khong_sinh_ten_tu_dong():
    """Một cái tên sinh tự động đi thẳng ra danh mục khách nhìn thấy.

    Và không ai rà lại nó, vì nó trông như đã được ai đó đặt.
    """
    src = TEP.read_text(encoding="utf-8")
    ham = next(n for n in ast.walk(ast.parse(src))
               if isinstance(n, ast.FunctionDef) and n.name == "main")
    doan = ast.unparse(ham)
    assert "thieu_ten" in doan, "main() phai kiem giong nao chua dat ten"
    assert "return 2" in doan


def test_chi_nhap_voi_tai_khoan_local():
    """Nó chạm tiền thật, và sổ credit chỉ ghi thêm."""
    assert _hang("DUOI_THU") == ".local"
    src = TEP.read_text(encoding="utf-8")
    assert "a.nhap and not a.email.endswith(DUOI_THU)" in src


def test_mac_dinh_la_XEM_chu_khong_phai_NHAP():
    """Chạy nhầm không được tạo ra 21 hồ sơ giọng và 21 lần thu tiền."""
    # đọc thẳng khai báo trong main(): `--nhap` phải là store_true
    src = TEP.read_text(encoding="utf-8")
    assert '"--nhap", action="store_true"' in src
    assert '"--xem"' not in src, (
        "khong duoc co co `--xem`: XEM la MAC DINH, va mot co rieng cho no se "
        "khien ai do tuong phai bat gi do de xem")


#: Hai mươi lăm mã giọng của kho cũ, ĐÓNG BĂNG.
#:
#: ⭐ Đóng băng ở đây thay vì `skipif` khi không có kho cũ, và lý do là một luật
#:    của chính dự án này: **một test bị bỏ qua là một test không canh gì cả.**
#:    Một `skipif` sẽ làm phép kiểm này im lặng trên mọi máy phát triển — tức
#:    trên hầu hết các máy — và chỉ nói ở đúng máy có kho cũ.
#:
#: ⇒ Danh sách hằng chạy ở MỌI máy; phần đối chiếu với kho thật chỉ chạy thêm ở
#:   máy có kho. Không nhánh nào rỗng nghĩa.
MA_CU = (
    'Huong_KT',
    'alex_male_education',
    'bella_nu',
    'bietdoi_girl',
    'cg_huong_nam',
    'giffen_male_social',
    'harry_male_adventure',
    'hoathinh_female',
    'ht3d_men',
    'khanh_male_entertainment',
    'kinhte_nam',
    'kyan_nam',
    'lam_male_storytelling',
    'lego_nu',
    'lichsu_nam',
    'lily_nu',
    'meodang_men',
    'meoquan_men',
    'nguyetnga_nu',
    'ninhdon_nam',
    'phatgiao_nu',
    'qtrungg_male_narrator',
    'quan_male_dialogue',
    'roger_male_dialogue',
    'tamlyhoc_men',
)


def test_TEN_phu_het_25_ma_da_dong_bang():
    """`TEN` phải phủ đúng 25 mã. Chạy ở mọi máy, không cần kho cũ.

    🔴 25, không phải 24. `kyan_nam` từng vắng mặt khỏi mọi phép đếm vì ba clip
       của nó ở 24000/24000/**22050** Hz và bộ nối từ chối cả giọng, in một dòng
       "BO:" giữa hai mươi lăm dòng. Con số "24 giọng" đã được báo cho chủ sản
       phẩm trước khi phát hiện ra.
    """
    ten = _hang("TEN")
    assert len(MA_CU) == 25
    assert sorted(ten) == sorted(MA_CU), {
        "thieu_trong_TEN": sorted(set(MA_CU) - set(ten)),
        "thua_trong_TEN": sorted(set(ten) - set(MA_CU)),
    }


def test_kho_cu_that_van_dung_25_ma():
    """Nếu máy này CÓ kho cũ thì kho ấy phải khớp danh sách đóng băng.

    ⛔ KHÔNG dùng `skipif`. Khi không có kho, phép kiểm vẫn chạy và vẫn khẳng
       định một điều thật (danh sách hằng có 25 mã); nó chỉ **thêm** một phép so
       khi kho có mặt. Một nhánh `if` không làm phép kiểm rỗng nghĩa ở đây —
       khác hẳn một `skipif`, thứ làm cả phép kiểm biến mất.
    """
    kho = pathlib.Path("D:/Voiceclone_TTS/configs/voice_profiles.yaml")
    assert len(MA_CU) == 25
    if not kho.exists():
        return
    """Mọi giọng trong kho cũ phải có tên soạn tay. 25, không phải 24.

    🔴 `kyan_nam` từng vắng mặt khỏi mọi phép đếm vì ba clip của nó ở
       24000/24000/**22050** Hz và bộ nối từ chối cả giọng. Con số "24 giọng"
       đã được báo cho chủ sản phẩm trước khi phát hiện ra.
    """
    import yaml
    d = yaml.safe_load(open(kho, encoding="utf-8")).get("profiles", {})
    cu = sorted(k for k in d if not str(k).startswith("_"))
    assert cu == sorted(MA_CU), {
        "kho_co_ma_moi": sorted(set(cu) - set(MA_CU)),
        "ma_da_bien_mat": sorted(set(MA_CU) - set(cu)),
    }
