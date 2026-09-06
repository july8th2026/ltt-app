"""
test_823 — cắt văn bản thành đoạn để TRUY HỒI, không phải để đọc. (H44 P06 b3)

⛔ Tệp này đo **hành vi**, không đo hình dạng mã. Câu tự hỏi trước mỗi phép kiểm
   (AGENTS.md §4c): *thứ tôi đang khẳng định có tồn tại được nếu hàm không chạy
   không?* Nếu có thì nó không kiểm hành vi.

## Vì sao không tái dùng `apps/ltt_voice/text_pipeline.chia_doan`

Không phải vì tổ chức mã. Hai mục tiêu khác nhau ở **đúng chỗ quyết định**:
chia cho đọc thành tiếng **không được chồng lấn** (chồng là đọc lặp), chia cho
truy hồi **phải chồng lấn** (không chồng thì dữ kiện vắt qua ranh giới biến
mất). `test_CHONG_LAN_cuu_du_kien_vat_qua_ranh_gioi` chốt đúng vế ấy.
"""
from __future__ import annotations

import pytest

from apps.chatltt.services import chia_doan as C


# ── 1. Bất biến của mọi lượt cắt ───────────────────────────────────────────

def _van_dai(n_cau: int = 200) -> str:
    """⛔ Mỗi câu phải có **đuôi riêng**, và đó không phải chi tiết thẩm mỹ.

    Bản đầu của hàm này kết mọi câu bằng đúng một chuỗi (*"...vao mot doan duy
    nhat."*). Hệ quả: 40 ký tự đuôi của đoạn N xuất hiện trong đoạn N+1 **kể cả
    khi chồng lấn bằng 0** — chữ trùng đến từ **văn bản**, không từ cơ chế. Phép
    kiểm cơ chế đo được 9 cặp "chia nhau chữ" ở chế độ `chong=0`, tức nó đang đo
    sự lặp của corpus chứ không đo thứ nó tưởng.

    ⭐ Lần **thứ hai** trong chương trình này dính ví dụ bẩn — lần đầu là
       `"tinh tien theo token"` ở `test_821`, trượt ở cả hai chế độ vì thiếu từ
       chứ không vì thiếu dấu. Cùng một hình dạng: **một fixture khiến phép đo
       có nghĩa khác thứ người viết nghĩ**, và cả hai lần chỉ lộ ra khi có một
       đối chứng bắt buộc phải khác nhau mà lại giống nhau.
    """
    return " ".join(
        f"Cau so {i} noi ve chu de rieng cua no va du dai de khong bi gop het "
        f"vao mot doan duy nhat, ket thuc bang dau hieu Z{i}." for i in range(n_cau))


def test_khong_doan_nao_vuot_tran():
    doan = C.chia(_van_dai(), tran=1200)
    assert doan, "khong cat duoc gi"
    qua = [(i, len(d)) for i, d in enumerate(doan) if len(d) > 1200]
    assert not qua, qua


def test_khong_mat_chu_nao_o_bien():
    """⭐ Đối chứng bắt buộc. Một hàm trả `[]` qua được mọi phép kiểm "không
    vượt trần"; phép kiểm này là thứ chặn nó."""
    van = _van_dai(30)
    doan = C.chia(van)
    ghep = " ".join(doan)
    for tu in ("Cau so 0", "Cau so 15", "Cau so 29"):
        assert tu in ghep, f"mat {tu!r} khi cat"


def test_van_RONG_cho_danh_sach_rong_chu_khong_no():
    assert C.chia("") == []
    assert C.chia("   \n\n  ") == []


# ── 2. Chồng lấn — vế phân biệt với bộ chia của TTS ────────────────────────

