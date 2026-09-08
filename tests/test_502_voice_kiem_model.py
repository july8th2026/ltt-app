r"""KIỂM TỆP MODEL THEO NỘI DUNG — `voice_sidecar/kiem_model.py`.

## Vì sao có tệp kiểm này

`os.path.isfile()` trả lời *"có tệp không"*, không trả lời *"tệp đó có phải
model không"*. Lớp lỗi ấy đã xảy ra thật ở một hệ khác (`D:\Viral`,
`giong_piper.py::_onnx_hop_le`, 07/08/2026): proxy trả **HTTP 200 kèm trang
HTML**, tệp được lưu, `isfile` xanh **vĩnh viễn**, và giọng offline mất hẳn mà
không lần nào tự sửa được.

⭐ Nên phép kiểm ở đây đo **nội dung**, và mỗi hàm test dưới đây là một kiểu
   hỏng CỤ THỂ, không phải một lời khẳng định chung chung.

## ⛔ Ba đối chứng, và chúng quan trọng ngang phần khẳng định

Một phép kiểm chỉ chạy đường hỏng sẽ xanh cả khi cổng bị gỡ. Nên tệp này luôn
đi theo cặp:

    tep LANH   -> KHONG duoc bao loi   (chong bao oan)
    tep HONG   -> PHAI bao loi         (chong bo sot)
    khong dinh vi duoc -> BO QUA       (fail-open, khong chan may dev)
"""
from __future__ import annotations

import ast
import json
import pathlib
import struct

import pytest

from voice_sidecar import kiem_model

GOC = pathlib.Path(__file__).resolve().parents[1]


# ── dựng một snapshot giả ────────────────────────────────────────────────────

def _safetensors_lanh(duong: pathlib.Path, co: int = 1_200_000) -> None:
    """Một tệp safetensors ĐỦ HỢP LỆ cho phép kiểm: u64 độ dài + JSON + đệm."""
    dau = json.dumps({"__metadata__": {"format": "pt"}}).encode()
    with open(duong, "wb") as f:
        f.write(struct.pack("<Q", len(dau)))
        f.write(dau)
        f.write(b"\0" * max(0, co - 8 - len(dau)))


def _onnx_lanh(duong: pathlib.Path, co: int = 1_200_000) -> None:
    """ONNX là protobuf: byte đầu 0x08 (field 1, varint) là dạng hay gặp."""
    with open(duong, "wb") as f:
        f.write(b"\x08\x07\x12\x04test")
        f.write(b"\0" * max(0, co - 10))


@pytest.fixture()
def snapshot(tmp_path: pathlib.Path) -> pathlib.Path:
    """Một snapshot LÀNH. Từng test tự làm hỏng đúng một thứ."""
    (tmp_path / "update").mkdir()
    _safetensors_lanh(tmp_path / "update" / "model.safetensors")
    _onnx_lanh(tmp_path / "denoiser.onnx")
    _onnx_lanh(tmp_path / "speaker_encoder.onnx")
    (tmp_path / "config.json").write_text('{"a": 1}', encoding="utf-8")
    return tmp_path


# ── 1. đối chứng: bản lành phải IM LẶNG ──────────────────────────────────────

def test_snapshot_lanh_khong_bao_loi(snapshot):
    """⛔ ĐỐI CHỨNG. Không có test này thì một hàm `return ["loi"]` cũng xanh."""
    assert kiem_model.kiem_thu_muc(str(snapshot)) == []


# ── 2. ca hỏng THẬT đã xảy ra ở hệ khác: HTML mang tên model ─────────────────

@pytest.mark.parametrize("ten", ["denoiser.onnx", "speaker_encoder.onnx"])
def test_trang_html_mang_ten_onnx_bi_bat(snapshot, ten):
    """🔴 Đây là ca 07/08/2026: proxy trả 200 + HTML, `isfile` vẫn True."""
    (snapshot / ten).write_bytes(
        b"<!DOCTYPE html><html><body>403 Forbidden</body></html>")
    loi = kiem_model.kiem_thu_muc(str(snapshot))
    assert any(ten in x for x in loi), loi


