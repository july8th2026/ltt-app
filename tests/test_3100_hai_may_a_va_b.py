"""HAI MÁY (2026-09-24) — chốt cơ học rằng chỉ MỘT tệp khai vai trò máy A/B.

🔴 VÌ SAO CÓ PHÉP KIỂM NÀY

Ngày 24/09/2026 một phiên viết cả một brief dựa trên giả định *"máy B có một card
RTX 5060 Ti 16 GB"*. Giả định ấy sai theo **hai** hướng: máy B có **hai** card,
và chiếc 5060 Ti mà phiên ấy nghĩ tới là card của **máy A**.

Nguồn nhầm lẫn là cơ học, không phải cẩu thả: **cả hai máy đều có một RTX 5060
Ti**, nên chuỗi "5060 Ti" trong một bản ghi không phân biệt được máy nào. Và kho
này có ~75 tệp nhắc tới hai máy, phần lớn là bản ghi có ngày từ thời cấu hình
khác — ai đọc trúng một bản ghi cũ thì sai, và không có gì kêu.

⭐ Nên phép kiểm này **không** đếm số card. Nó chốt hai điều:

  1. `docs/HAI_MAY_A_VA_B.md` tồn tại, khai CẢ HAI máy, và nói ra câu cảnh báo
     "cả hai đều có 5060 Ti" — vì đó là câu duy nhất ngăn được đúng lỗi 24/09;
  2. ⛔ không tệp nào NGOÀI nguồn chân lý khai một số card **trái** với nó
     (máy A hai card · máy A có 3090 · máy B một card). Bản ghi có ngày được
     miễn trừ TƯỜNG MINH ở `MIEN_TRU` — sửa một bản ghi có ngày là làm giả
     bằng chứng, nên chúng được giữ nguyên và khai ra ở đây.

⛔ ĐỪNG đổi phép kiểm này thành "cấm mọi tệp nhắc tới card của một máy". Đã thử
   trên cây: 132 dòng ở 75 tệp, gần hết là **đúng** (`render_gateway/busy.py`,
   `llama-swap.yaml`, `gpu_check.py` — nơi cái fact ấy là load-bearing). Một chốt
   kêu 132 lần thì bị tắt trong tuần. Cái bắt được lỗi 24/09 là **mâu thuẫn**,
   không phải **nhắc tới**.

⭐ ĐỐI CHỨNG: `test_doi_chung_*` tiêm dòng sai vào tệp tạm rồi chứng minh bộ dò
   ĐỎ. Một phép kiểm chưa từng đỏ thì chưa biết nó bắt được gì.
"""
from __future__ import annotations

import pathlib
import re

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]
NGUON = GOC / "docs" / "HAI_MAY_A_VA_B.md"

#: Đuôi tệp có thể chứa văn xuôi khai cấu hình.
DUOI = {".md", ".py", ".json", ".yaml", ".yml", ".ps1", ".cmd", ".txt", ".toml"}

#: Thư mục không quét: không phải mã của kho, hoặc là kho lưu trữ.
BO_THU_MUC = {
    ".git", ".codex", "node_modules", "venv", ".venv", "__pycache__",
    "vendor", "_luutru", "artifacts", "site-packages", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", "worktrees",
}

#: ⛔ MIỄN TRỪ TƯỜNG MINH — bản ghi CÓ NGÀY. Chúng khai cấu hình của một thời
#: điểm đã qua và **đúng tại thời điểm đó**; sửa chúng là làm giả bằng chứng.
#: Thêm một dòng vào đây là một quyết định, và nó hiện ra trong diff.
MIEN_TRU = {
    "docs/NHAT_KY.md",                              # nhật ký sống, theo ngày
    "docs/ANH_NOI_BO/DUNG_HAI_CARD_MAY_A.md",       # 24/08 — thời máy A hai card
    "docs/ANH_NOI_BO/CHIA_GPU_HAI_MODEL.md",        # 24/08 — thời máy B một card
    "docs/ANH_NOI_BO/KE_HOACH_H37.md",              # 21/08, trạng thái KẾ HOẠCH
    "docs/ANH_NOI_BO/DECISIONS.md",                 # sổ quyết định, theo ngày
    "docs/KE_HOACH_TIEP_2026-08-24.md",             # ngày nằm trong tên tệp
    "docs/audit_ltt_llm/STATE.md",                  # ảnh chụp 01/09, tự khai
    "docs/ltt_llm_dual/SO_LOI_DO_TAI.md",           # sổ lỗi, mỗi mục một ngày
    "docs/VLM_NOI_BO/NGHIEN_CUU_KHA_THI.md",        # nghiên cứu khả thi, 09/2026
    "docs/superpowers/plans/2026-09-23-nang-cap-sau-dien-tap-d1.md",
    "tests/test_3100_hai_may_a_va_b.py",            # chính tệp này (mẫu dò)
}

