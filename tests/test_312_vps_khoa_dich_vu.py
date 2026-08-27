"""Khoá SSH của **dịch vụ**: quyền tệp, và bước siết quyền phải TỰ KIỂM.

## Chuyện đã xảy ra, 2026-08-27

Một khách trả 1.490 credit và nhận về chữ "Lỗi". Nguyên nhân: ba dịch vụ chạy
bằng **LocalSystem**, còn khoá SSH nằm ở `C:\\Users\\<người>\\.ssh\\` nơi ACL cho
cả tài khoản người dùng. Từ góc nhìn của SYSTEM đó là khoá "hở", và OpenSSH
**từ chối dùng nó**.

Ba tính chất của lỗi này, và tệp test chốt từng cái:

**① Nó im lặng.** `/vps` vẫn bán, `/health/ready` vẫn 200, `tools/gate.py` xanh.
Tín hiệu duy nhất là một khách đã trả tiền.

**② Phép kiểm đang có đo nhầm thứ.** `vps_doctor.py` **có** kiểm SSH — nhưng
bằng `ssh ltt-gw`, một **bí danh trong SSH config**, chạy bằng **tài khoản con
người**. Nó không đi qua đường worker đi, nên nó **xanh trong khi worker chết**.

**③ Bước siết quyền của bộ cài nói dối.** `2-cai-dat.ps1` chạy

    icacls $secrets /inheritance:r /grant:r "SYSTEM:..." "Administrators:..."

rồi in `Ok 'Chi SYSTEM va Administrators doc duoc secrets\\'`. Nhưng
`/inheritance:r` chỉ bỏ ACE **thừa kế**, `/grant:r` chỉ thay quyền của chủ thể
**được liệt kê** — một ACE **tường minh** của chủ thể khác sống sót nguyên vẹn.
Câu "Ok" đó sai suốt từ khi viết.

⭐ Và tệp `vps_khoa_dich_vu.ps1` của chính đợt sửa này **mắc lại đúng lỗi ③ ở
lần chạy đầu**: in "da siet ACL" rồi thoát `EXITCODE=0` trong khi ACL y nguyên.
Thứ vạch ra nó là bước in lại ACL thật ở cuối. Đó là bài học tổng quát mà tệp
này chốt: **một bước bảo mật không tự kiểm là một bước sẽ nói dối vào đúng ngày
nó thất bại.**
"""
from __future__ import annotations

import pathlib
import re

GOC = pathlib.Path(__file__).resolve().parent.parent
SETUP = GOC / "setup"
TOOLS = GOC / "tools"

#: Hai kịch bản siết quyền thư mục bí mật. Cả hai phải theo cùng một luật.
KICH_BAN_SIET = (
    SETUP / "2-cai-dat.ps1",
    SETUP / "vps_khoa_dich_vu.ps1",
)


def _khong_chu_thich(noi_dung: str) -> str:
    """Bóc chú thích PowerShell.

    ⚠️ Bắt buộc, và đây là lần thứ **sáu** lớp lỗi này lặp trong dự án: chính
       khối chú thích giải thích cái bẫy `/grant:r` chứa đúng chuỗi mà phép kiểm
       "phải có /remove" đi tìm, nên nó xanh vì lời bàn về mã chứ không vì mã.
    """
    noi_dung = re.sub(r"(?s)<#.*?#>", " ", noi_dung)
    return re.sub(r"(?m)^\s*#.*$", " ", noi_dung)


# ── 1 · Bước siết quyền phải XOÁ được ACE tường minh ──────────────────────

def test_siet_quyen_KHONG_chi_dua_vao_grant_r():
    """`/inheritance:r /grant:r` **không** xoá được một ACE tường minh có sẵn.

    Đo 27/08 trên máy đang chạy: sau khi chạy đúng dòng đó, `secrets\\` vẫn còn
    ACE tường minh cho tài khoản người dùng — tức `app.env` (khoá phiên, khoá mã
    hoá token, hash mật khẩu admin, token Proxmox, khoá Vultr) nằm dưới một ACL
    yếu hơn câu mà bộ cài vừa in ra.
    """
    for tep in KICH_BAN_SIET:
        ma = _khong_chu_thich(tep.read_text(encoding="utf-8"))
        assert "icacls" in ma, f"{tep.name}: khong con buoc siet quyen nao"
        assert re.search(r"icacls[^\n]*/remove", ma), (
            f"{tep.name}: chi dung `/grant:r`, khong co `/remove`. Mot ACE tuong "
            f"minh cua chu the khac se song sot, va buoc nay se in 'Ok' cho mot "
            f"viec no khong lam")