def test_trang_html_mang_ten_safetensors_bi_bat(snapshot):
    (snapshot / "update" / "model.safetensors").write_bytes(
        b"<!DOCTYPE html><html><body>error</body></html>")
    loi = kiem_model.kiem_thu_muc(str(snapshot))
    assert any("model.safetensors" in x for x in loi), loi


def test_config_json_la_html_bi_bat(snapshot):
    """`config.json` nhỏ nên không có sàn kích thước — `json.load` là đủ."""
    (snapshot / "config.json").write_text("<html>oops</html>", encoding="utf-8")
    loi = kiem_model.kiem_thu_muc(str(snapshot))
    assert any("config.json" in x for x in loi), loi


# ── 3. blob bị cắt cụt (máy tắt / AV giữ tệp / đĩa đầy) ──────────────────────

def test_safetensors_bi_cat_cut_bi_bat(snapshot):
    """Phần đầu khai dài hơn phần thân còn lại ⇒ tệp không trọn vẹn."""
    d = snapshot / "update" / "model.safetensors"
    with open(d, "wb") as f:
        f.write(struct.pack("<Q", 50_000_000))     # khai 50 MB phần đầu
        f.write(b"{" + b"\0" * 1_200_000)          # nhưng chỉ có ~1,2 MB
    loi = kiem_model.kiem_thu_muc(str(d.parent.parent))
    assert any("cat cut" in x or "phan dau" in x for x in loi), loi


def test_thieu_tep_bi_bat(snapshot):
    (snapshot / "denoiser.onnx").unlink()
    assert any("thieu denoiser.onnx" in x
               for x in kiem_model.kiem_thu_muc(str(snapshot)))


def test_thu_muc_khong_ton_tai_bi_bat(tmp_path):
    assert kiem_model.kiem_thu_muc(str(tmp_path / "khong-co")) != []


# ── 4. 🔴 CHỖ DỄ SAI NHẤT: safetensors THẬT SỰ có `{`, chỉ là ở offset 8 ─────

def test_safetensors_co_dau_JSON_o_offset_8_van_duoc_coi_la_LANH(snapshot):
    """⛔ HỒI QUY CHỜ SẴN.

    Nếu ai đó "đơn giản hoá" `_kiem_safetensors` thành cùng một luật với ONNX
    (*"byte đầu là `{` thì hỏng"*), phép kiểm ấy sẽ **đúng gần hết thời gian**:
    byte 0 là byte thấp của độ dài phần đầu, và nó chỉ tình cờ bằng `0x7B`
    (`{`) khi phần đầu dài đúng 123 byte.

    Tệp dưới đây dựng ĐÚNG ca tình cờ ấy. Một luật đi mượn từ ONNX sẽ báo oan
    ở đây — giữa đêm, một lần, không tái hiện được.
    """
    d = snapshot / "update" / "model.safetensors"
    # Phần đầu dài đúng 123 byte -> struct.pack cho byte 0 = 0x7B = '{'
    dem = 123 - len('{"__metadata__": {"format": "pt"}}')
    dau = ('{"__metadata__": {"format": "pt"' + '_' * max(0, dem - 2)
           + '"}}').encode()
    dau = dau[:123].ljust(123, b" ")
    assert struct.pack("<Q", len(dau))[0:1] == b"{", "ca tinh co chua dung"
    with open(d, "wb") as f:
        f.write(struct.pack("<Q", len(dau)))
        f.write(dau)
        f.write(b"\0" * 1_200_000)
    loi = [x for x in kiem_model.kiem_thu_muc(str(snapshot))
           if "safetensors" in x]
    assert loi == [], "safetensors hop le bi bao oan: %r" % loi


# ── 5. fail-open / fail-closed ───────────────────────────────────────────────

def test_khong_dinh_vi_duoc_thi_BO_QUA(monkeypatch):
    """Máy dev không có cache HF vẫn phải khởi động được."""
    monkeypatch.setattr(kiem_model, "duong_snapshot", lambda *a, **k: "")
    assert kiem_model.kiem() == ""


