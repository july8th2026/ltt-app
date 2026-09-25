"""Lớp THỨ HAI cho `core.code` — `isolated-vm` bên trong vỏ đã có (P-D mục 2).

⛔ **KHÔNG phải phép nghiệm thu ranh giới.** Ranh giới là AppContainer
   (`test_4231_wf_code_dien_tap_thoat_vo.py`). Tệp này chỉ đo hình dạng của
   *lớp siết thêm*: `require` không tồn tại trong isolate, hạn thực thi ĐỒNG
   BỘ (mili-giây, đo bởi V8, nhanh hơn hẳn hạn giờ TRÔI của `vo_boc.chay`),
   trần bộ nhớ V8 riêng — và một lỗi đã đo thật, không phải suy đoán: gọi
   `isolate.dispose()` một lần nữa sau khi V8 đã tự huỷ vì chạm trần bộ nhớ.

## Nguồn PORT

MIT, `activepieces/activepieces`
`packages/server/engine/src/lib/core/code/v8-isolate-code-sandbox.ts` (⛔
ngoài `packages/ee/`). Sao lại đúng hình dạng cốt lõi: `Isolate({memoryLimit})`
+ `createContext` + `ExternalCopy` cho input + `compileScript` +
`script.run({timeout, reference, promise})` + bọc CJS KHÔNG định nghĩa
`require`. Bản port: `connector_runner/src/code_sandbox.js`.

## ⭐ Một điểm sửa so với bản gốc — đo được, không phải sở thích

Bản gốc gọi `isolate.dispose()` không điều kiện trong `finally`. Đo 25/09
trên một spike đứng riêng (`memoryLimit=32`, vòng lặp cấp phát vô hạn):
`script.run()` ném đúng như kỳ vọng ("Isolate was disposed during execution
due to memory limit" — V8 tự huỷ isolate khi chạm trần), nhưng gọi
`isolate.dispose()` LẦN NỮA trong `finally` ném "Isolate is already
disposed" — MỘT LỖI KHÔNG BẮT ĐƯỢC bên trong `finally`, tức nó thoát khỏi
`try/catch` của `chayCode` và sẽ làm sập tiến trình runner thay vì trả về
một `{ok:false}` sạch. Cùng kịch bản, ít nhất một lần đo còn thấy tiến trình
Node **segfault** khi dọn dẹp (không tái hiện được ổn định — ghi ra để biết,
⛔ không assert vào đó). Vá: kiểm `isolate.isDisposed` trước khi gọi
`dispose()` (`code_sandbox.js::_huyAnToan`).
"""
from __future__ import annotations

import sys

import pytest

CAN_WINDOWS = pytest.mark.skipif(
    sys.platform != "win32", reason="AppContainer chi co tren Windows")


# ── Đúng — không cần vỏ AppContainer để đo hình dạng của isolated-vm ───────
#
# ⭐ Các phép dưới đây gọi thẳng `code_sandbox.chayCode` (module Node), KHÔNG
#    qua `vo_boc.chay`/AppContainer: câu hỏi ở đây là "isolated-vm tự nó làm
#    được gì", tách khỏi câu hỏi "AppContainer chặn được gì" — hai câu khác
#    nhau, xem `test_4231`. Vì không cần vỏ, các phép này chạy được cả trên
#    máy không phải Windows/không có quyền quản trị.

def _chay_js(ma_js: str, ok_khi_timeout=False) -> tuple:
    """Chạy MỘT đoạn Node trực tiếp (không qua vỏ) gọi `code_sandbox.js`.

    Trả `(stdout, returncode)`. Dùng để đo cấp module — không phải cấp tiến
    trình AppContainer.
    """
    import pathlib
    import subprocess

    goc = pathlib.Path(__file__).resolve().parents[1] / "connector_runner"
    r = subprocess.run(["node", "-e", ma_js], cwd=str(goc),
                       capture_output=True, text=True, timeout=30)
    return r.stdout + r.stderr, r.returncode