def test_siet_quyen_TU_KIEM_LAI_va_hong_to():
    """Một bước bảo mật không tự kiểm là một bước sẽ nói dối vào đúng ngày nó
    thất bại — và cả hai kịch bản đã từng làm đúng thế.
    """
    for tep in KICH_BAN_SIET:
        ma = _khong_chu_thich(tep.read_text(encoding="utf-8"))
        assert "Get-Acl" in ma, (
            f"{tep.name}: khong doc lai ACL sau khi siet — khong co cach nao "
            f"biet buoc do co tac dung khong")
        assert "throw" in ma, (
            f"{tep.name}: doc lai ACL nhung khong `throw` khi con chu the thua. "
            f"In ra roi di tiep thi khong khac gi khong kiem")


def test_danh_sach_chu_the_duoc_phep_GIONG_NHAU_o_moi_cho():
    """Ba nơi cùng quyết định "ai được đọc bí mật": hai kịch bản và một công cụ
    chẩn đoán. Ba danh sách chép tay thì lần sửa sau chỉ sửa một."""
    mong_doi = {"system", "administrators", "trustedinstaller"}

    from tools.vps_kiem_khoa import CHU_THE_DUOC_PHEP
    assert set(CHU_THE_DUOC_PHEP) == mong_doi

    for tep in KICH_BAN_SIET:
        ma = _khong_chu_thich(tep.read_text(encoding="utf-8"))
        m = re.search(r"chuThePhep\s*=\s*@\(([^)]*)\)", ma)
        assert m, f"{tep.name}: khong khai danh sach chu the duoc phep"
        co = {x.strip().strip("'\"").lower() for x in m.group(1).split(",")}
        assert co == mong_doi, f"{tep.name}: danh sach lech: {sorted(co)}"


# ── 2 · Phép kiểm phải đi ĐÚNG ĐƯỜNG mà worker đi ─────────────────────────

def test_cong_cu_kiem_khoa_dung_DUNG_tang_van_chuyen_cua_worker():
    """🔴 Bài học lớn nhất của cả sự cố.

    `vps_doctor.py` kiểm SSH bằng `ssh ltt-gw` — bí danh trong SSH config, chạy
    bằng tài khoản con người. Worker thì chạy `ssh -i <đường dẫn khoá>
    -o BatchMode=yes` dưới LocalSystem. Hai đường khác nhau, và đường dễ hơn
    **xanh trong khi đường khó hơn chết**.

    ⭐ Một phép kiểm phải đi đúng đường mà thứ nó canh sẽ đi. Đo một đường dễ
       hơn rồi gọi nó là bằng chứng cho đường khó hơn là cách tạo ra một phép
       kiểm xanh vĩnh viễn.
    """
    ma = (TOOLS / "vps_kiem_khoa.py").read_text(encoding="utf-8")
    assert "from apps.vps.services.ssh_lenh import" in ma, (
        "cong cu kiem khoa khong dung `ssh_lenh` — no phai di qua DUNG tang "
        "van chuyen ma worker dung, khong dung mot lenh ssh tu viet")
    assert "DichDen(" in ma and "chay_ssh(" in ma
    assert not re.search(r'"ssh",\s*"-o"', ma), (
        "cong cu dang tu dung lenh ssh thay vi goi `chay_ssh` — no se troi khoi "
        "tuy chon that cua worker ngay lan sua sau")


def test_kiem_ca_QUYEN_lan_NOI_THAT():
    """Hai thứ khác nhau, và chỉ cái thứ nhất là cái đã hỏng mà không ai thấy.

    Khoá đúng quyền vẫn có thể sai nội dung; khoá đúng nội dung vẫn có thể sai
    quyền. Kiểm một cái rồi kết luận cho cả hai là cách bỏ sót đúng cái đang hỏng.
    """
    ma = (TOOLS / "vps_kiem_khoa.py").read_text(encoding="utf-8")
    assert "def chu_the_thua(" in ma, "khong co phep kiem QUYEN"
    assert "def _noi_thu(" in ma, "khong co phep kiem NOI THAT"
    assert "--nhanh" in ma, (
        "khong co che do chi-kiem-quyen — can no de chay duoc o cho khong noi "
        "duoc toi ha tang")


def test_nghiem_thu_sau_cai_dat_CO_GOI_phep_kiem_nay():
    """Một công cụ chẩn đoán không ai chạy là một công cụ không tồn tại.

    `4-nghiem-thu.ps1` là bước cuối của quy trình cài — nếu khoá dịch vụ hỏng
    quyền thì đó là chỗ phải biết, không phải lúc một khách trả tiền.
    """
    ma = (SETUP / "4-nghiem-thu.ps1").read_text(encoding="utf-8")
    assert "vps_kiem_khoa" in ma, (
        "4-nghiem-thu.ps1 khong goi `tools/vps_kiem_khoa.py` — loi khoa dich vu "
        "se lai im lang cho toi khi co khach tra tien")