RE_A = re.compile(r"(?i)(máy|may)\s?A\b")
RE_B = re.compile(r"(?i)(máy|may)\s?B\b")

#: 🔑 BỘ DÒ CHỈ BẮT **LỜI KHAI SỞ HỮU**, không bắt sự đồng hiện.
#:
#: Lý do đo được: chạy bản chỉ cần "máy A" và "3090" trên cùng dòng thì nó kêu ở
#: 5 dòng **đúng** kiểu *"3090 lúc nào do trọng tài residency ở máy A quyết"* —
#: câu về QUAN HỆ giữa hai máy, không phải lời khai máy nào có card nào. Nên luật
#: đòi một **động từ sở hữu** (`có`, `dùng`, `lắp`) hoặc một **giới từ sở hữu**
#: (`của`, `trên`) **đứng sát** tên card: `{0,14}` ký tự. "3090 của máy A" bị bắt;
#: "3090 ... trọng tài residency ở máy A" (cách ~30 ký tự) thì không.
_CO = r"(?:có|co|dùng|dung|lắp|lap|mang)"
_CUA = r"(?:của|cua|trên|tren|ở|o)"
_MA = r"(?:máy|may)\s?A"
_MB = r"(?:máy|may)\s?B"

#: Mỗi mục: (tên luật, regex mâu thuẫn). Chỉ áp cho dòng nhắc ĐÚNG MỘT máy.
LUAT_A = (
    ("máy A hai card",
     re.compile(rf"{_MA}\s*(?:chỉ |chi )?{_CO}\s*(?:đúng |dung )?"
                rf"(?:hai|2)\s*(?:card|GPU|VGA)\b|"
                rf"(?:hai|2)\s*(?:card|GPU|VGA)\b.{{0,14}}{_CUA}\s*{_MA}\b|"
                rf"(?:card|GPU)\s*(?:thứ hai|thu hai)\b.{{0,14}}{_CUA}\s*{_MA}\b",
                re.I)),
    ("máy A có 3090",
     re.compile(rf"{_MA}\s*(?:chỉ |chi )?{_CO}\s*(?:\w+\s+){{0,2}}3090\b|"
                rf"3090\b.{{0,14}}{_CUA}\s*{_MA}\b", re.I)),
)
LUAT_B = (
    ("máy B một card",
     re.compile(rf"{_MB}\s*(?:chỉ |chi )?{_CO}\s*(?:đúng |dung )?"
                rf"(?:một|mot|1)\s*(?:card|GPU|VGA)\b|"
                rf"(?:một|mot|1)\s*(?:card|GPU|VGA)\s*(?:duy nhất|duy nhat)\b"
                rf".{{0,30}}{_MB}\b|"
                rf"{_MB}\b.{{0,30}}(?:một|mot|1)\s*(?:card|GPU|VGA)\s*"
                rf"(?:duy nhất|duy nhat)\b", re.I)),
)

#: ⭐ THOÁT HIỂM CÓ NGUYÊN TẮC: dòng **tự mang ngày** là một bản ghi, không phải
#: lời khai về hôm nay. `(08/2026)`, `TỪ 11/09`, `2026-08-26` — người viết đã nói
#: rõ nó thuộc thời điểm nào, nên nó không lừa được ai. Nhờ đó một tệp mã SỐNG
#: vẫn giữ được ghi chép lịch sử của nó mà không phải vào `MIEN_TRU` cả tệp.
RE_CO_NGAY = re.compile(
    r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}/\d{4}\b|\b\d{1,2}/\d{4}\b|"
    r"\b\d{1,2}/\d{1,2}\b")


