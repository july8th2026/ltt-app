"""`tools/wangp/may_cloud.py` — client cloud của V2, và **luật không-legacy**.

🔴 Vì sao tệp phép kiểm này tồn tại. Ngày 07/09 đo được: năm chỗ trong mã V2
   `import tools.video_cloud`, mà tệp ấy chỉ có trên nhánh V3
   (`claude/ltt-video-ai-v3-p00-3f5713`) và bản thân nó
   `import platform_core.video_gen`. Trên `phien/video-v2-wangp` thì **không có
   tệp nào trong hai thứ đó**, nên `apps/lttvideo/jobs.py:_dieu_phoi_that()` —
   đường `B1` chạy trong worker thật — ném `ModuleNotFoundError` ở lượt job đầu
   tiên có `LTTV_POD_ID`.

   ⭐ Bộ test cũ không thấy vì `_dieu_phoi_that()` trả `None` khi thiếu biến môi
      trường, và mọi phép kiểm đều tiêm `_dieu_phoi` vào. Nghĩa là đường thật
      **chưa từng được nhập một lần nào**. Phép kiểm đầu tiên dưới đây sửa đúng
      chỗ đó: nó `import` thật.
"""
from __future__ import annotations

import ast
import importlib
import pathlib

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]

#: Mọi tệp V2 được phép gọi cloud. Thêm tệp vào đây là một quyết định.
_TEP_V2 = (
    "apps/lttvideo/dieu_phoi.py",
    "apps/lttvideo/jobs.py",
    "tools/wangp/canh_pod.py",
    "tools/wangp/tao_pod.py",
    "tools/wangp/theo_doi.py",
    "tools/wangp/cau_hinh_enhancer.py",
)

#: Mã V2 **không được** chạm tới. Luật đã khoá: "New V2 code: import legacy =
#: FORBIDDEN, call legacy = FORBIDDEN, fallback legacy = FORBIDDEN."
_LEGACY = ("tools.video_cloud", "platform_core.video_gen")


def _cac_import(duong: pathlib.Path) -> set[str]:
    cay = ast.parse(duong.read_text(encoding="utf-8"))
    ten: set[str] = set()
    for n in ast.walk(cay):
        if isinstance(n, ast.Import):
            ten.update(a.name for a in n.names)
        elif isinstance(n, ast.ImportFrom) and n.module:
            ten.add(n.module)
    return ten


@pytest.mark.parametrize("ten_tep", _TEP_V2)
def test_khong_tep_V2_nao_import_legacy(ten_tep):
    for mo_dun in _cac_import(GOC / ten_tep):
        for cam in _LEGACY:
            assert not (mo_dun == cam or mo_dun.startswith(cam + ".")), (
                f"{ten_tep} import legacy {mo_dun!r}")


@pytest.mark.parametrize("ten_tep", _TEP_V2)
def test_moi_mo_dun_cloud_duoc_nhac_toi_deu_CO_THAT(ten_tep):
    """⭐ Phép kiểm bắt được lỗi gốc: `import` thứ được nhắc tới, chứ không đọc
    tên nó. Một tên module chỉ tồn tại trên nhánh khác trông y hệt một tên đúng
    cho tới lúc ai đó thật sự nhập nó."""
    for mo_dun in _cac_import(GOC / ten_tep):
        if mo_dun.startswith("tools.") or mo_dun.startswith("platform_core.video"):
            importlib.import_module(mo_dun)


def test_be_mat_la_ten_CONG_KHAI():
    """Bản cũ để `_rest`/`_graphql` riêng tư rồi cho năm chỗ ngoài module gọi
    vào. Một tên riêng tư dùng xuyên ranh giới module là hợp đồng không ai hứa."""
    from tools.wangp import may_cloud

    assert hasattr(may_cloud.MayCloud, "rest")
    assert hasattr(may_cloud.MayCloud, "graphql")
    assert not hasattr(may_cloud.MayCloud, "_rest"), "bi danh gach duoi quay lai"
    assert not hasattr(may_cloud.MayCloud, "_graphql")


def test_rest_nem_loi_khi_ma_trang_thai_khong_phai_2xx():
    """Im lặng nuốt một 4xx là để một pod không tồn tại trông như một pod tắt."""
    from tools.wangp.may_cloud import LoiMayCloud, MayCloud

    m = MayCloud(goi=lambda *a, **k: (404, {"error": "no such pod"}))
    with pytest.raises(LoiMayCloud):
        m.rest("GET", "/pods/khong-co")


def test_mang_dut_thanh_LoiMayCloud_chu_khong_thanh_ngoai_le_la():
    """`dieu_phoi` bắt `LoiMayCloud`; một `OSError` lọt qua sẽ giết worker."""
    from tools.wangp.may_cloud import LoiMayCloud, MayCloud

    def hong(*a, **k):
        raise OSError("dns")

    with pytest.raises(LoiMayCloud):
        MayCloud(goi=hong).rest("GET", "/pods/x")