def _ngu_canh_hai_ben(doan: list[str], moc: str) -> int:
    """Đoạn nào chứa `moc` với nhiều ngữ cảnh **cả hai bên** nhất — trả về số ký
    tự của bên ÍT hơn. Đó mới là thứ quyết định một trích dẫn có đọc được không.
    """
    tot = -1
    for d in doan:
        i = d.find(moc)
        if i < 0:
            continue
        tot = max(tot, min(i, len(d) - i - len(moc)))
    return tot


def test_CHONG_LAN_cuu_du_kien_vat_qua_ranh_gioi():
    """🔴 Mệnh đề trung tâm, và là lý do không tái dùng bộ chia của `ltt_voice`.

    ⛔ **Bản đầu của phép kiểm này KHÔNG THỂ ĐỎ.** Nó khẳng định `len(d_chong)
       >= len(d_khong)`, và với `chong=0` hai vế bằng nhau nên nó vẫn xanh. Đo
       bằng đột biến (ép `chong = 0` trong `chia()`): **17/17 vẫn xanh**. Một
       phép kiểm không thể đỏ là loại tệ nhất — nó mua về cảm giác đã phủ.

    ⭐ Bản này hỏi đúng thứ chồng lấn sinh ra để giải: một dữ kiện rơi vào chỗ
       nối thì đoạn chứa nó có **ngữ cảnh cả hai bên** không. Quét nhiều vị trí
       đặt dữ kiện, rồi lấy trường hợp TỆ NHẤT — vì cái quyết định chất lượng
       truy hồi là ca xấu nhất, không phải ca trung bình.
    """
    cau = "Mot cau dem khong mang thong tin gi dac biet ca. "
    MOC = "Ma so bi mat la 4C7X9."

    def te_nhat(chong: int) -> int:
        return min(
            _ngu_canh_hai_ben(
                C.chia(cau * k + MOC + " " + cau * 20, tran=600, chong=chong),
                MOC)
            for k in range(6, 20))

    co = te_nhat(150)
    khong = te_nhat(0)

    assert khong >= 0 and co >= 0, "du kien phai ton tai o CA HAI che do"
    assert co > khong, (
        f"chong lan khong cai thien ngu canh hai ben: co={co} khong={khong} — "
        "phep kiem nay phai DO khi co che chong lan bi tat")


def test_hai_doan_LIEN_TIEP_chia_nhau_chu_khi_chong_BAT():
    """⭐ Đo thẳng **cơ chế**, không qua một hệ quả của nó.

    Phép kiểm trên đo *kết quả* (ngữ cảnh hai bên). Phép kiểm này đo *cách* nó
    có được: hai đoạn liền nhau phải dùng chung một khúc chữ. Hai phép kiểm
    cùng chết khi tắt chồng lấn, nhưng chúng chết vì hai lý do khác nhau — nên
    một bản vá sai chỉ qua được một cái.
    """
    van = _van_dai(60)

    def co_phan_chung(doan: list[str]) -> int:
        n = 0
        for truoc, sau in zip(doan, doan[1:]):
            duoi = truoc[-40:]
            if duoi and duoi in sau:
                n += 1
        return n

    assert co_phan_chung(C.chia(van, tran=600, chong=150)) > 0
    assert co_phan_chung(C.chia(van, tran=600, chong=0)) == 0


def test_chong_lan_KHONG_lam_doan_vuot_tran():
    """⛔ Bản vá cho ca A mà làm hỏng ca B thì tệ hơn cái nó chữa."""
    doan = C.chia(_van_dai(), tran=500, chong=200)
    assert not [d for d in doan if len(d) > 500]


def test_chong_BANG_KHONG_thi_khong_doan_nao_lap_dau_doan_truoc():
    """Đối chứng âm cho chính cơ chế chồng: tắt nó thì phần lặp biến mất."""
    doan = C.chia(_van_dai(60), tran=600, chong=0)
    assert len(doan) > 2
    for truoc, sau in zip(doan, doan[1:]):
        assert not sau.startswith(truoc[-60:]), "chong=0 ma van co phan lap"