def _bo_ma_nguon_va_neo(dong: str) -> str:
    """Bỏ mã nội tuyến và tên định danh — chúng không phải lời khai.

    `ltt_35_5060`, `anh_3090`, `vram_3090_mib`, `GPU-3090` là TÊN, không phải câu
    nói "máy này có card kia". Giữ chúng lại thì bộ dò kêu ở mọi tệp mã.
    """
    dong = re.sub(r"`[^`]*`", " ", dong)               # mã nội tuyến markdown
    dong = re.sub(r"\[[^\]]*\]\([^)]*\)", " ", dong)   # liên kết markdown
    dong = re.sub(r"\w*[_.\-]\d{4}\w*", " ", dong)     # ltt_35_5060, GPU-3090…
    dong = re.sub(r"\d{4}[_.\-]\w+", " ", dong)        # 3090_mib, 5060-ti…
    dong = re.sub(r"[*_]{1,2}", "", dong)              # nhấn mạnh markdown
    return dong


def do_mot_dong(dong: str) -> list[str]:
    """Tên các luật mà `dong` vi phạm. Rỗng = dòng này không mâu thuẫn gì."""
    if RE_CO_NGAY.search(dong):
        return []                       # dòng tự mang ngày ⇒ là bản ghi
    sach = _bo_ma_nguon_va_neo(dong)
    co_a, co_b = bool(RE_A.search(sach)), bool(RE_B.search(sach))
    vi_pham = []
    if co_a and not co_b:
        vi_pham += [ten for ten, mau in LUAT_A if mau.search(sach)]
    if co_b and not co_a:
        vi_pham += [ten for ten, mau in LUAT_B if mau.search(sach)]
    return vi_pham


def quet(goc: pathlib.Path) -> list[tuple[str, int, str, str]]:
    """[(đường tương đối, số dòng, tên luật, nội dung dòng)] trên cả cây."""
    ra = []
    for tep in goc.rglob("*"):
        if not tep.is_file() or tep.suffix.lower() not in DUOI:
            continue
        rel_parts = tep.relative_to(goc).parts
        if BO_THU_MUC & set(rel_parts):
            continue
        rel = tep.relative_to(goc).as_posix()
        if rel in MIEN_TRU or tep.resolve() == NGUON.resolve():
            continue
        try:
            noi_dung = tep.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for i, dong in enumerate(noi_dung.splitlines(), 1):
            for ten in do_mot_dong(dong):
                ra.append((rel, i, ten, dong.strip()[:160]))
    return ra


# ── 1. Nguồn chân lý phải nói đủ ────────────────────────────────────────────

def test_nguon_chan_ly_ton_tai():
    assert NGUON.is_file(), (
        "docs/HAI_MAY_A_VA_B.md là nguồn chân lý duy nhất về vai trò hai máy. "
        "Mất nó thì mọi phiên lại đoán máy theo tên card.")


def test_nguon_khai_ca_hai_may():
    van = NGUON.read_text(encoding="utf-8")
    assert RE_A.search(van), "nguồn chân lý không khai máy A"
    assert RE_B.search(van), "nguồn chân lý không khai máy B"
    assert "5060" in van and "3090" in van, (
        "nguồn chân lý phải gọi tên cả hai loại card — đây là chỗ DUY NHẤT được "
        "phép khai chúng theo máy")


def test_nguon_co_cau_canh_bao_ca_hai_deu_co_5060():
    """Câu cảnh báo này là thứ ngăn đúng lỗi 24/09. Mất nó là mất phép kiểm."""
    van = NGUON.read_text(encoding="utf-8")
    mau = re.compile(r"(?i)cả hai (máy )?(đều )?(có|mang|đều)?.{0,40}5060")
    assert mau.search(van), (
        "docs/HAI_MAY_A_VA_B.md phải nói thẳng rằng CẢ HAI máy đều có một RTX "
        "5060 Ti. Không có câu đó thì tệp chỉ là một bảng nữa, và người đọc vẫn "
        "suy máy từ tên card — đúng cách phiên 24/09 đã sai.")