def test_require_KHONG_ton_tai_trong_isolate():
    """🔴 Toàn bộ giá trị của lớp này: không có `require` ⇒ không `fs`, không
    `child_process`, không `net` — code không có CÁCH NÀO chạm Node builtin
    từ bên trong isolate, không phải vì bị chặn bằng một danh sách đen."""
    ra, rc = _chay_js(
        "const {chayCode}=require('./src/code_sandbox');"
        "chayCode({nguon:'module.exports.code=function(inputs){"
        "return typeof require;};'}).then(r=>console.log('KET_QUA',r));")
    assert rc == 0, ra
    assert "KET_QUA undefined" in ra, ra


def test_ket_qua_dung_va_ExternalCopy_giu_hinh_dang():
    ra, rc = _chay_js(
        "const {chayCode}=require('./src/code_sandbox');"
        "chayCode({nguon:'module.exports.code=function(inputs){"
        "return {tong: inputs.a+inputs.b, ten: inputs.ten};};',"
        "inputs:{a:3,b:4,ten:'vi du'}})"
        ".then(r=>console.log('KET_QUA',JSON.stringify(r)));")
    assert rc == 0, ra
    assert '{"tong":7,"ten":"vi du"}' in ra, ra


def test_han_thuc_thi_DONG_BO_cat_vong_lap_vo_han_nhanh():
    """`timeout` của `script.run` phải cắt trong VÀI GIÂY, không phải đợi hạn
    giờ TRÔI (hàng chục giây) của tiến trình ngoài — đó là lý do isolated-vm
    đáng giá cho code node, không chỉ AppContainer."""
    import time
    t0 = time.monotonic()
    ra, rc = _chay_js(
        "const {chayCode}=require('./src/code_sandbox');"
        "chayCode({nguon:'module.exports.code=function(inputs){"
        "while(true){}};', han_ms:1200})"
        ".catch(e=>console.log('LOI',e.message));")
    dt = time.monotonic() - t0
    assert "Script execution timed out" in ra, ra
    assert dt < 8, f"cat qua cham: {dt}s (isolate timeout=1.2s)"


def test_TIEM_LOI_dispose_khong_dieu_kien_NEM_khi_da_tu_huy():
    """Phép TIÊM LỖI cho ca "tràn bộ nhớ": tái hiện ĐÚNG mã lỗi gốc (dispose
    không điều kiện trong `finally`, KHÔNG dùng `code_sandbox.js`) và chứng
    minh nó **ném một lỗi không bắt được bên trong `finally`** — đây là thứ
    `_huyAnToan`/`isolate.isDisposed` phải chặn. Không có phép này,
    `test_han_bo_nho...` phía dưới có thể xanh dù đã gỡ mất chỗ vá.
    """
    ra, rc = _chay_js(
        "const ivm=require('isolated-vm');"
        "(async()=>{"
        "const iso=new ivm.Isolate({memoryLimit:32});"
        "try{"
        "const ctx=await iso.createContext();"
        "const s=await iso.compileScript("
        "'let a=[];while(true){a.push(new Array(1e6).fill(0));}');"
        "await s.run(ctx,{timeout:6000});"
        "}finally{"
        "iso.dispose();"  # <- LOI GOC: khong kiem isDisposed
        "}"
        "})().catch(e=>{console.log('NEM',e.message);process.exitCode=1;});")
    assert "NEM Isolate is already disposed" in ra, (
        f"khong tai hien duoc loi goc — phep TIEM LOI nay da mat gia tri: {ra!r}")
    assert rc != 0


