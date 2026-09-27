# UI-0 — Bốn lỗi P0 cơ khí: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: dùng `superpowers:subagent-driven-development`
> (khuyến nghị) hoặc `superpowers:executing-plans` để thi hành từng task.
> Các bước dùng checkbox (`- [ ]`) để theo dõi.

**Goal:** Làm cho một workflow dựng bằng chuột trên Canvas **biên dịch và chạy được**
— hôm nay 55/67 loại bước không biên dịch được và không kéo nổi một sợi dây.

**Architecture:** Ba trong bốn lỗi sửa **ở máy chủ**, không ở dữ liệu và không ở
trình duyệt. Cổng biên dịch đã có sẵn đúng chuỗi tra và đúng luật cần dùng; nó chỉ
chưa được gọi cho hình dạng node mà palette sinh ra. ⇒ Không có bước di trú dữ liệu
nào, và mọi bản nháp đang nằm trên production tự chạy được ngay sau khi deploy.

**Tech Stack:** Python 3.13 · FastAPI · SQLAlchemy · pytest · React 19 ·
`@xyflow/react` 12.11.2 · vitest 4 · Playwright (`playwright-cli`).

**Spec:** `docs/architecture/agent_ui_v2/01_CURRENT_UI_AUDIT.md` §2 (bốn lỗi P0),
và `docs/superpowers/plans/2026-09-27-agent-ui-v2-TONG.md` §1.5 (vì sao sửa ở cổng
biên dịch thay vì di trú dữ liệu).

## Global Constraints

- ⛔ **KHÔNG chạy gate trong pha này** — không L1, không L2, không L3. Gate chỉ chạy
  MỘT lần ở CUỐI PLAN (hết **mọi** pha của `…-TONG.md`). Xong UI-0 **không** phải
  cuối plan.
- Test nhắm: chạy **đúng các tệp test liệt kê trong task**, ⛔ **không** chạy
  `python tools\thanh_phan.py --test core:wf_soan` rồi pytest cả 86 tệp —
  `conftest` tự xin khoá `cpu_nhieu` khi ≥ 20 tệp và sẽ **tự khoá chính mình**.
- Gộp `main`: test nhắm xanh là đủ. Gộp xong chạy `pre-commit run --all-files`.
- ⛔ Không sửa `frontend/agent-canvas/src/CanvasShell.tsx` quá phạm vi Task 5 —
  UI-3 là chủ sở hữu tệp đó.
- Đổi JS/CSS tĩnh ⇒ phải bump `server/templating.py:ASSET_VER`.
- Frontend giữ schema-driven: ⛔ không bảng tra tên app/tool/nhãn trong `src/`.
- Ghi cấu hình KHÔNG BOM · `.ps1` thuần ASCII · ⛔ không Python inline qua PowerShell.

---

## Task 0: Mở làn và ghi sổ

**Files:**
- Create: `docs/architecture/agent_ui_v2/00_SO_TIEN_DO.md`

- [ ] **Bước 1: Tạo cây riêng cho làn**

```bash
python tools/cay_rieng.py tao ui0
```

Lệnh in ra hai thứ phải chép lại ngay:
- đường dẫn cây mới (nhánh `phien/ui0`),
- **`DAI SO TEST cua cay nay: <đầu>-<đầu+99>`**.

🔴 Mọi tệp test mới trong pha này phải mang số **trong dải đó**. Dải được cấp lúc
tạo cây nên hai làn không thể chọn trùng.

✅ **Đã cấp cho làn UI-0 (27/09/2026): dải `5600-5699`.** Quét 193 cây trên đĩa, số
cao nhất đang dùng là `5562`. Hai tệp test của pha này:

```
tests/test_5600_wf_node_palette_bien_dich.py    (Task 1)
tests/test_5601_wf_canh_dieu_khien_suy_ra.py    (Task 2)
```

- [ ] **Bước 2: Tạo sổ tiến độ theo khuôn ở `…-TONG.md` §4.2**

Chép nguyên khuôn, rồi điền hàng UI-0: trạng thái `ĐANG LÀM`, nhánh `phien/ui0`,
tệp sở hữu = `platform_core/workflow/bien_dich.py`, `frontend/agent-canvas/src/workflowApi.ts`,
`frontend/agent-canvas/src/canvas.css`, `frontend/agent-canvas/src/nodes/NodeKhung.tsx`,
`frontend/agent-canvas/src/editorState.ts`.

Ghi dải số test vào phần *Nhật ký*.

- [ ] **Bước 3: Commit**

```bash
git add docs/architecture/agent_ui_v2/00_SO_TIEN_DO.md
git commit -m "docs(agent-ui): mo lan UI-0, so tien do + dai so test"
```

---

## Task 1: Cổng biên dịch nhận node hình dạng palette

**Files:**
- Modify: `platform_core/workflow/bien_dich.py` (hàm `_node`, quanh dòng 597–629)
- Test: `tests/test_5600_wf_node_palette_bien_dich.py`

**Interfaces:**
- Consumes: `_node_loi(n: dict, nid: str, loai: str) -> dict` (đã có, dòng ~572)
- Produces: không đổi chữ ký nào. `_node()` giữ nguyên chữ ký và giữ nguyên mã lỗi
  `node_khong_ton_tai` cho trường hợp loại thật sự không tồn tại.

**Bối cảnh — đọc trước khi sửa.** `frontend/agent-canvas/src/editorState.ts::nextNode()`
dựng MỌI node với `type: 'tool'` và đặt loại thật vào `data.tool`. `_node()` phân
nhánh theo `n["type"]` ở mức trên cùng, nên node palette rơi vào nhánh `loai == "tool"`
và tra `cc` — **sổ công cụ APP**, không có `core.*`/`piece.*`.