def test_nguon_tro_ve_ho_so_uuid_thay_vi_chep_uuid():
    """⛔ Hai chỗ khai một điều thì lệch âm thầm: UUID chỉ có MỘT chủ."""
    van = NGUON.read_text(encoding="utf-8")
    assert "gpu_may_b.json" in van, (
        "nguồn chân lý phải TRỎ tới llm_gateway/deploy/gpu_may_b.json cho UUID "
        "card máy B, thay vì tự khai")
    assert not re.search(r"GPU-[0-9a-fA-F]{8}-", van), (
        "⛔ đừng chép UUID vào đây — chủ của chúng là gpu_may_b.json "
        "(tests/test_1200_ghim_gpu_may_b.py đã chốt)")


def test_nguon_duoc_tro_tu_ban_do_khoi_dong():
    """Một nguồn không ai tìm ra thì bằng không có."""
    for tep in (GOC / "CLAUDE.md",
                GOC / "docs" / "00_LTT_OPERATING_CONTRACT.md"):
        van = tep.read_text(encoding="utf-8")
        assert "HAI_MAY_A_VA_B.md" in van, (
            f"{tep.name} phải có một dòng trỏ tới docs/HAI_MAY_A_VA_B.md")


# ── 2. Không tệp nào khác được khai TRÁI nguồn ───────────────────────────────

def test_khong_tep_nao_khai_trai_nguon_chan_ly():
    vi_pham = quet(GOC)
    if vi_pham:
        bang = "\n".join(
            f"  {r}:{i}  [{ten}]  {noi}" for r, i, ten, noi in vi_pham)
        pytest.fail(
            "Có tệp khai số card TRÁI docs/HAI_MAY_A_VA_B.md:\n" + bang +
            "\n\nSự thật: máy A MỘT RTX 5060 Ti · máy B HAI card (3090 + 5060 "
            "Ti). Nếu dòng trên là BẢN GHI CÓ NGÀY thì ⛔ đừng sửa nó — thêm "
            "đường tệp vào MIEN_TRU trong tệp này, kèm ngày của bản ghi.")


# ── 3. ⭐ ĐỐI CHỨNG — bộ dò phải ĐỎ với dòng sai ────────────────────────────

@pytest.mark.parametrize("dong,luat_cho_doi", [
    ("Máy A có hai card RTX 5060 Ti.", "máy A hai card"),
    ("may A co 2 GPU nen job nang roi vao card trong nhat.", "máy A hai card"),
    ("Hai card của máy A đều khoẻ.", "máy A hai card"),
    ("Card thứ hai của máy A đang nằm không.", "máy A hai card"),
    # Dạng nhấn mạnh markdown phải bị bắt như dạng thường.
    ("Đã kiểm: **máy A có 2 card** 5060 Ti.", "máy A hai card"),
    ("Model 27B chạy trên RTX 3090 của máy A.", "máy A có 3090"),
    ("Máy A có card RTX 3090 24 GB.", "máy A có 3090"),
    ("Máy B chỉ có một card.", "máy B một card"),
    ("may B co 1 GPU.", "máy B một card"),
    ("Đã kiểm: máy B chỉ có **một** card RTX 3090.", "máy B một card"),
])
def test_doi_chung_dong_sai_bi_bat(dong, luat_cho_doi):
    assert luat_cho_doi in do_mot_dong(dong), (
        f"bộ dò BỎ LOT dòng sai: {dong!r} — chốt này chưa bắt được gì")