# ── 3. Không cắt giữa câu ──────────────────────────────────────────────────

def test_KHONG_cat_giua_cau_khi_cau_vua_tran():
    """Một trích dẫn mở đầu bằng nửa câu là một trích dẫn không dùng được."""
    doan = C.chia(_van_dai(40), tran=600)
    for d in doan[1:]:
        dau = d.lstrip()
        assert dau[:1].isupper() or dau[:1].isdigit(), (
            f"doan mo dau bang nua cau: {dau[:60]!r}")


def test_cau_DAI_HON_tran_thi_moi_cat_cung_va_KHONG_mat_chu():
    """Bậc nhượng bộ cuối. Nó phải chạy — nhưng chỉ khi thật sự cần."""
    cau = "A" * 900 + "."
    doan = C.chia(cau, tran=300, chong=0, toi_thieu=1)
    assert len(doan) >= 3
    assert "".join(doan).count("A") == 900


# ── 4. Dọn khoảng trắng của bộ trích PDF ───────────────────────────────────

def test_xuong_dong_DON_la_be_rong_trang_chu_khong_phai_ranh_gioi_y():
    """🔴 Đây là khác biệt giữa một PDF đọc được và một PDF đọc như thơ.

    `\\n` đơn trong PDF sinh ra vì hết bề rộng trang, không phải vì hết ý. Giữ
    nguyên nó thì mọi câu bị chẻ và bộ tách câu đếm sai ranh giới.
    """
    assert C.don("mot cau bi\nchia lam hai dong") == "mot cau bi chia lam hai dong"


def test_xuong_dong_KEP_la_ranh_gioi_THAT_nen_giu():
    """⛔ Chiều ngược lại, và thiếu nó thì bản vá trên dán liền hai đoạn văn."""
    assert C.don("doan mot.\n\ndoan hai.") == "doan mot.\n\ndoan hai."


def test_don_bo_dau_cach_kep_nhung_giu_dau_cach_don():
    assert C.don("a    b\tc") == "a b c"


# ── 5. Mẩu quá ngắn ────────────────────────────────────────────────────────

def test_mau_qua_ngan_bi_bo():
    """Số trang lẻ, tiêu đề chạy — rác của bộ trích. Mỗi mẩu vẫn tốn một hàng
    CSDL và một chỗ trong kết quả tìm."""
    van = "Mot doan that su co noi dung va du dai de duoc giu lai trong ket qua. " * 3
    doan = C.chia(van + "\n\n12\n\n", toi_thieu=40)
    assert not [d for d in doan if len(d) < 40]


def test_tep_NGAN_THAT_khong_bi_bo_sach():
    """🔴 Ca biên mà bản vá trên dễ làm hỏng: một ghi chú ba dòng.

    Bỏ sạch thì người dùng thấy *"trích xong, 0 đoạn"* — một câu trả lời tệ hơn
    cả một lỗi, vì nó nghe như đã thành công.
    """
    doan = C.chia("Ghi chu ngan.", toi_thieu=40)
    assert doan == ["Ghi chu ngan."]


# ── 6. Vân tay ─────────────────────────────────────────────────────────────

def test_bam_on_dinh_va_phan_biet_duoc():
    assert C.bam("abc") == C.bam("abc")
    assert C.bam("abc") != C.bam("abd")
    assert len(C.bam("abc")) == 64


@pytest.mark.parametrize("tran,chong", [(1200, 150), (600, 100), (300, 0)])
def test_moi_cau_hinh_deu_giu_duoc_toan_bo_chu(tran, chong):
    """⭐ Bất biến phải đúng với MỌI cấu hình, không chỉ mặc định — nếu không thì
    nó là một hằng số may mắn chứ không phải một tính chất."""
    van = _van_dai(50)
    ghep = " ".join(C.chia(van, tran=tran, chong=chong))
    for i in (0, 25, 49):
        assert f"Cau so {i} " in ghep
