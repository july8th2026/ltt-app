"""`thanh_phan.py` phải thấy cả test gọi app qua ĐƯỜNG DẪN HTTP, không chỉ qua `import`.

🔴 **VÌ SAO CHỐT (đo 27/09/2026).** Đồ thị import ⛔ không thấy
`client.post("/taovideo/prefill")` — đó là một **chuỗi**, không một cạnh import.
Đo hai tầng (đếm, rồi đối chiếu với chính `--test app:<X>`): **50 tệp test** gọi
một app mà ⛔ không nằm trong thành phần của app đó. Nặng nhất: `app:agent` liệt kê
**11** tệp trong khi **21** tệp khác gọi `/agent` — gần ba lần tập đã biết là vô hình.

⚠️ Vì trong phiên **chỉ** chạy test nhắm (hợp đồng §4; gate một lần ở cuối plan),
lỗ này nằm trong **lưới an toàn duy nhất** để gộp `main`. Ca thật đã xảy ra:
`tests/test_5152_taovideo_prefill_route_and_queue.py` khẳng định trần ảnh cũ
(`== 4`); khi trần lên 9 nó ĐỎ, nhưng `--test app:taovideo` ⛔ không liệt kê nó —
nó chỉ lộ vì một người đọc mã và báo trước.

⭐ **Cách vá KHÔNG đảo nguyên tắc "đọc bản khai, đừng đoán từ tên"** của công cụ:
`route_prefix` là một **bản khai** — chính `platform_core/registry.py` dùng nó để
gắn router của app. Đọc nó là cùng một hành vi với đọc `import`. Và nó **cần thiết**
vì nhiều app có prefix KHÁC slug (`auto_scan_video` -> `/auto-scan-video`).

Ba bài dưới đây đo ba thứ khác nhau, ⛔ không bài nào thay được bài khác.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOC / "tools"))
import thanh_phan as tp  # noqa: E402


def _cay_gia(goc: Path, than_test: str, *, prefix: str = "/thu-nghiem-abc") -> Path:
    """Dựng một kho tí hon: một app khai `prefix`, một tệp test với `than_test`."""
    (goc / "apps" / "appthu").mkdir(parents=True)
    (goc / "apps" / "appthu" / "manifest.py").write_text(
        "from platform_core.registry import AppManifest\n"
        f'MANIFEST = AppManifest(slug="appthu", route_prefix="{prefix}")\n',
        encoding="utf-8", newline="\n")
    (goc / "tests").mkdir(parents=True)
    (goc / "tests" / "test_9001_gia.py").write_text(than_test, encoding="utf-8",
                                                    newline="\n")
    return goc


def _test_cua(goc: Path) -> set[str]:
    return tp.test_cua_thanh_phan(root=goc).get("app:appthu", set())


# ── 1. Cơ chế: gọi qua đường dẫn thì PHẢI được thấy ──────────────────────────

def test_test_goi_qua_duong_dan_duoc_gan_vao_app(tmp_path):
    """Đây là ĐỐI CHỨNG TIÊM LỖI của bài số 3: một tệp gọi route mà ⛔ không
    `import` app. Trước bản vá, bài này ĐỎ — và đó chính là lỗ 50 tệp."""
    goc = _cay_gia(tmp_path, 'def test_x(client):\n'
                             '    client.post("/thu-nghiem-abc/queue", json={})\n')
    assert "tests/test_9001_gia.py" in _test_cua(goc)


def test_prefix_doc_tu_BAN_KHAI_chu_khong_tu_ten_thu_muc(tmp_path):
    """Thư mục tên `appthu` mà prefix khai là `/hoan-toan-khac` ⇒ phải theo BẢN KHAI.

    ⛔ Không có bài này thì một cài đặt "đoán từ tên thư mục" cũng xanh ở bài trên,
    và nó sẽ **bỏ sót** mọi app có prefix khác slug — đúng 6 app trong kho này.
    """
    goc = _cay_gia(tmp_path,
                   'def test_x(client):\n'
                   '    client.get("/hoan-toan-khac/trang")\n',
                   prefix="/hoan-toan-khac")
    assert "tests/test_9001_gia.py" in _test_cua(goc)


# ── 2. ⛔ KHÔNG được gán thừa theo hai cách cụ thể mà thiết kế đã lo ─────────

@pytest.mark.parametrize("than, vi_sao", [
    ('def test_x():\n    """Bai nay ke ve /thu-nghiem-abc/queue."""\n    pass\n',
     "docstring KE ve mot duong dan khong phai mot lan GOI no"),
    ('def test_x():\n    # /thu-nghiem-abc/queue\n    pass\n',
     "chu thich khong ton tai trong AST"),
    ('def test_x(client):\n    client.get("/thu-nghiem-abcxyz/khac")\n',
     "thieu ranh gioi doan thi /thu-nghiem-abc an ca /thu-nghiem-abcxyz"),
])
def test_khong_gan_khi_chi_NHAC_toi_hoac_khop_nham(tmp_path, than, vi_sao):
    goc = _cay_gia(tmp_path, than)
    assert "tests/test_9001_gia.py" not in _test_cua(goc), vi_sao


def test_prefix_dai_thang_prefix_ngan(tmp_path):
    """`/agent` ⛔ không được ăn `/agent-dong-co/...` — hai app THẬT trong kho này.

    Nếu vòng khớp ⛔ không sắp giảm theo độ dài, tệp bị gán cho app SAI, và app
    đúng vẫn ⛔ không thấy nó ⇒ hỏng theo cả hai chiều.
    """
    for ten, prefix in (("ngan", "/agent"), ("dai", "/agent-dong-co")):
        (tmp_path / "apps" / f"app{ten}").mkdir(parents=True)
        (tmp_path / "apps" / f"app{ten}" / "manifest.py").write_text(
            "from platform_core.registry import AppManifest\n"
            f'MANIFEST = AppManifest(slug="app{ten}", route_prefix="{prefix}")\n',
            encoding="utf-8", newline="\n")
    (tmp_path / "tests").mkdir(parents=True)
    (tmp_path / "tests" / "test_9002_gia.py").write_text(
        'def test_x(client):\n    client.get("/agent-dong-co/chay")\n',
        encoding="utf-8", newline="\n")
    ra = tp.test_cua_thanh_phan(root=tmp_path)
    assert "tests/test_9002_gia.py" in ra.get("app:appdai", set())
    assert "tests/test_9002_gia.py" not in ra.get("app:appngan", set())


# ── 3. Trên KHO THẬT: bất biến không còn tệp nào bị bỏ ──────────────────────

def test_kho_that_khong_con_tep_test_nao_bi_bo():
    """Mọi tệp test gọi `"/<prefix đã khai>/..."` đều nằm trong thành phần app đó.

    ⭐ Ba ĐỐI CHỨNG, thiếu cái nào thì "0 tệp bị bỏ" có thể chỉ là **tập rỗng**:
      a) tập prefix đã khai ⛔ không rỗng (đọc manifest hỏng ⇒ 0 oan);
      b) bản đồ test ⛔ không rỗng (đọc `tests/` hỏng ⇒ 0 oan);
      c) có ÍT NHẤT một tệp thật được gán **nhờ** cạnh đường dẫn chứ không nhờ
         import — nếu không, bài này xanh cả khi cạnh mới chưa hề chạy.
    """
    prefix = tp._route_prefix_da_khai(GOC)
    assert len(prefix) >= 20, f"chi doc duoc {len(prefix)} route_prefix"

    ban_do = tp.test_cua_thanh_phan(root=GOC)
    assert sum(len(v) for v in ban_do.values()) > 100, "ban do test rong bat thuong"

    thu_tu = sorted(prefix.items(), key=lambda kv: -len(kv[1]))
    nho_duong_dan = 0
    bi_bo: list[str] = []
    for tep in sorted((GOC / "tests").glob("test_*.py")):
        ten = f"tests/{tep.name}"
        if ten in tp.DUNG_CHUNG:
            continue
        goi = tp._app_go_qua_http(tep, thu_tu)
        imp = {m for m in tp._module_duoc_import(tep)}
        for app in goi:
            if ten not in ban_do.get(f"app:{app}", set()):
                bi_bo.append(f"{ten} -> app:{app}")
            elif not any(m == f"apps.{app}" or m.startswith(f"apps.{app}.")
                         for m in imp):
                nho_duong_dan += 1

    assert not bi_bo, f"{len(bi_bo)} cap bi bo: {bi_bo[:10]}"
    assert nho_duong_dan >= 10, (
        f"chi {nho_duong_dan} cap duoc gan NHO canh duong dan — nghi canh moi "
        f"khong he chay, va '0 tep bi bo' la mot tap rong")