# ── 3 · Khoá dịch vụ phải sống cùng chỗ với mọi bí mật khác ───────────────

def test_khoa_dich_vu_thuoc_secrets_KHONG_thuoc_ho_so_nguoi_dung():
    """Bí mật của **dịch vụ** không được sống trong hồ sơ của **con người**.

    Mọi kỷ luật quyền của nền tảng áp lên `C:\\LTTPlatform\\secrets\\`; một tệp
    nằm ngoài đó là một tệp bộ cài không với tới, và ACL của nó trôi mà không ai
    biết. Đó chính là hình dạng của sự cố 27/08.
    """
    ma = (SETUP / "vps_khoa_dich_vu.ps1").read_text(encoding="utf-8")
    assert "LTT_VPS_ROUTER_SSH_KEY" in ma and "LTT_VPS_GATEWAY_SSH_KEY" in ma, (
        "kich ban khong con tro hai bien khoa vao secrets\\")
    # Bản trong `.ssh` của con người KHÔNG bị đụng tới — họ vẫn phải tự dùng được.
    assert "GIU NGUYEN" in ma, (
        "kich ban khong con noi ro ban trong .ssh duoc giu nguyen; xoa no di la "
        "lay mat khoa cua chinh chu san pham")


def test_doi_app_env_thi_phai_NAP_LAI_ENV_chu_khong_chi_restart():
    """🔴 Cái bẫy dự án này đã trả giá **ba** lần.

    Dịch vụ chạy qua nssm, và nssm **nướng** biến môi trường vào đăng ký dịch vụ
    **lúc cài** (`AppEnvironmentExtra`). `server\\run.py` chỉ đọc `os.environ` —
    nó **không** tự đọc `secrets\\app.env` lúc chạy. Nên:

        sửa app.env  →  Restart-Service  →  dịch vụ lên lại với ENV CŨ

    Không lỗi nào báo. Cấu hình đúng, dịch vụ chạy, thay đổi không có tác dụng.

    Hai lần đầu: cổng VLM máy B, và `LTT_PUBLIC_API_TOOLS` ngày 23/08. Lần thứ
    ba là chính `vps_khoa_dich_vu.ps1` ở lượt chạy đầu — nó đổi đường dẫn khoá,
    restart, báo xong, và worker vẫn dùng đường dẫn **cũ**. Triệu chứng: máy vẫn
    vào `loi` với **nguyên văn** thông báo cũ, trỏ vào đường dẫn cũ.

    ⭐ `nap_lai_env.ps1` đã tồn tại sẵn cho việc này, kèm một đoạn cảnh báo dài ở
       đầu tệp. Nó có sẵn mà vẫn dẫm — nên chốt bằng máy, không bằng trí nhớ.
    """
    ma = _khong_chu_thich(
        (SETUP / "vps_khoa_dich_vu.ps1").read_text(encoding="utf-8"))
    assert "nap_lai_env.ps1" in ma, (
        "kich ban sua app.env nhung khong goi `nap_lai_env.ps1` — dich vu se len "
        "lai voi ENV CU va khong co loi nao bao")
    # Và không được tự chép lại logic nssm: hai bản sẽ lệch.
    assert "AppEnvironmentExtra" not in ma, (
        "dang tu dung nssm thay vi goi `nap_lai_env.ps1` — hai ban logic se lech")


def test_ghi_app_env_KHONG_BOM():
    """Quy tắc 1 của `CLAUDE.md`, và nó **đã thực sự làm sập production**.

    `Out-File -Encoding utf8` của PowerShell 5.1 chèn BOM, `json.load()` vỡ, và
    `/health/ready` trả 503 trong khi dịch vụ vẫn chạy bình thường.
    """
    ma = _khong_chu_thich((SETUP / "vps_khoa_dich_vu.ps1").read_text(encoding="utf-8"))
    assert "WriteAllText" in ma and "UTF8Encoding($false)" in ma, (
        "kich ban ghi app.env khong dung [IO.File]::WriteAllText + "
        "UTF8Encoding($false)")
    assert not re.search(r"Out-File[^\n]*app\.env|Set-Content[^\n]*\$envFile", ma), (
        "dang ghi app.env bang Out-File/Set-Content — PowerShell 5.1 chen BOM")
