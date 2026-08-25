"""H39/G9b — dựng lại cổng vào sau khi nó chết.

Bộ test này canh **một loại lỗi rất cụ thể**: kịch bản dựng lại sinh ra một cổng
vào *gần giống* cổng thật. Đó là thứ tệ hơn không có kịch bản, vì nó chạy xong,
không báo lỗi, và cái khác biệt chỉ lộ ra khi một khách nào đó không ra được
Internet.

Đã suýt dính: bản đầu của `dung-lai-cong-vao.sh` do tôi tự viết lại bộ luật
"tương đương" và **thiếu đúng một dòng**:

    ip saddr 10.51.0.0/24 oifname "enp1s0" masquerade

Dòng đó là đường ra cho máy **chưa** được gắn IP riêng — lúc đang tạo, hoặc khi
gắn IP thất bại. Thiếu nó thì máy lên bình thường và không ra được Internet, im
lặng. Nay kịch bản nhúng thẳng **bản sao lưu của bộ luật đang chạy thật**, và
test này chốt rằng hai thứ đó không trôi khỏi nhau.
"""
from __future__ import annotations

from pathlib import Path

import pytest

KICH_BAN = Path("tools/vps_gateway/dung-lai-cong-vao.sh")
SAO_LUU = Path("secrets/cong_vao/nftables.conf")