def test_graphql_coi_truong_errors_la_that_bai():
    """GraphQL trả 200 kèm `errors` — đọc `data` mà bỏ `errors` là đọc rác."""
    from tools.wangp.may_cloud import LoiMayCloud, MayCloud

    m = MayCloud(goi=lambda *a, **k: (200, {"data": None,
                                            "errors": [{"message": "nope"}]}))
    with pytest.raises(LoiMayCloud):
        m.graphql("query{myself{clientBalance}}")


def test_KHONG_co_ham_nao_xoa_volume():
    """Dừng chi tiêu không cần chạm volume, và đó là chỗ dễ mất dữ liệu nhất."""
    ma = (GOC / "tools/wangp/may_cloud.py").read_text(encoding="utf-8")
    cay = ast.parse(ma)
    chuoi = {n.value for n in ast.walk(cay)
             if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    assert not any("networkvolume" in s.lower() for s in chuoi)
    assert "DELETE" not in chuoi


def test_nap_env_khong_de_bien_da_dat_bi_ghi_de(tmp_path, monkeypatch):
    from tools.wangp.may_cloud import nap_env

    monkeypatch.setenv("LTTV_THU_NGHIEM", "da-co")
    tep = tmp_path / "app.env"
    # BOM co y: `CLAUDE.md` quy tac 1 ke chuyen mot BOM da lam sap production.
    tep.write_bytes("﻿LTTV_THU_NGHIEM=trong-tep\nLTTV_MOI=gia-tri\n"
                    .encode("utf-8"))
    nap_env(tep)
    import os

    assert os.environ["LTTV_THU_NGHIEM"] == "da-co"
    assert os.environ["LTTV_MOI"] == "gia-tri"


# ── cau_hinh_enhancer: bon khoa, va ly do tung khoa ─────────────────────────

def test_bon_khoa_dich_dung_voi_thu_da_do_tren_C_CLOUD():
    from tools.wangp import cau_hinh_enhancer as ce

    assert ce.MUON["enhancer_enabled"] == 4          # Qwen3.5-9B Abliterated
    assert ce.MUON["enhancer_mode"] == 0             # 0 = tu dong (duong API)
    assert ce.MUON["prompt_enhancer_quantization"] == "quanto_int8"
    assert ce.MUON["prompt_enhancer_speculative_decoding"] == 0


def test_KHONG_chon_model_5_vi_no_dang_chan_boi_loi_cuBLAS():
    from tools.wangp import cau_hinh_enhancer as ce

    assert ce.MUON["enhancer_enabled"] != 5
    assert ce.MUON["prompt_enhancer_quantization"] != "gguf"


def test_khac_biet_chi_ke_khoa_that_su_lech():
    from tools.wangp import cau_hinh_enhancer as ce

    assert ce.khac_biet(dict(ce.MUON)) == {}
    assert ce.khac_biet({**ce.MUON, "enhancer_enabled": 5}) == {
        "enhancer_enabled": 4}
    # Khoa vang mat cung la lech — `enhancer_mode` vang chinh la ca ban dau.
    thieu = {k: v for k, v in ce.MUON.items() if k != "enhancer_mode"}
    assert ce.khac_biet(thieu) == {"enhancer_mode": 0}


def test_khac_biet_KHONG_dung_toi_khoa_ngoai_danh_sach():
    """WanGP tự ghi hàng trăm khoá vào tệp ấy. Ta chỉ được đụng bốn khoá."""
    from tools.wangp import cau_hinh_enhancer as ce

    cu = {**ce.MUON, "deepy_enabled": 1, "checkpoints_paths": ["ckpts"]}
    assert ce.khac_biet(cu) == {}


# ── tim_app_env: cay rieng KHONG mang theo tep bi gitignore ────────────────

def test_tim_app_env_uu_tien_duong_dan_truyen_vao(tmp_path):
    from tools.wangp.may_cloud import tim_app_env

    tep = tmp_path / "rieng.env"
    tep.write_text("A=1\n", encoding="utf-8")
    assert tim_app_env(tep) == tep
    assert tim_app_env(str(tep)) == tep


def test_tim_app_env_nem_loi_RO_RANG_khi_duong_dan_sai(tmp_path):
    from tools.wangp.may_cloud import LoiMayCloud, tim_app_env

    with pytest.raises(LoiMayCloud) as e:
        tim_app_env(tmp_path / "khong-co.env")
    assert "khong thay tep env" in str(e.value)


def test_tim_app_env_lui_ve_GOC_KHO_DUNG_CHUNG_khi_cay_thieu(monkeypatch, tmp_path):
    """🔴 Đây là ca thật đã hỏng: `secrets/` bị gitignore, mà `git worktree add`
    chỉ chép thứ git theo dõi — nên **mọi cây riêng đều thiếu** `app.env`, và cả
    bốn công cụ cloud chết ngay dòng đầu khi chạy từ cây riêng.

    Phép kiểm đứng ở một thư mục **không có** `secrets/`, rồi đòi hàm vẫn tìm ra
    tệp ở gốc kho dùng chung — thứ `git rev-parse --git-common-dir` chỉ ra.
    """
    from tools.wangp.may_cloud import tim_app_env

    cay = tmp_path / "cay-rieng-gia"
    (cay / "secrets").mkdir(parents=True)  # thu muc co, tep thi KHONG
    monkeypatch.chdir(cay)
    assert not (cay / "secrets" / "app.env").exists()

    goc = tmp_path / "kho-goc"
    (goc / "secrets").mkdir(parents=True)
    that = goc / "secrets" / "app.env"
    that.write_text("RUNPOD_API_KEY=gia\n", encoding="utf-8")

    import subprocess

    def gia(cmd, *a, **kw):
        assert cmd[:3] == ["git", "rev-parse", "--git-common-dir"]
        return subprocess.CompletedProcess(cmd, 0, stdout=str(goc / ".git"),
                                           stderr="")

    monkeypatch.setattr(subprocess, "run", gia)
    assert tim_app_env() == that


def test_tim_app_env_KHONG_neo_duong_dan_tuyet_doi(tmp_path):
    """Đường dẫn tuyệt đối gõ tay sai ngay khi ai đó đổi chỗ kho. Phải hỏi git."""
    import ast
    import inspect

    from tools.wangp import may_cloud

    cay = ast.parse(inspect.getsource(may_cloud.tim_app_env))
    hang = {n.value for n in ast.walk(cay)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    assert not any(":" in s and ("\\" in s or "/" in s) and s[1:3] == ":\\"
                   for s in hang), "co duong dan tuyet doi go tay"
    assert "--git-common-dir" in hang


def test_bon_cong_cu_cloud_deu_dung_tim_app_env():
    """Một chỗ sót là một công cụ chết ở cây riêng."""
    import ast

    for ten in ("tao_pod.py", "theo_doi.py", "canh_pod.py",
                "cau_hinh_enhancer.py"):
        ma = (GOC / "tools" / "wangp" / ten).read_text(encoding="utf-8")
        cay = ast.parse(ma)
        goi = {n.func.id for n in ast.walk(cay)
               if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        assert "tim_app_env" in goi, f"{ten} khong dung tim_app_env"
        hang = {n.value for n in ast.walk(cay)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        assert "secrets/app.env" not in hang, f"{ten} van neo cung duong dan"


# ── cai_dat.sh: cong bo-qua-cai phai SO kien truc GPU ──────────────────────

def test_cong_bo_qua_cai_co_so_kien_truc_GPU():
    """🔴 `_ARCH_SAGE` từng được **ghi ra mà không ai đọc lại**, nên nó không
    canh gì. Đổi card (A100 8.0 → H100 9.0) thì ba mức cũ vẫn đủ, cổng bỏ qua,
    và ta chạy tiếp trên bản SageAttention biên dịch cho card cũ — im lặng."""
    ma = (GOC / "tools" / "wangp" / "cai_dat.sh").read_text(encoding="utf-8")
    than = ma.split("co_moi_truong_ben() {", 1)[1].split("}", 1)[0]
    assert "TEP_ARCH" in than, "cong khong doc tep kien truc"
    assert "$ARCH" in than, "cong khong so voi kien truc do duoc"


def test_kien_truc_duoc_GHI_LAI_sau_khi_cai():
    """Cổng chỉ chặt được nếu có thứ để so. Thiếu bước ghi thì lần sau luôn lệch
    và ta cài lại vĩnh viễn — sai về phía tốn tiền."""
    ma = (GOC / "tools" / "wangp" / "cai_dat.sh").read_text(encoding="utf-8")
    assert '> "$TEP_ARCH"' in ma


def test_KHONG_doan_kien_truc_khi_khong_do_duoc():
    """Một giá trị dự phòng im lặng biến một phép đo thành một lời đoán —
    lỗi này đã xảy ra thật 06/09 (rơi về `8.0` trong khi card là H100)."""
    ma = (GOC / "tools" / "wangp" / "cai_dat.sh").read_text(encoding="utf-8")
    assert "exit 4" in ma
    assert "do_arch" in ma

def _backslash_n_NGOAI_nhay(raw: bytes) -> list[int]:
    """Vị trí các byte `backslash`+`n` nằm **ngoài** dấu nháy.

    🔴 Bản đầu của phép kiểm này quét cả trong nháy, và nó báo động sai ngay lập
       tức trên `printf '%s\n' "$KHOA_RIENG"` — nơi dãy ấy là **mã định dạng
       của printf**, hoàn toàn đúng.

    ⭐ Ranh giới đúng là dấu nháy, và nó không phải một tinh chỉnh cho vừa: ngoài
      nháy, escape một chữ cái thường như `n` là **vô nghĩa** trong shell, nên
      mọi lần xuất hiện ở đó đều là một dấu xuống dòng đã bị nuốt. Trong nháy
      đơn thì ngược lại — nó là hai ký tự chữ thật, và `printf` đọc chúng.
    """
    ra, i, n = [], 0, len(raw)
    nhay = None            # None | b"'" | b'"'
    while i < n - 1:
        c = raw[i:i + 1]
        if nhay is None:
            if c == b"#":                      # chu thich: bo toi het dong
                j = raw.find(b"\n", i)
                i = n if j < 0 else j + 1
                continue
            if c in (b"'", b'"'):
                nhay = c
            elif c == b"\\" and raw[i + 1:i + 2] == b"n":
                ra.append(i)
            elif c == b"\\":
                i += 2                          # escape hop le: bo qua ca hai
                continue
        elif c == nhay:
            nhay = None
        elif nhay == b'"' and c == b"\\":
            i += 2
            continue
        i += 1
    return ra


def test_KHONG_script_shell_nao_co_dau_xuong_dong_BI_NUOT():
    """🔴 Lỗi thật, đã **commit và sống sót**: `cai_dat.sh:76` chứa hai byte
    `backslash`+`n` chữ thật thay cho một dấu xuống dòng nối dòng.

    Lệnh thành `nvidia-smi ... n` — một tham số rác. `nvidia-smi` lỗi, `ARCH`
    rỗng, script thoát mã 4. Tức **bộ cài không chạy được**, và ta chỉ biết sau
    khi đã tạo pod và bắt đầu tính tiền.

    ⛔ `bash -n` **KHÔNG** bắt được: ngoài dấu nháy, dãy ấy là một escape hợp lệ
       (thành chữ `n`). Cú pháp đúng, ngữ nghĩa sai — đúng lớp lỗi mà một bộ
       kiểm cú pháp không thể thấy.

    ⭐ Nguồn gốc: công cụ Bash nuốt một lớp backslash khi ghi tệp. Sổ đã ghi luật
      ấy cho heredoc; đây là bằng chứng nó áp cho **mọi** lần ghi, và rằng phép
      kiểm phải đọc **byte**, không đọc dòng.
    """
    import pathlib as _pl

    goc = _pl.Path(__file__).resolve().parents[1]
    pham = []
    for tep in sorted(list((goc / "tools").rglob("*.sh"))
                      + list((goc / "setup").rglob("*.sh"))):
        raw = tep.read_bytes()
        for i in _backslash_n_NGOAI_nhay(raw):
            pham.append(f"{tep.relative_to(goc)}:{raw[:i].count(b'\n') + 1}")
    assert not pham, (
        "dau xuong dong bi nuot thanh chu `n` (bash -n KHONG thay): " + str(pham))


def test_doi_chung_bo_do_KHONG_bao_dong_tren_printf_hop_le():
    """⛔ Đối chứng hai chiều cho bộ dò trên — nếu thiếu, nó có thể là một bộ dò
    luôn trả rỗng và mọi phép kiểm dùng nó xanh vĩnh viễn."""
    assert _backslash_n_NGOAI_nhay(b"""printf '%s\\n' \"$X\"
""") == []
    assert _backslash_n_NGOAI_nhay(b'echo "a\\nb"') == []
    assert _backslash_n_NGOAI_nhay(b"cmd --a 2>/dev/null \\n  | head -1")


def test_cai_dat_kiem_ca_ban_CUDA_cua_torch_chu_khong_chi_kien_truc_GPU():
    """⛔ Bốn điều kiện cũ của `co_moi_truong_ben` — python / kho / kiến trúc
    GPU / `import torch` — đều **xanh** khi đổi ảnh container từ cu130 sang
    cu128, vì không điều kiện nào hỏi torch được build cho CUDA nào.

    ⇒ Pod khởi động với torch lệch ảnh và **bỏ qua cài lại**, im lặng. Và đó
      đúng là hướng HM-9 đang chọn, nên lỗ hổng này sẽ nổ ở đúng lượt tới.
    """
    import pathlib as _pl

    ma = (_pl.Path(__file__).resolve().parents[1] / "tools" / "wangp"
          / "cai_dat.sh").read_text(encoding="utf-8")
    than = ma.split("co_moi_truong_ben()", 1)[1].split("\n}", 1)[0]
    assert "TEP_CUDA" in than, "khong kiem ban CUDA cua torch"
    assert "do_cuda_torch" in than
    assert "torch.version.cuda" in ma, "khong do bang chinh torch"