@pytest.mark.parametrize("dong", [
    # Đúng sự thật ⇒ phải im.
    "Máy A có một card RTX 5060 Ti 16 GB.",
    "Máy B có hai card: RTX 3090 và RTX 5060 Ti.",
    # Nhắc cả hai máy trong một câu về QUAN HỆ ⇒ không phải lời khai số card.
    "Trọng tài residency ở máy A quyết 3090 của máy B thuộc LLM hay thuộc ảnh.",
    # Đồng hiện, không sở hữu — đây là 5 dòng ĐÚNG mà bản dò đầu tiên kêu oan.
    "3090 lúc nào do trọng tài residency ở máy A quyết, còn cửa sổ LLM thì khác.",
    "Cuộc tranh 3090 nay do **một** trọng tài residency ở máy A phân xử.",
    "Trọng tài residency ở máy A. Để nhánh đó mở là báo rảnh trong khi 3090 bẩn.",
    # "một card" là mạo từ, không phải lời khai kiểm kê.
    "Sẽ nạp 16 GB lên một card đang vẽ. Máy B có chốt fail-closed cho ca này.",
    "Tài nguyên của LTT là một suất vật lý trên máy B và một card GPU.",
    "Vẽ trước khi máy B xác nhận LTT-3.8 đã rời card ⇒ hai model một card.",
    # Tên định danh mang số, không phải lời khai.
    "Máy A cấp lease qua `anh_3090` và `ltt_35_5060`.",
    "assert may_a.vram_3090_mib == 7",
])
def test_doi_chung_dong_dung_khong_bi_bat(dong):
    assert do_mot_dong(dong) == [], f"bộ dò kêu OAN với dòng đúng: {dong!r}"


@pytest.mark.parametrize("dong,co_bat", [
    # Cùng MỘT lời khai sai: không ngày ⇒ bắt; có ngày ⇒ tha (là bản ghi).
    ("Máy A có hai card 5060 Ti.", True),
    ("Máy A có hai card 5060 Ti (cấu hình 08/2026).", False),
    ("BẢN GHI 2026-08-26: máy A có hai card, job nặng rơi vào card xuất hình.",
     False),
])
def test_doi_chung_thoat_hiem_theo_ngay(dong, co_bat):
    """⭐ Thoát hiểm phải CÓ tác dụng, và phải KHÔNG tha dòng không ngày."""
    assert bool(do_mot_dong(dong)) is co_bat, (
        f"thoát hiểm theo ngày xử sai dòng: {dong!r}")


def test_doi_chung_quet_ca_cay_bat_duoc_dong_tiem(tmp_path):
    """⭐ Tiêm một dòng sai vào tệp tạm rồi chứng minh `quet` ĐỎ.

    Phép kiểm ở §2 chạy trên cây thật và đang XANH. Một phép kiểm chỉ từng xanh
    thì chưa biết nó nhìn thấy gì — nên ở đây ta dựng một cây tí hon, chứng minh
    nó im khi sạch, tiêm MỘT dòng, rồi chứng minh nó kêu đúng chỗ, và chứng minh
    `MIEN_TRU` thật sự miễn trừ (nếu không, `MIEN_TRU` chỉ là trang trí).
    """
    (tmp_path / "docs").mkdir()
    sach = tmp_path / "docs" / "SACH.md"
    sach.write_text("Máy A có một card. Máy B có hai card.\n", encoding="utf-8")
    assert quet(tmp_path) == [], "cây sạch mà bộ dò đã kêu ⇒ nó kêu oan"

    ban = tmp_path / "docs" / "BAN.md"
    ban.write_text(
        "# ghi chú\nMáy B chỉ có một card RTX 5060 Ti 16 GB.\n",
        encoding="utf-8")
    ra = quet(tmp_path)
    assert [(r, i, ten) for r, i, ten, _ in ra] == [
        ("docs/BAN.md", 2, "máy B một card")], (
        f"tiêm một dòng sai mà bộ dò không bắt đúng chỗ: {ra}")

    # Miễn trừ: cùng một dòng sai, nhưng ở đường đã khai trong MIEN_TRU.
    ban.unlink()
    nk = tmp_path / "docs" / "NHAT_KY.md"
    nk.write_text("Máy B chỉ có một card RTX 3090.\n", encoding="utf-8")
    assert quet(tmp_path) == [], (
        "MIEN_TRU không có tác dụng — bản ghi có ngày sẽ bị buộc phải sửa, tức "
        "buộc phải làm giả bằng chứng")

    # Và bỏ miễn trừ ra thì đúng dòng ấy phải kêu lại ⇒ phép trên không rỗng.
    nk.rename(tmp_path / "docs" / "KHONG_MIEN_TRU.md")
    assert quet(tmp_path), "đối chứng rỗng: dòng sai không kêu ở tệp thường"