def _doc(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _ma_thuc_thi(p: Path) -> str:
    """Chỉ phần bash THỰC THI: bỏ dòng chú thích, và bỏ cả khối heredoc đã nháy.

    Không lọc thì hai phép kiểm dưới đây bắt nhầm chính **chú thích** giải thích
    vì sao không được dùng thứ đó — một test báo đỏ vì tài liệu nói đúng là một
    test sẽ bị xoá, không phải được sửa.

    Heredoc nháy (`<<'NFT'`) an toàn với dấu huyền vì shell không diễn giải gì
    bên trong; heredoc KHÔNG nháy (`<<EOF`) mới là chỗ dấu huyền thành
    thay-thế-lệnh.
    """
    ra, trong_heredoc_nhay = [], False
    for dong in _doc(p).splitlines():
        if trong_heredoc_nhay:
            if dong.strip() in ("NFT", "EOF"):
                trong_heredoc_nhay = False
            continue
        if "<<'" in dong:
            trong_heredoc_nhay = True
            continue
        if dong.lstrip().startswith("#"):
            continue
        ra.append(dong)
    return chr(10).join(ra)


# ── 1. Kịch bản phải tồn tại và chạy được trên Debian ───────────────────────

def test_kich_ban_ton_tai():
    assert KICH_BAN.exists(), (
        "khong co kich ban dung lai => cau tra loi cho 'cong vao chet thi sao' "
        "la mot buoi lam bang tay va mot tai lieu khong ai kiem lai")


def test_xuong_dong_kieu_LF():
    """Viết trên Windows, chạy trên Debian. Một `\\r` sót lại biến
    `set -euo pipefail` thành `pipefail<CR>` và bash báo *invalid option name* —
    một câu không chỉ vào nguyên nhân nào cả."""
    assert bytes([13]) not in KICH_BAN.read_bytes(), "phai la LF, khong phai CRLF"


def test_KHONG_chua_dau_huyen():
    """Kịch bản sinh tệp cấu hình bằng heredoc **không nháy** (phải thế, vì nó
    cần thay `$KHOA_RIENG`). Trong heredoc không nháy, dấu huyền là
    thay-thế-lệnh — đã làm hỏng `cai-dat-router.sh` ba lần trong một ngày."""
    assert "`" not in _ma_thuc_thi(KICH_BAN), (
        "dau huyen trong phan thuc thi = thay-the-lenh; dung dau nhay don")


# ── 2. Bộ luật trong kịch bản phải KHỚP bộ đang chạy thật ───────────────────

@pytest.mark.skipif(not SAO_LUU.exists(),
                    reason="chua sao luu bo luat cua cong vao")
def test_bo_luat_trong_kich_ban_KHOP_ban_sao_luu():
    """Trôi khỏi nhau nghĩa là dựng lại xong sẽ ra một cổng vào khác cái đã chạy
    — và không ai biết cho tới khi một khách kêu."""
    kb, sl = _doc(KICH_BAN), _doc(SAO_LUU)
    for dong in sl.splitlines():
        d = dong.strip()
        if not d or d.startswith("#"):
            continue
        assert d in kb, f"kich ban thieu dong cua bo luat that: {d!r}"


@pytest.mark.skipif(not SAO_LUU.exists(), reason="chua sao luu")
def test_duong_ra_cho_may_CHUA_co_IP_rieng_khong_bi_bo_quen():
    """Chính là dòng tôi từng làm mất. Chốt riêng nó, không chỉ chốt chung ở test
    trên — một dòng có lịch sử thì đáng có một phép kiểm mang tên nó."""
    assert "masquerade" in _doc(KICH_BAN)
    assert 'ip saddr 10.51.0.0/24 oifname "enp1s0" masquerade' in _doc(KICH_BAN)


def test_dung_MAP_chu_khong_phai_mot_luat_moi_khach():
    """Ruleset càng dài thì **mọi** kết nối càng chậm. Cách phổ biến — mỗi khách
    một luật `dnat` — chính là cái bẫy đó."""
    kb = _doc(KICH_BAN)
    assert "map vao" in kb and "map ra" in kb
    assert "map @vao" in kb and "map @ra" in kb


def test_KHONG_dung_flush_ruleset():
    """`flush ruleset` xoá cả ruleset của UFW. Nó đã tắt UFW trên chính con này
    một lần rồi, và đường hầm chết im lặng sau lần khởi động lại kế tiếp."""
    assert "flush ruleset" not in _ma_thuc_thi(KICH_BAN)
    assert "delete table ip ltt" in _doc(KICH_BAN), "phai dung khuon delete+table"


# ── 3. Ba thứ thiếu là hỏng im lặng ─────────────────────────────────────────

def test_bat_chuyen_tiep_goi():
    """Thiếu thì WireGuard lên, bắt tay xong, và gói im lặng không đi đâu cả."""
    assert "net.ipv4.ip_forward=1" in _doc(KICH_BAN)


def test_rp_filter_LOOSE_chu_khong_strict():
    """Gói trả về cho khách đi VÀO qua WAN và RA qua `wg0` — đường về không đối
    xứng. `rp_filter=1` (strict) vứt chúng đi, và triệu chứng là *"ping được
    nhưng TCP thì không"*."""
    assert "rp_filter=2" in _doc(KICH_BAN)


def test_MSS_clamp():
    """Đường qua WireGuard MTU 1420. Thiếu clamp thì gói lớn rơi im lặng, và
    triệu chứng là "web nào cũng vào được trừ vài trang"."""
    assert "maxseg size set rt mtu" in _doc(KICH_BAN)


def test_mo_cong_51820_va_noi_UFW():
    """Ảnh Debian của Vultr bật UFW, và UFW chặn 51820 **lẫn** chuyển tiếp."""
    kb = _doc(KICH_BAN)
    assert "51820" in kb
    assert 'DEFAULT_FORWARD_POLICY="ACCEPT"' in kb


# ── 4. Khoá riêng: thứ duy nhất không dựng lại được ─────────────────────────

def test_kich_ban_DOI_khoa_rieng_chu_khong_tu_sinh():
    """Router bên nhà **ghim** khoá công khai của cổng vào. Sinh khoá mới thì
    router không bắt tay được, và triệu chứng là "cổng vào lên rồi mà khách vẫn
    không vào được" — một chỗ rất dễ mất thì giờ.

    Nên kịch bản phải **đòi** khoá cũ, không được tự chạy tiếp với khoá mới."""
    kb = _doc(KICH_BAN)
    assert "wg genkey" not in kb, "khong duoc tu sinh khoa moi"
    assert "exit 2" in kb, "thieu khoa thi phai dung lai"
    assert "secrets/cong_vao/wg_private.key" in kb, "phai chi ro lay khoa o dau"


def test_cong_cu_API_khong_tu_tao_instance():
    """Tạo máy là thao tác tiêu tiền. Tạo nhầm một con là một dòng tiền nhỏ
    nhưng đều, và nó chạy âm thầm."""
    from apps.vps.services import vultr

    for cam in ("tao_instance", "tao_may", "xoa_instance", "xoa_may"):
        assert not hasattr(vultr.VultrClient, cam), (
            f"services/vultr.py khong duoc co {cam}")


def test_cong_cu_gan_lai_IP_GO_truoc_khi_GAN():
    """Một Reserved IP chỉ gắn được vào MỘT instance. Máy cũ có thể đã chết
    nhưng Vultr vẫn coi là đang gắn — không gỡ trước thì lệnh gắn hỏng."""
    nguon = Path("tools/vps_dung_lai_cong_vao.py").read_text(encoding="utf-8")
    assert nguon.index("go_ip(") < nguon.index("gan_ip(")
