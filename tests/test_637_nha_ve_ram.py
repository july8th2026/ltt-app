"""
Nhả model về RAM, không nhả hẳn về đĩa — chốt một tính chất đang ĐÚNG TÌNH CỜ.

🔴 VÌ SAO TỆP NÀY TỒN TẠI. Máy B có **một** card, nên model phải nhả ra vào liên
   tục giữa LLM và ảnh. Chi phí của mỗi lần nhả nằm ở lần **nạp lại**:

     nạp từ page cache (RAM)  ->  vài giây
     nạp từ đĩa lạnh          ->  lâu hơn nhiều

   `llama-swap` nhả bằng cách **tắt tiến trình** `llama-server`. Model không nằm
   lại trong RAM của tiến trình nào cả — nhưng tệp GGUF thì **vẫn nằm trong page
   cache của hệ điều hành**, vì `llama.cpp` mở nó bằng `mmap` mặc định. Đo
   04/09: máy B có 192 GB RAM, trống 82 GB, GGUF 15,33 GiB — thừa chỗ.

⛔ NHƯNG KHÔNG AI ĐANG CANH ĐIỀU ĐÓ. Thêm một cờ `--no-mmap` vào `cmd`, hoặc một
   dịch vụ khác ăn hết RAM, là mỗi lần nhả trở thành một lần đọc đĩa 15 GiB —
   **và không có gì kêu**. Cùng đúng hình dạng với sự cố "tràn trọng số sang RAM
   chủ" đo ngày 22/08: `/health` xanh, nội dung đúng, chỉ tốc độ lặng lẽ mất đi
   một phần.

⭐ Nên tệp này biến một tính chất **tình cờ** thành một tính chất **được canh**.
"""
from __future__ import annotations

import pathlib
import re

import pytest

YAML = pathlib.Path(__file__).resolve().parents[1] / "llm_gateway" / "deploy" / "llama-swap.yaml"


@pytest.fixture(scope="module")
def van() -> str:
    assert YAML.is_file(), f"khong thay {YAML}"
    return YAML.read_text(encoding="utf-8")


def _cac_dong_cmd(van: str) -> list:
    """Các dòng nằm trong khối `cmd:` của mọi hồ sơ model."""
    ra, trong_cmd = [], False
    for dong in van.splitlines():
        if re.match(r"^\s*cmd:\s*\|", dong):
            trong_cmd = True
            continue
        if trong_cmd:
            # Khối `cmd` kết thúc khi gặp một khoá cùng cấp (vd `proxy:`).
            if dong.strip() and not dong.startswith((" " * 6, "\t")):
                trong_cmd = False
                continue
            if dong.strip():
                ra.append(dong.strip())
    return ra


def test_khong_ho_so_nao_dung_no_mmap(van):
    """⛔ `--no-mmap` biến mỗi lần nhả thành một lần đọc đĩa 15 GiB.

    Với `mmap` (mặc định), trọng số được ánh xạ từ **page cache**, nên tắt tiến
    trình rồi bật lại chỉ tốn vài giây. Với `--no-mmap`, mỗi lần nạp là một lần
    đọc thật từ ổ đĩa.

    ⭐ Trên một máy phải swap model liên tục, đó là khác biệt giữa "nhả về RAM"
       và "nhả hẳn về đĩa" — đúng thứ chủ dự án yêu cầu giữ.
    """
    xau = [d for d in _cac_dong_cmd(van) if "--no-mmap" in d]
    assert not xau, (
        "co ho so dung `--no-mmap`, nen moi lan nha model se phai doc lai 15 GiB "
        f"tu dia: {xau}")


def test_mmap_khong_bi_tat_o_bat_ky_dau(van):
    """Chặn cả các biến thể: `--no-mmap`, `--mmap 0`, `--mmap false`."""
    for mau in (r"--no-mmap", r"--mmap\s+0\b", r"--mmap\s+false\b"):
        assert not re.search(mau, van, re.IGNORECASE), f"tat mmap qua `{mau}`"


def test_han_cho_nap_du_cho_TRUONG_HOP_XAU_NHAT(van):
    """`healthCheckTimeout` phải đủ cho một lần nạp **từ đĩa lạnh**.

    ⛔ Không đặt theo trường hợp thường (page cache, vài giây). Page cache là thứ
       **có thể mất** — sau khởi động lại máy, hoặc khi một tiến trình khác ăn
       hết RAM. Đặt hạn theo trường hợp thường nghĩa là lần nạp lạnh đầu tiên sau
       mỗi lần reboot sẽ bị coi là **hỏng**.
    """
    m = re.search(r"^healthCheckTimeout:\s*(\d+)", van, re.MULTILINE)
    assert m, "khong khai `healthCheckTimeout`"
    assert int(m.group(1)) >= 300, (
        f"healthCheckTimeout={m.group(1)}s co the khong du cho mot lan nap "
        "15 GiB tu dia lanh")


def test_ttl_du_dai_de_khong_nap_lai_moi_luot(van):
    """TTL quá ngắn thì mỗi lượt khách là một lần nạp lại — đắt và chậm.

    ⚠️ Đây là chốt về **hướng**, không phải về một con số cụ thể: nó chỉ kêu khi
       ai đó hạ TTL xuống mức làm việc nhả/nạp thành chuyện xảy ra giữa hai câu
       hỏi liên tiếp của cùng một khách.
    """
    ttl = [int(x) for x in re.findall(r"^\s*ttl:\s*(\d+)", van, re.MULTILINE)]
    assert ttl, "khong ho so nao khai `ttl`"
    assert min(ttl) >= 300, f"co ttl qua ngan: {ttl}"


def test_moi_ho_so_deu_co_unloadTimeout(van):
    """Nhả phải có hạn: một tiến trình không chịu chết là card không bao giờ về."""
    so_ho_so = len(re.findall(r"^\s*ttl:\s*\d+", van, re.MULTILINE))
    so_han = len(re.findall(r"^\s*unloadTimeout:\s*\d+", van, re.MULTILINE))
    assert so_han == so_ho_so, (
        f"{so_ho_so} ho so nhung chi {so_han} khai `unloadTimeout`")


def test_khong_khai_groups(van):
    """⛔ `groups` cho phép hai hồ sơ cùng sống — trên card này là một lần OOM.

    Hai hồ sơ text cộng lại ~43 GB trên một card 24,5 GB. Chú thích cuối
    `llama-swap.yaml` đã ghi thẳng điều đó; chốt này giữ cho nó không bị thêm vào
    trong một lần sửa vội.
    """
    assert not re.search(r"^groups:", van, re.MULTILINE), (
        "khai `groups` la cho phep hai ho so cung nam tren card")