⭐ `tests/test_4250_wf_v3_soan_data_tool_shape.py` đã **ghi ra bằng chữ** chính xác
cơ chế hỏng này (*"Đổi `type` sang `'tool'` cho node lõi sẽ … tra `cong_cu.tat_ca()`
… → sinh lỗi `node_khong_ton_tai`"*) — nhưng chỉ soi đường Agent Designer, không ai
nối nó sang đường palette. Đây là một phép kiểm XANH đã tái hiện sẵn lỗi.

- [ ] **Bước 1: Viết phép kiểm ĐỎ**

Tạo `tests/test_5600_wf_node_palette_bien_dich.py`:

```python
"""UI-0 Task 1 — node do PALETTE Canvas tao phai bien dich duoc.

`editorState.nextNode()` dung MOI node voi `type:'tool'` va dat loai THAT vao
`data.tool`. `bien_dich._node()` phan nhanh theo `type` muc tren cung, nen truoc
ban va nay moi node `core.*`/`piece.*` keo tu palette deu chet voi
`node_khong_ton_tai` — do duoc tren trinh duyet that 27/09/2026
(`docs/architecture/agent_ui_v2/01_CURRENT_UI_AUDIT.md` §2.1).

⛔ KHONG doi `nextNode()` ghi `type` that o task nay: lam vay se doi hinh dang
   MOI ban nhap dang nam tren production va doi mot buoc di tru. Cong bien dich
   nhan CA HAI hinh dang thi khong ban nhap nao phai doi.
"""
from __future__ import annotations

import pytest

from platform_core.workflow import bien_dich


def _tai_lieu(tool: str, params: dict | None = None) -> dict:
    """Mot tai lieu v3 MOT trang MOT node, dung hinh dang `nextNode()` sinh."""
    return {"version": 3, "goal": "", "active_page_id": "p1",
            "pages": [{"id": "p1", "name": "Page 1",
                       "nodes": [{"id": "n1", "type": "tool",
                                  "position": {"x": 0, "y": 0},
                                  "data": {"tool": tool,
                                           "params": params or {}}}],
                       "edges": []}]}


@pytest.mark.parametrize("tool,mong_doi", [
    ("core.set", "core.set"),
    ("core.if", "core.if"),
    ("core.stop", "core.stop"),
])
def test_node_loi_tu_palette_bien_dich_duoc(tool, mong_doi):
    ct = bien_dich.cau_truc(_tai_lieu(tool, _tham_so_toi_thieu(tool)))
    assert [n["type"] for n in ct.nodes] == [mong_doi]


def test_node_app_tu_palette_van_bien_dich_duoc():
    """Duong `app.*` KHONG duoc hong khi them nhanh lui."""
    ct = bien_dich.cau_truc(
        _tai_lieu("image.generate", {"prompt": "mot con meo"}))
    assert ct.nodes[0]["type"] == "app.image.generate"


def test_loai_that_su_khong_ton_tai_van_bao_dung_ma_loi():
    with pytest.raises(bien_dich.LoiBienDich) as e:
        bien_dich.cau_truc(_tai_lieu("khong.ton.tai.that"))
    assert e.value.ma == "node_khong_ton_tai"


def _tham_so_toi_thieu(tool: str) -> dict:
    """Tham so BAT BUOC toi thieu cua tung node loi, lay tu `nut_loi/`."""
    return {"core.if": {"dieu_kien": "1 == 1"},
            "core.set": {"bien": {}},
            "core.stop": {}}.get(tool, {})
```

⚠️ `_tham_so_toi_thieu` phải khớp `required` thật của từng node. Xác nhận bằng:

```bash
python -c "from platform_core.workflow import nut_loi; [print(t, nd.tham_so.get('required')) for t, nd in sorted(nut_loi.tat_ca().items())]"
```

Nếu lệch, sửa `_tham_so_toi_thieu` cho khớp — ⛔ không sửa `nut_loi`.

- [ ] **Bước 2: Chạy để xác nhận ĐỎ**

```bash
python -m pytest tests/test_5600_wf_node_palette_bien_dich.py -q
```

Kỳ vọng: **FAIL**, ba ca `core.*` ném `LoiBienDich(ma="node_khong_ton_tai")`.
Hai ca còn lại (`app.*` và loại không tồn tại) đã XANH từ trước — đó là chủ ý,
chúng là lưới chống hồi quy.

- [ ] **Bước 3: Sửa `_node()`**

Trong `platform_core/workflow/bien_dich.py`, tìm:

```python
    tool = cc.get(ten)
    if tool is None:
        raise LoiBienDich("node_khong_ton_tai", ten, nid)
```

Thay bằng:

```python
    tool = cc.get(ten)
    if tool is None:
        # ⭐ Node do PALETTE Canvas tao: `type` la hang so `'tool'`, con loai
        #    THAT nam o `data.tool` (`editorState.nextNode()`), va
        #    `params`/`settings` nam duoi `data`. `_node_loi` DA co dung chuoi
        #    tra ta can (`nut_loi.tat_ca()` roi `nut.dinh_nghia_piece`), nen
        #    chi can nang `data.*` len muc tren cho khop hop dong cua no.
        #
        # ⛔ KHONG cai dat lai phep tra o day: hai ban cai dat song song thi
        #    lech, va lech im lang (cung bai hoc voi luat noi day).
        #
        # 🔴 Nhanh nay la thu duy nhat cho 55/67 loai buoc keo tu palette bien
        #    dich duoc. Xoa no la lam chet lai ca palette —
        #    `tests/test_5600_wf_node_palette_bien_dich.py` giu cho nay.
        if loai == "tool" and ten:
            return _node_loi({**n, "type": ten, "params": params,
                              "settings": settings}, nid, ten)
        raise LoiBienDich("node_khong_ton_tai", ten, nid)
```

- [ ] **Bước 4: Chạy để xác nhận XANH**

```bash
python -m pytest tests/test_5600_wf_node_palette_bien_dich.py -q
```

Kỳ vọng: **PASS**, 5 passed.

- [ ] **Bước 5: Chạy lưới hồi quy quanh cổng biên dịch**

```bash
python -m pytest tests/test_1714_wf_bien_dich.py tests/test_4250_wf_v3_soan_data_tool_shape.py tests/test_1783_wf_nut_dieu_huong.py -q
```

Kỳ vọng: **PASS**. Ba tệp này ghim hình dạng node của Agent Designer và của node
điều hướng; nếu một trong ba đỏ thì bản vá đã đụng vào hợp đồng chúng giữ — sửa
tại chỗ rồi chạy lại **đúng** lệnh này.

- [ ] **Bước 6: Commit**

```bash
git add platform_core/workflow/bien_dich.py tests/test_5600_wf_node_palette_bien_dich.py
git commit -m "fix(wf): cong bien dich nhan node hinh dang palette (type:'tool' + data.tool)"
```

---

## Task 2: Nhánh điều khiển — suy ra `kind`/`condition` ở máy chủ

**Files:**
- Modify: `platform_core/workflow/bien_dich.py` (hàm `cau_truc`, quanh dòng 709–726)
- Test: `tests/test_5601_wf_canh_dieu_khien_suy_ra.py`

**Interfaces:**
- Consumes: `nut.tat_ca(cong_cu=cc)` → `dict[str, NodeDefinition]`;
  `NodeDefinition.cong_ra` → `tuple[tuple[str, he_kieu.Cong], ...]`, `Cong.type: str`
- Produces: `_suy_kind_canh(loai_nguon: str, cong: str, so: dict) -> tuple[str, str]`
  trả `(kind, condition)`. Task 6 dùng lại tên này.

**Bối cảnh.** `cau_truc()` đọc `c.get("kind")` và `c.get("condition")` từ tài liệu,
nhưng `workflowApi.edgeToV3()` **đóng cứng `kind:'DATA'` và không gửi `condition`**.
Động cơ (`dong_co.py:150`) xử: `if not dk: return True` ⇒ **mọi nhánh của `core.if`
đều kích hoạt**. Người dùng vẽ một rẽ nhánh và nhận một phân đôi — trên tiền thật.

Spec §5.4: *"Cạnh CONTROL mang `condition = <tên nhánh>`"*. Với `core.if`, **tên nhánh
chính là tên cổng ra** (`true`/`false`) ⇒ suy ra được từ kiểu cổng, không cần người
dùng khai thêm gì và không cần di trú.

🔴 **`core.switch` KHÔNG suy ra được — và suy bừa sẽ làm HỎNG NẶNG HƠN.**
Đo bằng `nut_loi.tat_ca()` ngày 27/09:

```
core.if      cong_ra = [('true','control'), ('false','control')]   ← 2 cong control
core.switch  cong_ra = [('nhanh','control')]                        ← 1 cong, TEN CHUNG
```

Tên các nhánh của `core.switch` nằm trong **tham số** `nhanh: array`, không phải tên
cổng. Nếu suy `condition='nhanh'` thì động cơ so `_nhanh_da_chon(...) == "nhanh"` —
mà hàm đó trả **giá trị nhánh thật** (`"a"`, `"b"`…) ⇒ **không nhánh nào khớp ⇒ MỌI
nhánh chết ⇒ mọi node sau switch SKIPPED.** Hôm nay switch chạy cả các nhánh (sai
nhưng chạy); sau một bản suy bừa nó sẽ **không chạy gì** — hồi quy tệ hơn hiện trạng.

⇒ **Luật đúng: chỉ suy khi node nguồn có ≥ 2 cổng ra kiểu `control`.** Khi đó tên
cổng mới thật sự định danh một nhánh. Node một-cổng-control (`core.switch`) **giữ
nguyên** như hôm nay, và phải có một phép kiểm ghim rằng ta **không** đụng vào nó.

⚠️ **Khoảng trống còn lại, ghi ra chứ không giấu:** `core.switch` vẫn chạy mọi nhánh.
Sửa nó cần một cửa giao diện đặt tên nhánh lên cạnh — thuộc **UI-4**, không thuộc pha
này. Ghi vào sổ tiến độ ở Bước 6.

🔴 **Đây là một THAY ĐỔI HÀNH VI** (sổ rủi ro R3): workflow hôm nay chạy cả hai
nhánh, sau bản vá sẽ chạy một nhánh. Đó là hành vi **đúng**, nhưng phải báo chủ dự
án trước khi deploy — ghi vào sổ tiến độ ở Bước 6.

- [ ] **Bước 1: Viết phép kiểm ĐỎ**

Tạo `tests/test_5601_wf_canh_dieu_khien_suy_ra.py`:

```python
"""UI-0 Task 2 — canh roi mot cong CONTROL phai mang kind=CONTROL + condition.

`workflowApi.edgeToV3()` dong cung `kind:'DATA'` va khong gui `condition`, nen
`dong_co._kich_hoat` thay `dk` rong va tra `True` cho MOI canh — hai nhanh cua
`core.if` deu chay. Do duoc tren trinh duyet 27/09/2026.

⭐ Suy ra o MAY CHU vi may chu SO HUU luat: no biet `core.if` khai hai cong ra
   kieu `control` ten `true`/`false`. Client suy lai la ban cai dat thu hai.
"""
from __future__ import annotations

from platform_core.workflow import bien_dich


def _tai_lieu_if() -> dict:
    """core.if --true--> core.set ; core.if --false--> core.stop."""
    return {"version": 3, "goal": "", "active_page_id": "p1",
            "pages": [{"id": "p1", "name": "Page 1", "nodes": [
                {"id": "n-if", "type": "tool", "position": {"x": 0, "y": 0},
                 "data": {"tool": "core.if", "params": {"dieu_kien": "1 == 1"}}},
                {"id": "n-set", "type": "tool", "position": {"x": 300, "y": 0},
                 "data": {"tool": "core.set", "params": {"bien": {}}}},
                {"id": "n-stop", "type": "tool", "position": {"x": 300, "y": 200},
                 "data": {"tool": "core.stop", "params": {}}},
            ], "edges": [
                {"id": "e1", "source_node": "n-if", "target_node": "n-set",
                 "source_port": "true", "target_port": "in", "kind": "DATA"},
                {"id": "e2", "source_node": "n-if", "target_node": "n-stop",
                 "source_port": "false", "target_port": "in", "kind": "DATA"},
            ]}]}


def test_canh_tu_cong_control_mang_kind_va_ten_nhanh():
    ct = bien_dich.cau_truc(_tai_lieu_if())
    theo_id = {e["id"]: e for e in ct.edges}
    assert theo_id["e1"]["kind"] == "CONTROL"
    assert theo_id["e1"]["condition"] == "true"
    assert theo_id["e2"]["kind"] == "CONTROL"
    assert theo_id["e2"]["condition"] == "false"


def test_canh_du_lieu_thuong_khong_bi_doi():
    """Canh roi mot cong DU LIEU phai giu DATA va condition rong."""
    doc = {"version": 3, "goal": "", "active_page_id": "p1",
           "pages": [{"id": "p1", "name": "Page 1", "nodes": [
               {"id": "a", "type": "tool", "position": {"x": 0, "y": 0},
                "data": {"tool": "image.generate", "params": {"prompt": "x"}}},
               {"id": "b", "type": "tool", "position": {"x": 300, "y": 0},
                "data": {"tool": "core.set", "params": {"bien": {}}}},
           ], "edges": [
               {"id": "e", "source_node": "a", "target_node": "b",
                "source_port": "image_keys", "target_port": "in", "kind": "DATA"},
           ]}]}
    ct = bien_dich.cau_truc(doc)
    assert ct.edges[0]["kind"] == "DATA"
    assert ct.edges[0]["condition"] == ""


def test_core_switch_KHONG_bi_suy_bua():
    """🔴 Hoi quy: `core.switch` co DUNG MOT cong control ten `nhanh`, con ten
    cac nhanh nam trong THAM SO. Suy `condition='nhanh'` se lam MOI nhanh cua
    switch chet (dong co so `_nhanh_da_chon(...) == "nhanh"`, khong bao gio
    khop). Canh cua switch phai di qua NGUYEN VEN.
    """
    doc = {"version": 3, "goal": "", "active_page_id": "p1",
           "pages": [{"id": "p1", "name": "Page 1", "nodes": [
               {"id": "n-sw", "type": "tool", "position": {"x": 0, "y": 0},
                "data": {"tool": "core.switch",
                         "params": {"bieu_thuc": "1", "nhanh": ["a", "b"]}}},
               {"id": "n-set", "type": "tool", "position": {"x": 300, "y": 0},
                "data": {"tool": "core.set", "params": {"bien": {}}}},
           ], "edges": [
               {"id": "e", "source_node": "n-sw", "target_node": "n-set",
                "source_port": "nhanh", "target_port": "in", "kind": "DATA"},
           ]}]}
    ct = bien_dich.cau_truc(doc)
    assert ct.edges[0]["condition"] == "", "da suy bua cho core.switch"


def test_tai_lieu_KHAI_TUONG_MINH_thi_giu_nguyen_khong_suy():
    """Tai lieu da khai `condition` thi may chu KHONG duoc ghi de."""
    doc = _tai_lieu_if()
    doc["pages"][0]["edges"][0]["kind"] = "ERROR"
    doc["pages"][0]["edges"][0]["condition"] = "tu_khai"
    ct = bien_dich.cau_truc(doc)
    theo_id = {e["id"]: e for e in ct.edges}
    assert theo_id["e1"]["kind"] == "ERROR"
    assert theo_id["e1"]["condition"] == "tu_khai"
```

- [ ] **Bước 2: Chạy để xác nhận ĐỎ**

```bash
python -m pytest tests/test_5601_wf_canh_dieu_khien_suy_ra.py -q
```

Kỳ vọng: **FAIL** ở `test_canh_tu_cong_control_mang_kind_va_ten_nhanh`
(`kind` là `"DATA"`, `condition` là `""`). Hai ca còn lại XANH sẵn.

- [ ] **Bước 3: Thêm hàm suy ra**

Trong `bien_dich.py`, đặt ngay **trước** `def cau_truc(`:

```python
def _suy_kind_canh(loai_nguon: str, cong: str, so: dict) -> tuple[str, str]:
    """`(kind, condition)` SUY RA cho mot canh tai lieu khong khai.

    ⭐ Spec §5.4: *"Canh CONTROL mang `condition = <ten nhanh>`"*. Voi `core.if`,
       ten nhanh CHINH LA ten cong ra (`true`/`false`), nen suy duoc.

    🔴 CHI suy khi node nguon co >= 2 cong ra kieu `control`. Do la phep thu
       duy nhat phan biet "ten cong LA ten nhanh" voi "ten cong chi la mot cai
       ong". `core.switch` co DUNG MOT cong control ten `nhanh`, con ten cac
       nhanh nam trong THAM SO `nhanh: array` — suy `condition='nhanh'` cho no
       thi dong co se so `_nhanh_da_chon(...) == "nhanh"`, khong bao gio khop,
       va MOI nhanh cua switch chet. Hom nay switch chay ca cac nhanh (sai
       nhung chay); mot ban suy bua bien no thanh khong chay gi — te hon.

    ⛔ Khong suy theo TEN node (`loai_nguon == "core.if"`): mot node moi co hai
       cong control se im lang khong duoc suy. Hoi CAU TRUC CONG — do la thu
       `he_kieu` so huu, giong het luat noi day.
    """
    nd = so.get(loai_nguon)
    if nd is None:
        return ("DATA", "")
    cong_control = [ten for ten, c in nd.cong_ra if c.type == "control"]
    if len(cong_control) < 2 or cong not in cong_control:
        return ("DATA", "")
    return ("CONTROL", cong)
```

- [ ] **Bước 4: Gọi nó trong `cau_truc()`**

Tìm khối:

```python
        for c in trang.get("edges") or []:
            e = _canh_v3(c)
            e["kind"] = str(c.get("kind") or "DATA")
            e["condition"] = str(c.get("condition") or "")
            edges.append((pid, e))  # type: ignore[arg-type]
```

Thay bằng:

```python
        for c in trang.get("edges") or []:
            e = _canh_v3(c)
            # 🔴 Tai lieu KHAI TUONG MINH thi thang; chi SUY khi no im lang.
            #    `edgeToV3` hom nay dong cung `kind:'DATA'`, nen "im lang" o
            #    day nghia la "khai DATA ma khong khai condition".
            khai_kind = str(c.get("kind") or "")
            khai_dk = str(c.get("condition") or "")
            if khai_dk or (khai_kind and khai_kind != "DATA"):
                e["kind"] = khai_kind or "DATA"
                e["condition"] = khai_dk
            else:
                nguon = _loai_node_theo_id.get(str(c.get("source_node") or ""), "")
                e["kind"], e["condition"] = _suy_kind_canh(
                    nguon, e["source_port"], _so_node)
            edges.append((pid, e))  # type: ignore[arg-type]
```

Và ngay **trước** vòng `for trang in document.get("pages") or []:`, thêm hai biến
tra cứu:

```python
    from platform_core.workflow import nut as _nut
    #: `type` THAT cua tung node, dung de hoi kieu cong khi suy `kind` canh.
    #: Dien dan trong chinh vong duyet node ben duoi.
    _loai_node_theo_id: dict[str, str] = {}
    #: So node hop ba nguon. Tra MOT lan cho ca tai lieu, khong tra moi canh.
    _so_node = _nut.tat_ca(cong_cu=cc)
```

Trong vòng duyệt node, ngay sau `nodes.append(nd)`, thêm:

```python
            _loai_node_theo_id[nd["id"]] = nd["type"]
```

⚠️ Thứ tự quan trọng: trong `cau_truc()`, vòng `for trang` duyệt **node trước, cạnh
sau trong cùng một trang**, nên một cạnh chỉ tra được node cùng trang. Đó đúng là
ràng buộc đã có (`canh_khac_trang`), nên không sinh ca mới.

- [ ] **Bước 5: Chạy để xác nhận XANH**

```bash
python -m pytest tests/test_5601_wf_canh_dieu_khien_suy_ra.py -q
python -m pytest tests/test_1714_wf_bien_dich.py tests/test_1719_wf_dong_co.py tests/test_1783_wf_nut_dieu_huong.py -q
```

Kỳ vọng: cả hai lệnh **PASS**.

- [ ] **Bước 6: Ghi cảnh báo đổi hành vi vào sổ**

Thêm vào phần *Nhật ký* của `00_SO_TIEN_DO.md`:

```markdown
- `<ngày giờ>` `UI-0` — 🔴 ĐỔI HÀNH VI (R3): canh roi cong CONTROL nay mang
  kind=CONTROL + condition=<ten cong>. Workflow dang chay hom nay chay CA HAI
  nhanh cua core.if; sau ban va se chay MOT nhanh. Dung, nhung phai bao chu du
  an TRUOC khi deploy.
```

- [ ] **Bước 7: Commit**

```bash
git add platform_core/workflow/bien_dich.py tests/test_5601_wf_canh_dieu_khien_suy_ra.py docs/architecture/agent_ui_v2/00_SO_TIEN_DO.md
git commit -m "fix(wf): suy kind=CONTROL + condition tu kieu cong ra (re nhanh chay dung mot nhanh)"
```

---

## Task 3: Nhánh LỖI — client gửi `kind:'ERROR'`

**Files:**
- Modify: `frontend/agent-canvas/src/workflowApi.ts` (dòng 142–180)
- Test: `frontend/agent-canvas/tests/workflowApi.test.ts` (thêm vào tệp đã có)

**Interfaces:**
- Consumes: `CanvasEdge.data.condition?: 'success' | 'error'` (đã có)
- Produces: `CanvasEdgeKind = 'DATA' | 'CONTROL' | 'ERROR'`;
  `CanvasEdgeV3.condition?: string`

**Bối cảnh.** Task 2 lo nhánh `true`/`false` (suy được từ kiểu cổng). Nhánh **LỖI**
thì **không** suy được — nó là ý định của người dùng, đặt bằng nút *"Nhánh: Lỗi /
Thành công"*. Nút đó ghi `edge.data.condition` mà `edgeToV3` không gửi ⇒ nút đó hôm
nay đổi một nhãn trên màn hình và **không đổi gì khác**.

- [ ] **Bước 1: Viết phép kiểm ĐỎ**

Thêm vào cuối `frontend/agent-canvas/tests/workflowApi.test.ts`:

```ts
import { edgeToV3, edgeFromV3 } from '../src/workflowApi'

describe('edgeToV3 — nhanh loi', () => {
  it('canh danh dau LOI gui kind ERROR', () => {
    const ra = edgeToV3({ id: 'e1', source: 'a', target: 'b',
      sourceHandle: 'out', targetHandle: 'in',
      data: { condition: 'error' } })
    expect(ra.kind).toBe('ERROR')
  })

  it('canh thuong van la DATA', () => {
    const ra = edgeToV3({ id: 'e2', source: 'a', target: 'b',
      sourceHandle: 'out', targetHandle: 'in' })
    expect(ra.kind).toBe('DATA')
  })

  it('canh danh dau THANH CONG cung la DATA', () => {
    const ra = edgeToV3({ id: 'e3', source: 'a', target: 'b',
      sourceHandle: 'out', targetHandle: 'in',
      data: { condition: 'success' } })
    expect(ra.kind).toBe('DATA')
  })

  it('di ve khong mat nhan loi', () => {
    const goc = { id: 'e4', source: 'a', target: 'b',
      sourceHandle: 'out', targetHandle: 'in',
      data: { condition: 'error' as const } }
    expect(edgeFromV3(edgeToV3(goc)).data?.condition).toBe('error')
  })
})
```

- [ ] **Bước 2: Chạy để xác nhận ĐỎ**

```bash
cd frontend/agent-canvas && npm test -- workflowApi
```

Kỳ vọng: **FAIL** — ca 1 nhận `'DATA'`, ca 4 nhận `undefined`.

⚠️ `npm test` cần `node_modules`, **không có trong worktree mới**. Nếu thiếu:
`cd frontend/agent-canvas && npm ci` (lệnh nặng ⇒ đi qua `chay_nang.py`).

- [ ] **Bước 3: Sửa `workflowApi.ts`**

Đổi kiểu (dòng ~142):

```ts
export type CanvasEdgeKind = 'DATA' | 'CONTROL' | 'ERROR'
export type CanvasEdgeV3 = {
  id: string
  source_node: string
  target_node: string
  source_port: string
  target_port: string
  kind: CanvasEdgeKind
  /** Ten nhanh (§5.4). May chu SUY khi vang — xem `bien_dich._suy_kind_canh`. */
  condition?: string
}
```

Đổi `edgeToV3`:

```ts
export function edgeToV3(edge: CanvasEdge): CanvasEdgeV3 {
  // ⭐ CHI nhanh LOI duoc khai o day. Nhanh `true`/`false` cua core.if/switch
  //    do MAY CHU suy ra tu kieu cong (`bien_dich._suy_kind_canh`) — client
  //    khong co bang kieu cong, va mot ban cai dat thu hai thi lech im lang.
  const laLoi = edge.data?.condition === 'error'
  return {
    id: edge.id,
    source_node: edge.source,
    target_node: edge.target,
    source_port: edge.sourceHandle || DEFAULT_SOURCE_PORT,
    target_port: edge.targetHandle || DEFAULT_TARGET_PORT,
    kind: laLoi ? 'ERROR' : 'DATA',
  }
}
```

Đổi `edgeFromV3`:

```ts
export function edgeFromV3(edge: CanvasEdgeV3): CanvasEdge {
  return {
    id: edge.id,
    source: edge.source_node,
    target: edge.target_node,
    sourceHandle: edge.source_port,
    targetHandle: edge.target_port,
    ...(edge.kind === 'ERROR'
      ? { data: { condition: 'error' as const } }
      : {}),
  }
}
```

- [ ] **Bước 4: Chạy để xác nhận XANH**

```bash
cd frontend/agent-canvas && npm test -- workflowApi
```

Kỳ vọng: **PASS**.

- [ ] **Bước 5: Commit**

```bash
git add frontend/agent-canvas/src/workflowApi.ts frontend/agent-canvas/tests/workflowApi.test.ts
git commit -m "fix(canvas): gui kind=ERROR cho nhanh loi (nut 'Nhanh: Loi' nay co tac dung that)"
```

---

## Task 4: Cổng nối có vị trí thật và vùng bấm 24px

**Files:**
- Modify: `frontend/agent-canvas/src/canvas.css`
- Modify: `frontend/agent-canvas/src/nodes/NodeKhung.tsx`
- Test: `frontend/agent-canvas/tests/NodeRenderer.test.tsx` (thêm vào tệp đã có)

**Interfaces:**
- Consumes: `NodeKhung({ dinhNghia, trangThai, children })` — chữ ký **không đổi**
- Produces: mỗi `.node-cong` là một khối định vị (`position: relative`); `Handle`
  bên trong neo theo hàng của chính nó.

**Bối cảnh.** `.react-flow__handle` là `position:absolute`, `.react-flow__handle-left`
là `{top:50%; left:0}`. `.node-cong` là `position:static` ⇒ không có tổ tiên định vị
ở hàng ⇒ cả 15 cổng quy chiếu về **thẻ node** và ra **cùng một điểm**.
Đo 27/09: `targetDistinctPositions: 1`, `elementFromPoint` luôn trả cổng **cuối**.

- [ ] **Bước 1: Viết phép kiểm ĐỎ**

Thêm vào `frontend/agent-canvas/tests/NodeRenderer.test.tsx`:

```tsx
it('moi hang cong la mot khoi dinh vi rieng', () => {
  // jsdom khong tinh layout that, nen ⛔ KHONG do toa do o day —
  // do bang `getBoundingClientRect` trong jsdom luon tra 0 va se cho mot
  // phep kiem XANH GIA. Kiem dung thu kiem duoc: hop dong CSS.
  const { container } = render(
    <NodeRenderer {...propsGia({ cong_vao: [
      { ten: 'a', kieu: 'text', bat_buoc: true, nhieu: false },
      { ten: 'b', kieu: 'image', bat_buoc: false, nhieu: false },
    ] })} />)
  const hang = container.querySelectorAll('.node-cong-vao')
  expect(hang).toHaveLength(2)
  hang.forEach(h => {
    // Moi hang phai CHINH no chua handle cua no (khong phai mot to tien chung).
    expect(h.querySelector('.react-flow__handle')).not.toBeNull()
  })
})
```

🔴 **Phép kiểm toạ độ THẬT không chạy được trong jsdom** — nó không tính layout, mọi
`getBoundingClientRect()` trả 0, nên một phép so toạ độ ở đây sẽ **XANH GIẢ**. Phép
đo thật nằm ở Task 6 (Playwright, trình duyệt thật). Đây đúng là bài học *"đọc thứ
đại diện thay vì đọc thứ thật"*: jsdom không đại diện được cho layout.

- [ ] **Bước 2: Chạy để xác nhận trạng thái hiện tại**

```bash
cd frontend/agent-canvas && npm test -- NodeRenderer
```

Kỳ vọng: **PASS** (cấu trúc DOM đã đúng từ trước — lỗi nằm ở CSS). Phép kiểm này là
lưới chống hồi quy cho Task 6, không phải phép kiểm đỏ-rồi-xanh.

- [ ] **Bước 3: Sửa CSS**

Trong `canvas.css`, tìm `.node-cong {` và thay khối đó bằng:

```css
/* 🔴 `position:relative` KHONG phai trang tri. `.react-flow__handle` la
   `position:absolute` va `.react-flow__handle-left` la `{top:50%;left:0}` —
   khong co to tien dinh vi o HANG thi ca 15 cong quy chieu ve THE NODE va roi
   dung MOT diem. Do 27/09/2026: 15 cong, 1 vi tri, keo day tao 0 canh trong im
   lang. Go dong nay la lam hong lai ca viec noi day. */
.node-cong { position:relative; display:flex; gap:6px; font-size:11px;
             min-height:var(--handle-hit,24px); align-items:center; }
.node-cong-ra { justify-content:flex-end; }

/* Vung bam >= 24px (WCAG 2.2 AA 2.5.8) trong khi cham tron van nho. */
.node-cong .react-flow__handle {
  width:var(--handle-size,12px); height:var(--handle-size,12px);
}
.node-cong .react-flow__handle::after {
  content:''; position:absolute; inset:50% auto auto 50%;
  width:var(--handle-hit,24px); height:var(--handle-hit,24px);
  transform:translate(-50%,-50%);
}
```

Và thêm vào khối token ở đầu tệp (nếu chưa có `:root` phạm vi canvas, tạo nó):

```css
.canvas-shell { --handle-size:12px; --handle-hit:24px; }
```

⚠️ UI-2 là chủ sở hữu `canvas.css` về sau. Task này được phép sửa vì UI-2 **chưa
mở** — ghi vào *Phiếu tệp* để UI-2 biết khi nhận bàn giao.

- [x] **Bước 4: Cache-bust — ✅ KHÔNG cần làm gì (plan đã sai, đã sửa 27/09)**

Plan bản đầu ghi *"tăng `ASSET_VER` lên một"*. **Sai.** Đọc `server/templating.py`:

- `ASSET_VER = _tinh_asset_ver()` là **hash MD5 tự tính** từ nội dung của
  `TAI_SAN_CO_VERSION` — một danh sách **cố định** gồm `ltt.css`, `htmx.min.js`,
  `voice.js`… ⛔ **không có** `agent-canvas`. Không có hằng số nào để "tăng".
- Bundle Canvas do **Vite đặt tên theo hash nội dung** (`main-Bmc_qv-u.js`), và
  `bundle_assets("agent-canvas")` phát đúng tên tệp ấy ra template. Đổi CSS ⇒ đổi
  tên tệp ⇒ URL mới ⇒ **tự cache-bust**.

⇒ ⛔ Sửa `server/templating.py` ở pha này là **thừa và sai** — nó sẽ đụng một tệp
không thuộc phạm vi UI-0 mà không đổi được gì. Gỡ `server/templating.py` khỏi
*Phiếu tệp* của làn.

⚠️ Điều **thật sự** phải làm để CSS mới tới được người dùng: **build lại bundle**
(Task 6 Bước 1). Không build thì `canvas.css` mới nằm trong `src/` và không ai thấy.

- [ ] **Bước 5: Chạy lại test frontend**

```bash
cd frontend/agent-canvas && npm test
```

Kỳ vọng: **PASS** toàn bộ.

- [ ] **Bước 6: Commit**

```bash
git add frontend/agent-canvas/src/canvas.css frontend/agent-canvas/tests/NodeRenderer.test.tsx server/templating.py
git commit -m "fix(canvas): moi cong noi co vi tri rieng + vung bam 24px (WCAG 2.5.8)"
```

---

## Task 5: Gỡ nút `+` chết và sửa bước xếp node chồng nhau

**Files:**
- Modify: `frontend/agent-canvas/src/CanvasEdgeView.tsx`
- Modify: `frontend/agent-canvas/src/editorState.ts` (hàm `nextNode`, và `case 'layout'`)
- Test: `frontend/agent-canvas/tests/editorState.test.ts` (thêm vào tệp đã có)

**Interfaces:**
- Consumes: `nextNode(nd: NodeDefinition, count: number) -> CanvasNode`
- Produces: chữ ký **không đổi**. Chỉ hằng số bước xếp đổi.

**Bối cảnh.** Hai lỗi nhỏ, cùng một lần chạm:

1. `CanvasEdgeView` vẽ nút `+` trên **mọi** cạnh và gọi `data.onInsert?.(…)`, nhưng
   `onInsert` **chưa bao giờ được gán**. Bấm thật 27/09: node 3→3, cạnh 2→2, không
   picker nào mở. ⇒ Một nút không-op trên mọi cạnh. **Gỡ**, không giữ — UI-4 sẽ dựng
   lại nó có thật. ⛔ Một nút chết làm người dùng mất niềm tin vào mọi nút khác.
2. `nextNode` xếp bước **430px** nhưng node rộng **456px** ⇒ node thứ hai **đè 26px**
   lên node thứ nhất.

- [ ] **Bước 1: Viết phép kiểm ĐỎ**

Thêm vào `frontend/agent-canvas/tests/editorState.test.ts`:

```ts
import { nextNode } from '../src/editorState'

describe('nextNode — buoc xep phai rong hon node', () => {
  it('hai node lien tiep KHONG duoc de len nhau', () => {
    // Node rong nhat do duoc tren trinh duyet that (app.video.generate) la
    // 456px. Buoc xep phai > con so do, khong phai xap xi.
    const RONG_NHAT = 456
    const a = nextNode(nutGia(), 0)
    const b = nextNode(nutGia(), 1)
    expect(b.position.x - a.position.x).toBeGreaterThan(RONG_NHAT)
  })
})
```

- [ ] **Bước 2: Chạy để xác nhận ĐỎ**

```bash
cd frontend/agent-canvas && npm test -- editorState
```

Kỳ vọng: **FAIL** — nhận 430, cần > 456.

- [ ] **Bước 3: Đổi hằng số bước xếp**

Trong `editorState.ts`, thêm ngay trước `export function nextNode`:

```ts
/** Buoc xep node mac dinh.
 *
 *  🔴 PHAI LON HON node rong nhat. Do 27/09/2026 tren trinh duyet that:
 *     `app.video.generate` rong 456px, con buoc xep cu la 430px — nen node thu
 *     HAI da de len node thu nhat 26px va che mat duoi tieu de cua no.
 *     Khong phai "hoi chat", la SAI. */
export const BUOC_XEP_X = 520
export const BUOC_XEP_Y = 260
```

Trong `nextNode`, đổi:

```ts
    position: { x: 90 + (count % 3) * BUOC_XEP_X,
                y: 90 + Math.floor(count / 3) * BUOC_XEP_Y },
```

Trong `case 'layout':`, đổi `430` thành `BUOC_XEP_X` và `430` (trục y) thành
`BUOC_XEP_Y`:

```ts
    case 'layout': return changed(state, updateActive(state.document, page => ({ ...page,
      nodes: page.nodes.map((node, index) => ({ ...node,
        position: { x: 90 + (index % 4) * BUOC_XEP_X,
                    y: 90 + Math.floor(index / 4) * BUOC_XEP_Y } })) })))
```

- [ ] **Bước 4: Gỡ nút `+` chết**

Thay toàn bộ `frontend/agent-canvas/src/CanvasEdgeView.tsx` bằng:

```tsx
import {BaseEdge,getSmoothStepPath,type EdgeProps} from '@xyflow/react'

// ⛔ Nut "+" chen buoc DA GO (UI-0 Task 5). No goi `data.onInsert`, va
//    `onInsert` chua bao gio duoc gan o bat ky dau trong `src/` — bam that
//    27/09/2026: node 3->3, canh 2->2, khong picker nao mo. Mot nut khong-op
//    tren MOI canh lam nguoi dung mat niem tin vao moi nut con lai.
//
//    UI-4 se dung lai no CO THAT (quick-add tu cong + chen giua canh). Dung
//    khoi phuc tep nay ma khong noi `onInsert` truoc.
export function CanvasEdgeView({id,sourceX,sourceY,targetX,targetY,
  sourcePosition,targetPosition,markerEnd,style}:EdgeProps){
  const [path]=getSmoothStepPath({sourceX,sourceY,targetX,targetY,
    sourcePosition,targetPosition,borderRadius:14})
  return <BaseEdge id={id} path={path} markerEnd={markerEnd} style={style}/>
}
```

Rồi gỡ lớp CSS không còn ai dùng trong `canvas.css`: tìm và xoá mọi quy tắc cho
`.edge-insert`.

- [ ] **Bước 5: Chạy để xác nhận XANH**

```bash
cd frontend/agent-canvas && npm test
```

Kỳ vọng: **PASS** toàn bộ.

- [ ] **Bước 6: Commit**

```bash
git add frontend/agent-canvas/src/editorState.ts frontend/agent-canvas/src/CanvasEdgeView.tsx frontend/agent-canvas/src/canvas.css frontend/agent-canvas/tests/editorState.test.ts
git commit -m "fix(canvas): buoc xep 520px (het de node) + go nut '+' chen buoc khong-op"
```

---

## Task 6: Nghiệm thu trên TRÌNH DUYỆT THẬT

**Files:**
- Create: `tests/browser/agent_ui_v2_ui0_nghiem_thu.js`
- Create: `tests/browser/agent_ui_v2_ui0_may_chu.py`
- Modify: `docs/architecture/agent_ui_v2/00_SO_TIEN_DO.md`

**Interfaces:**
- Consumes: bundle đã build ở `server/static/agent-canvas/`
- Produces: kịch bản trả `{status:'PASS'|'FAIL', so_lieu:{…}}` — UI-3…UI-11 dùng lại
  khuôn này.

🔴 **⛔ KHÔNG đọc mã rồi tuyên bố đã sửa.** Ba trong bốn lỗi của pha này chỉ lộ ra
trên layout thật; jsdom không tính layout nên test frontend **không** chứng minh
được Task 4.

- [ ] **Bước 1: Build lại bundle**

```bash
python "C:\Users\Thang Tuong\.claude\ltt\chay_nang.py" --phien ui0 -- cmd /c "cd /d D:\...\frontend\agent-canvas && npm run build"
```

⚠️ Đây là lệnh nặng ⇒ **phải** đi qua `chay_nang.py`. ⛔ Không gộp bước đọc kết quả
hay sửa mã vào cùng một lượt giữ khoá — nhả khoá ngay khi build xong.

⚠️ Sau khi build, xác nhận bundle **đại diện đúng** mã nguồn:

```bash
node -e "const{createHash}=require('crypto'),{readFileSync}=require('fs');console.log(JSON.parse(readFileSync('server/static/agent-canvas/build-meta.json','utf8')).source_sha256)"
```

- [ ] **Bước 2: Dựng máy chủ cô lập**

Tạo `tests/browser/agent_ui_v2_ui0_may_chu.py`, chép khuôn từ
`tests/fixtures/image_studio_server.py` (cùng kho), đổi: cổng 8198, sqlite trong thư
mục tạm ngoài kho, một tài khoản fixture có credit.

🔴 ⛔ **KHÔNG chạy trên cổng 8100** — đó là production thật trên chính máy này.

- [ ] **Bước 3: Viết kịch bản nghiệm thu**

Tạo `tests/browser/agent_ui_v2_ui0_nghiem_thu.js`:

```js
// UI-0 nghiem thu — BON phep do tren trinh duyet THAT.
// ⛔ Khong doc ma roi tuyen bo; ba trong bon loi chi lo ra o layout that.
async page => {
  const base = 'http://127.0.0.1:8198';
  const loi = [];
  const check = (dk, msg) => { if (!dk) loi.push(msg); };

  await page.goto(base + '/agent/canvas');
  check(!page.url().includes('/login'), 'chua dang nhap');

  // ── Phep do 1: node core.* tu palette BIEN DICH duoc ──────────────
  await page.evaluate(async () => {
    const csrf = document.querySelector('#agent-canvas-root').dataset.csrfToken;
    const ds = await (await fetch('/agent/api/v3/workflows',
      {credentials:'same-origin',headers:{Accept:'application/json'}})).json();
    const id = ds.items[0].id;
    const cur = await (await fetch('/agent/api/v3/workflows/' + id,
      {credentials:'same-origin',headers:{Accept:'application/json'}})).json();
    await fetch('/agent/api/v3/workflows/' + id, {method:'PUT',
      credentials:'same-origin',
      headers:{'Content-Type':'application/json','X-CSRF-Token':csrf,
               'If-Match':'"' + cur.revision + '"'},
      body: JSON.stringify({csrf_token: csrf, document:{
        version:3, goal:'', budget_max_credit:0, active_page_id:'p1',
        pages:[{id:'p1',name:'Page 1',viewport:{x:0,y:0,zoom:1},
                frames:[],notes:[],comments:[],
                nodes:[{id:'n-set',type:'tool',position:{x:90,y:90},
                        data:{tool:'core.set',params:{bien:{}}}}],
                edges:[]}]}})});
  });
  await page.goto(base + '/agent/canvas');
  await page.locator('button.run-primary').click();
  await page.locator('button.run-confirm').click();
  await page.waitForTimeout(2500);
  const loiChay = await page.evaluate(() =>
    document.querySelector('.run-error')?.textContent ?? null);
  check(!(loiChay || '').includes('node_khong_ton_tai'),
        'P0-1 CHUA SUA: ' + loiChay);

  // ── Phep do 2: cong noi co vi tri KHAC NHAU ───────────────────────
  const cong = await page.evaluate(() => {
    const n = document.querySelector('.react-flow__node');
    if (!n) return null;
    const hs = [...n.querySelectorAll('.react-flow__handle.target')];
    return {so: hs.length,
            viTri: new Set(hs.map(h => {
              const r = h.getBoundingClientRect();
              return Math.round(r.x) + ',' + Math.round(r.y);
            })).size,
            cao: hs[0] ? Math.round(hs[0].getBoundingClientRect().height) : 0};
  });
  if (cong && cong.so > 1) {
    check(cong.viTri === cong.so,
      `P0-2 CHUA SUA: ${cong.so} cong nhung chi ${cong.viTri} vi tri`);
  }

  // ── Phep do 3: KEO DAY tao ra mot canh THAT ───────────────────────
  // (seed hai node app.* roi keo cong image_keys -> image_key)
  // ... (chi tiet: xem Buoc 4)

  // ── Phep do 4: khong con nut '+' chet tren canh ───────────────────
  const nutChet = await page.evaluate(() =>
    document.querySelectorAll('.edge-insert').length);
  check(nutChet === 0, `P0 nut '+' chet van con: ${nutChet}`);

  if (loi.length) return {status:'FAIL', loi};
  return {status:'PASS', so_lieu:{cong}};
}
```

- [ ] **Bước 4: Hoàn thiện phép đo 3 (kéo dây thật)**

Thay khối `// ...` bằng: seed hai node `image.generate` và `video.generate`, tải lại
trang, rồi dùng `page.locator(...).dragTo(...)` từ cổng `image_keys` sang cổng
`image_key`, rồi đọc `data-edge-count` trên `.canvas-stage`.

🔴 Mốc nền 27/09: thao tác này tạo **0** cạnh và Playwright còn **không click nổi**
cổng `image_keys` (*"subtree intercepts pointer events"*). Sau Task 4, nó phải tạo
đúng **1** cạnh. Nếu Playwright vẫn báo "intercepts pointer events" thì Task 4
**chưa xong** — ⛔ không đánh dấu pha là xong.

- [ ] **Bước 5: Chạy nghiệm thu**

```bash
python tests/browser/agent_ui_v2_ui0_may_chu.py   # nền, cổng 8198
playwright-cli -s=ui0 run-code --filename=tests/browser/agent_ui_v2_ui0_nghiem_thu.js
```

Kỳ vọng: `"status": "PASS"`.

- [ ] **Bước 6: Chụp ảnh trước/sau**

Lưu vào `docs/architecture/agent_ui_v2/bang_chung/` với tiền tố `ui0_sau_`. So với
`04_hai_node_chong_nhau_cong_chong_diem.png` (ảnh "trước" đã có).

- [ ] **Bước 7: Dừng máy chủ thử**

```bash
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*ui0_may_chu*' } | ForEach-Object { $_.ProcessId }"
```

⛔ **Chỉ giết pid do chính mình khởi động, và TỪ CHỐI mọi pid có cha là `services.exe`.**
In `CommandLine` từng pid trước khi giết. Sau đó xác nhận cổng 8100 vẫn trả 200.

- [ ] **Bước 8: Cập nhật sổ + commit**

Điền *Bảng độ phủ*: UX-3 và UX-5 đổi sang ✅ nếu kịch bản xanh. Đổi trạng thái UI-0
sang `CHỜ DUYỆT`.

```bash
git add tests/browser/ docs/architecture/agent_ui_v2/
git commit -m "test(browser): nghiem thu UI-0 tren trinh duyet that (4 phep do)"
```

---

## Task 7: Gộp `main` và bàn giao

- [ ] **Bước 1: Chạy trọn bộ test nhắm**

```bash
python -m pytest tests/test_5600_wf_node_palette_bien_dich.py tests/test_5601_wf_canh_dieu_khien_suy_ra.py tests/test_1714_wf_bien_dich.py tests/test_1719_wf_dong_co.py tests/test_1783_wf_nut_dieu_huong.py tests/test_4250_wf_v3_soan_data_tool_shape.py -q
cd frontend/agent-canvas && npm test
```

Kỳ vọng: cả hai **PASS**. ⛔ Nếu đỏ: sửa tại chỗ, chạy lại **đúng** phép đã đỏ.

- [ ] **Bước 2: Gộp `main`**

```bash
git checkout main && git merge phien/ui0 && pre-commit run --all-files
```

⚠️ Merge **không** chạy bánh cóc, nên `pre-commit run --all-files` là lưới duy nhất.

⛔ **KHÔNG chạy gate.** Xong UI-0 không phải cuối plan.

- [ ] **Bước 3: Trả phiếu tệp và báo**

Đổi UI-0 sang `ĐÃ GỘP`, xoá các hàng của UI-0 khỏi *Phiếu tệp*, mở UI-3.

Báo chủ dự án **ba** điều, không hơn:
1. 55/67 loại bước đã biên dịch được — có số đo trình duyệt.
2. 🔴 **R3 — đổi hành vi:** `core.if` nay chạy **một** nhánh thay vì cả hai.
   Hỏi: **deploy UI-0 ngay hay đợi cuối plan?** (deploy giữa plan cần gate xanh
   trên đúng SHA ⇒ đây là quyết định của chủ dự án, ⛔ không tự quyết).
3. UI-3 đã sẵn sàng mở.

---

## Task 8: Chốt trên WEB THẬT sau khi deploy

> ⚠️ Task này **chỉ chạy sau khi chủ dự án đồng ý deploy UI-0** (Task 7 Bước 3).
> Nếu quyết định là "đợi cuối plan" thì Task 8 dời sang UI-11.

**Files:**
- Create: `tests/browser/agent_ui_v2_ui0_web_that.js`
- Modify: `docs/architecture/agent_ui_v2/00_SO_TIEN_DO.md`

**Bối cảnh.** Task 6 chạy ở **chế độ A** (máy chủ cô lập 8198) — nó chứng minh *mã
mới* đúng. Nó **không** chứng minh *bản deploy* đúng: bundle có được build lại không,
`ASSET_VER` có bump không, Cloudflare có phục vụ đúng tệp không. CLAUDE.md luật 7 đòi
chốt trên `https://app.lttstudios.com`, ⛔ không phải loopback — loopback bỏ qua
Cloudflare, và Cloudflare đã từng là thủ phạm thật.

- [ ] **Bước 1: Lấy cookie tài khoản thử (⛔ không gõ mật khẩu)**

```bash
python tools\nang_quyen.py --lenh "C:\LTTPlatform\venv\Scripts\python.exe tools\tai_khoan_thu.py --app-env C:\LTTPlatform\secrets\app.env --cookie khach1.thu@lttstudios.local"
```

Kết quả một dòng: `session=<giá trị>`. Đặt vào biến môi trường `LTT_COOKIE_THU`.

⚠️ Nếu tài khoản chưa có hoặc hết credit:

```bash
python tools\nang_quyen.py --lenh "C:\LTTPlatform\venv\Scripts\python.exe tools\tai_khoan_thu.py --app-env C:\LTTPlatform\secrets\app.env --tao-bo --nap-den 20000"
```

⛔ **Không** chạy `--dat-lai-mat-khau` — nó thu hồi mọi phiên cũ và đá văng phiên
khác đang dùng cookie.

- [ ] **Bước 2: Viết kịch bản web thật**

Tạo `tests/browser/agent_ui_v2_ui0_web_that.js`:

```js
// UI-0 chot tren WEB THAT (CLAUDE.md luat 7: chot tren app.lttstudios.com,
// KHONG chot tren loopback — loopback bo qua Cloudflare).
//
// Dang nhap bang COOKIE tu `tools/tai_khoan_thu.py --cookie`, ⛔ khong go mat
// khau vao form. Tai khoan duoi `.local`, khong phai khach that.
async page => {
  const COOKIE = process.env.LTT_COOKIE_THU;
  if (!COOKIE) throw new Error('thieu LTT_COOKIE_THU — xem Buoc 1');

  const pageErrors = [], consoleErrors = [], failedRequests = [], serverErrors = [];
  page.on('pageerror',     e => pageErrors.push(e.message));
  page.on('console',       m => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  page.on('requestfailed', r => failedRequests.push({url: r.url(), err: r.failure()?.errorText}));
  page.on('response',      r => { if (r.status() >= 500) serverErrors.push({url: r.url(), status: r.status()}); });

  await page.context().addCookies([{ name: 'session', value: COOKIE,
    domain: 'app.lttstudios.com', path: '/', secure: true, httpOnly: true }]);

  const loi = [];
  const check = (dk, msg) => { if (!dk) loi.push(msg); };

  await page.goto('https://app.lttstudios.com/agent/canvas');
  check(!page.url().includes('/login'), 'cookie khong con hieu luc — lay lai o Buoc 1');
  await page.locator('#agent-canvas-root').waitFor();

  // ── Phep do 1: ban deploy DA MANG ban va CSS cong noi ───────────────
  // Them mot node nhieu cong roi dem SO VI TRI KHAC NHAU cua cong vao.
  await page.locator('.canvas-rail button[aria-label="Mo cong cu"]').click()
    .catch(() => page.locator('.canvas-rail button').nth(1).click());
  await page.waitForTimeout(600);
  const cong = await page.evaluate(() => {
    const n = document.querySelector('.react-flow__node');
    if (!n) return null;
    const hs = [...n.querySelectorAll('.react-flow__handle.target')];
    return {so: hs.length, viTri: new Set(hs.map(h => {
      const r = h.getBoundingClientRect();
      return Math.round(r.x) + ',' + Math.round(r.y);
    })).size};
  });
  if (cong && cong.so > 1) {
    check(cong.viTri === cong.so,
      `ban DEPLOY chua mang ban va cong: ${cong.so} cong / ${cong.viTri} vi tri`);
  }

  // ── Phep do 2: khong con nut '+' chet ───────────────────────────────
  check(await page.evaluate(() => document.querySelectorAll('.edge-insert').length) === 0,
        "ban deploy van con nut '+' chet");

  // ── Phep do 3: bon so hieu suc khoe trang ───────────────────────────
  check(pageErrors.length === 0,     'pageerror: ' + JSON.stringify(pageErrors));
  check(consoleErrors.length === 0,  'console error: ' + JSON.stringify(consoleErrors));
  check(failedRequests.length === 0, 'request hong: ' + JSON.stringify(failedRequests));
  check(serverErrors.length === 0,   '5xx: ' + JSON.stringify(serverErrors));

  if (loi.length) return {status: 'FAIL', loi};
  return {status: 'PASS', so_lieu: {cong}};
}
```

- [ ] **Bước 3: Chạy trên profile trình duyệt RIÊNG của làn**

```bash
playwright-cli -s=ui0 run-code --filename=tests/browser/agent_ui_v2_ui0_web_that.js
```

⛔ `-s=ui0` là profile riêng của làn — **không** dùng Chrome thật của chủ dự án.

Kỳ vọng: `"status": "PASS"`.

⚠️ Nếu phép đo 1 hoặc 2 đỏ mà Task 6 (8198) đã xanh ⇒ **không phải lỗi mã**, mà là
**lỗi đường deploy**: bundle chưa build lại, `ASSET_VER` chưa bump, hoặc Cloudflare
còn phục vụ bản cũ. Kiểm theo đúng thứ tự đó.

- [ ] **Bước 4: Chụp ảnh chốt + ghi sổ**

Lưu `bang_chung/ui0_web_that_<ngày>.png`. Ghi vào *Nhật ký* một dòng có **số**, ví dụ
`15 cổng / 15 vị trí`, ⛔ không ghi "đã xác minh" suông.

- [ ] **Bước 5: Commit**

```bash
git add tests/browser/agent_ui_v2_ui0_web_that.js docs/architecture/agent_ui_v2/
git commit -m "test(browser): chot UI-0 tren web that qua cookie tai khoan thu"
```

---

## Self-review

**Phủ spec.** Bốn lỗi P0 của `01 §2`: P0-1 → Task 1 · P0-2 → Task 4 · P0-3
(credential) → **KHÔNG thuộc pha này**, nó là UI-5 và bị chặn bởi Q4 · P0-4 → Task 2
(nhánh true/false) + Task 3 (nhánh lỗi). Hai lỗi P1 rẻ đi kèm: nút `+` chết và node
đè nhau → Task 5. ✅

**Quét placeholder.** Không có "TBD"/"xử lý lỗi phù hợp"/"tương tự Task N". Chỗ duy
nhất chưa có mã đầy đủ là Task 6 Bước 4 (kéo dây), và nó được viết thành **một bước
riêng có hướng dẫn cụ thể + mốc nền + tiêu chí đỏ/xanh**, không phải một lời hứa.
Số tệp test đã được cấp thật (`5600`, `5601`) ở Task 0 và ghim vào mọi lệnh, không
còn chỗ trống nào.

**Sửa sau khi lập plan (27/09, trước khi viết dòng mã đầu tiên).** Bước xác minh
`nut_loi.tat_ca()` mà chính Task 1 dặn chạy đã bắt một **lỗi thiết kế trong Task 2**:
luật suy `(CONTROL, tên cổng)` cho *mọi* cổng `control` sẽ gán `condition='nhanh'`
cho `core.switch` (node đó có **một** cổng control tên chung, tên nhánh nằm trong
tham số) ⇒ **mọi nhánh switch chết**, hồi quy tệ hơn hiện trạng. Luật đã thu hẹp
thành *"chỉ suy khi node nguồn có ≥ 2 cổng control"*, và thêm một phép kiểm hồi quy
ghim rằng `core.switch` đi qua nguyên vẹn.

**Nhất quán kiểu.** `_suy_kind_canh(loai_nguon, cong, so) -> (kind, condition)` khai
ở Task 2 và không có task nào khác gọi. `CanvasEdgeKind` mở rộng ở Task 3 và
`edgeFromV3` khớp `edgeToV3`. `BUOC_XEP_X`/`BUOC_XEP_Y` khai một lần ở Task 5 và
dùng ở cả `nextNode` lẫn `case 'layout'`.

**Một rủi ro còn mở, đã ghi:** Task 2 đổi hành vi thật (R3) — có bước báo riêng ở
Task 7 Bước 3 thay vì giấu trong commit.