@pytest.mark.parametrize("lan", range(3))
def test_han_bo_nho_isolate_KHONG_nem_loi_khong_bat_duoc(lan):
    """Bản THẬT (`code_sandbox.js`, có `_huyAnToan`) không được lặp lại lỗi
    trên — chạy 3 lần vì chỗ crash gốc từng thấy không ổn định (phụ thuộc
    thời điểm GC/bộ nhớ)."""
    ra, rc = _chay_js(
        "const {chayCode}=require('./src/code_sandbox');"
        "chayCode({nguon:'module.exports.code=function(inputs){"
        "let a=[];while(true){a.push(new Array(1e6).fill(0));}};',"
        "bo_nho_mb:32, han_ms:6000})"
        ".then(()=>console.log('KHONG_NEM (sai — phai cham tran)'))"
        ".catch(e=>console.log('LOI_SACH', e.message));")
    assert "Isolate is already disposed" not in ra, (
        f"⛔ VAN NEM LOI KHONG BAT DUOC — cho sua da mat: {ra!r}")
    assert "LOI_SACH" in ra, ra
    assert "memory limit" in ra, ra
    assert rc == 0, f"tien trinh Node thoat bat thuong (rc={rc}): {ra!r}"


# ── Đầu cuối qua `platform_core.workflow.code_sandbox` (cần vỏ thật) ───────

@pytest.fixture(scope="module")
def vo():
    from platform_core.workflow import code_sandbox
    try:
        code_sandbox.chuan_bi_vo_code()
    except Exception as loi:  # noqa: BLE001
        pytest.skip(f"khong dung duoc vo code: {loi}")
    yield code_sandbox.TEN_VO_CODE
    try:
        code_sandbox.go_vo_code()
    except Exception:  # noqa: BLE001
        pass


@CAN_WINDOWS
def test_dau_cuoi_qua_vo_ket_qua_dung(vo):
    from platform_core.workflow import code_sandbox
    kq = code_sandbox.chay(
        "module.exports.code = function(inputs){ return inputs.a * inputs.b; };",
        {"a": 6, "b": 7})
    assert kq.ok, (kq.ma_loi, kq.thong_diep)
    assert kq.output == 42


@CAN_WINDOWS
def test_dau_cuoi_qua_vo_vong_lap_vo_han_bi_cat_BOI_ISOLATE_khong_phai_HAN_NGOAI(vo):
    """⭐ Phép phân biệt: nếu bị cắt bởi `han_ms` NGOÀI (het_gio ở tầng
    `vo_boc`), độ trễ sẽ ăn theo `han_ms` mặc định của `connector` (hàng chục
    giây). Ở đây phải nhanh — chứng minh chính `isolate` đã cắt trước."""
    import time
    from platform_core.workflow import code_sandbox
    t0 = time.monotonic()
    kq = code_sandbox.chay(
        "module.exports.code = function(inputs){ while(true){} };", {},
        han_isolate_ms=1000)
    dt = time.monotonic() - t0
    assert kq.ok is False
    assert kq.ma_loi == "het_gio"
    assert dt < 10, f"cat qua cham ({dt}s) — nghi bi han NGOAI cat, khong phai isolate"


@CAN_WINDOWS
def test_dau_cuoi_qua_vo_tran_bo_nho_khong_lam_sap_runner(vo):
    """Đối chứng cho cả hai lớp cùng lúc: qua TRỌN đường ống (Python ⇄
    AppContainer ⇄ isolated-vm), tràn bộ nhớ vẫn phải trả về một `KetQuaCode`
    sạch — không ném `LoiCodeSandbox`, không hết giờ NGOÀI (nếu hết giờ NGOÀI
    thì `_huyAnToan` không có cơ hội chạy, và phép này không đo được gì)."""
    from platform_core.workflow import code_sandbox
    kq = code_sandbox.chay(
        "module.exports.code = function(inputs){ let a=[]; "
        "while(true){a.push(new Array(1e6).fill(0));} };", {},
        bo_nho_isolate_mb=32, han_isolate_ms=6000)
    assert kq.ok is False
    assert kq.ma_loi == "het_gio", (
        "khong phai isolate cat -> phep nay khong doi chung duoc gi ve dispose: "
        f"{kq.ma_loi} {kq.thong_diep}")
    assert "memory limit" in kq.thong_diep