def test_khong_dinh_vi_duoc_ma_BAT_BUOC_thi_NEM(monkeypatch):
    """Trên máy chủ đã cài, "không có cache" LÀ một sự cố."""
    monkeypatch.setattr(kiem_model, "duong_snapshot", lambda *a, **k: "")
    with pytest.raises(kiem_model.ModelHong):
        kiem_model.kiem(bat_buoc=True)


def test_dinh_vi_duoc_ma_hong_thi_NEM_du_KHONG_bat_buoc(monkeypatch, snapshot):
    """⛔ `bat_buoc` chỉ đổi nhánh *không tìm thấy*. Tìm thấy mà hỏng thì luôn chặn."""
    (snapshot / "denoiser.onnx").write_bytes(b"<html>")
    monkeypatch.setattr(kiem_model, "duong_snapshot", lambda *a, **k: str(snapshot))
    with pytest.raises(kiem_model.ModelHong):
        kiem_model.kiem(bat_buoc=False)


def test_che_do_gia_tri_la_thi_ve_bat(monkeypatch):
    monkeypatch.setenv("LTT_VOICE_KIEM_MODEL", "hmm")
    assert kiem_model.che_do() == "bat"
    monkeypatch.setenv("LTT_VOICE_KIEM_MODEL", "TAT")
    assert kiem_model.che_do() == "tat"
    monkeypatch.delenv("LTT_VOICE_KIEM_MODEL", raising=False)
    assert kiem_model.che_do() == "bat"


# ── 6. hai bản sao phải khớp nhau ────────────────────────────────────────────

def test_repo_va_revision_khop_ban_cai():
    """🔴 `kiem_model` và `install-vieneu-sidecar.ps1` giữ HAI bản sao của cùng
    một sự thật. Lệch nhau thì phép kiểm đi tìm một model khác, **không thấy**,
    rồi **bỏ qua** — nó im lặng thôi làm việc thay vì báo động.
    """
    ps1 = (GOC / "deploy" / "windows" / "install-vieneu-sidecar.ps1").read_text(
        encoding="utf-8", errors="replace")
    assert kiem_model.REPO_MAC_DINH in ps1, "REPO_MAC_DINH khong co trong ban cai"
    assert kiem_model.REV_MAC_DINH in ps1, "REV_MAC_DINH khong co trong ban cai"


def test_danh_sach_tep_khop_lam_am_cache():
    """`KHUON` phải là tập con của thứ `lam_am_cache.MAU_GPU` thật sự tải về.

    ⛔ Kiểm một tệp mà bộ làm ấm **không tải** thì cổng sẽ chặn mọi lần khởi
       động trên một máy cài đúng — đúng kiểu rào cản sẽ bị gỡ sau một tuần.
    """
    from voice_sidecar import lam_am_cache
    mau = set(lam_am_cache.MAU_GPU)
    for tuong_doi, _ in kiem_model.KHUON:
        ok = (tuong_doi in mau
              or any(m.endswith("/*") and tuong_doi.startswith(m[:-1])
                     for m in mau))
        assert ok, f"{tuong_doi} khong nam trong MAU_GPU cua lam_am_cache"


def test_engine_thuc_su_goi_cong_nay():
    """Đọc AST, không import: `engine.py` sống trong venv cách ly có torch.

    ⭐ Cùng khuôn với `test_384::test_giai_giong_tra_canh_bao_lan` — một cổng
       chỉ tồn tại nếu có ai gọi nó, và "có ai gọi nó" là thứ đo được tĩnh.
    """
    cay = ast.parse((GOC / "voice_sidecar" / "engine.py").read_text(
        encoding="utf-8"))
    nap = next(n for n in ast.walk(cay)
               if isinstance(n, ast.FunctionDef) and n.name == "nap")
    goi = {ast.unparse(n.func) for n in ast.walk(nap) if isinstance(n, ast.Call)}
    assert any("kiem_model.kiem" in g for g in goi), \
        "engine.nap() khong goi kiem_model.kiem — cong nay dang khong duoc gan vao"
