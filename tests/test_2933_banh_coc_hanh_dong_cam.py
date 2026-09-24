"""🔴 BÁNH CÓC CƠ HỌC — *"hành động cấm KHÔNG CÓ đường gọi"*.

Điều kiện ra của **phase gốc 12** (spec §19 dòng 12: *"các hành động cấm không
có đường gọi (phép kiểm)"*). Đây là một phép đo trên **đồ thị gọi có thật**
(`ast`), ⛔ không phải một giao ước trong tài liệu và ⛔ không phải một `if`
lúc chạy — một `if` là thứ người ta sửa được trong một dòng mà không ai thấy.

## Nó hỏi ĐÚNG mệnh đề nào

    Từ mọi hành động supervisor công bố (`supervisor.HANH_DONG`) và từ cửa soạn
    draft (`ke_hoach_v3.soan_draft`), đi theo MỌI lời gọi giải được trong
    `platform_core/`, có tới được một trong các hàm CẤM không?

`CAM` là danh sách địa chỉ thật, không phải khái niệm: mỗi mục là một hàm đang
tồn tại, và §12.4 cấm đúng hành động mà hàm ấy làm.

## 🔑 Nó KHÔNG phủ cái gì — nói trước khi ai hỏi

- **Gọi động**: `getattr(mod, "ten")()`, `eval`, `exec`, `__import__`. Đồ thị
  tĩnh không thấy chúng, nên phép kiểm thứ hai dưới đây **cấm hẳn** bốn tên ấy
  trong tập hàm với tới được. Bịt bằng một luật khác, không bằng hy vọng.
- **Gọi qua phương thức của đối tượng** (`db.execute(...)`, `x.f()` khi `x`
  không phải bí danh mô-đun): không giải được ⇒ không theo. Một lời gọi cấm
  giấu sau một đối tượng sẽ **lọt**. Đây là lỗ đã biết, và nó hẹp: mọi hàm
  trong `CAM` đều là hàm cấp mô-đun, gọi qua `<mo_dun>.<ham>`.
- **SQL thô**: một `UPDATE workflow_version …` viết tay không đi qua hàm nào
  trong `CAM`. Phép kiểm thứ ba cấm chuỗi `UPDATE`/`INSERT` thô trong tập ấy.
- Nó không nói gì về việc các hành động ĐƯỢC PHÉP có đúng luật không —
  `test_2932` đo phần đó.

## ⭐ Bánh cóc phải CẮN: có tiêm lỗi

`test_banh_coc_CAN_khi_tiem_mot_loi_gia` dựng lại đồ thị trên một bản
`supervisor.py` **đã bị sửa trong bộ nhớ** để gọi `tien.giu_cho_run`, rồi đòi
phép dò phải báo. Không có nó, một phép dò rỗng (đọc nhầm thư mục, tên hàm gõ
sai) cũng xanh — đúng bài học *"không đối chứng thì số 0 không phải phát hiện"*.
"""
from __future__ import annotations

import ast
import pathlib
from collections import deque

import pytest

GOC = pathlib.Path(__file__).resolve().parent.parent / "platform_core"

#: 🔴 HÀM CẤM. Mỗi dòng ánh xạ một gạch đầu dòng của spec §12.4
#: (*"Cấm (không có hàm nào làm được): tăng hold, sửa version đã publish, gắn
#: credential, vượt validator, thử lại node irreversible ABANDONED"*).
CAM: dict[str, str] = {
    # tăng hold / đụng sổ tiền
    "platform_core.workflow.tien:giu_cho_run": "tang hold cua run",
    "platform_core.workflow.ket_so:ket_so": "quyet toan lai mot run",
    "platform_core.credit:giu_cho": "giu them credit",
    "platform_core.credit:tru": "tru credit",
    "platform_core.credit:nap": "nap credit",
    "platform_core.credit:cap_tay": "cap credit tay",
    # sửa version đã publish / vượt validator
    "platform_core.workflow.dinh_nghia:xuat_ban": "ghi mot workflow_version",
    "platform_core.workflow.dinh_nghia:xuat_ban_draft": "publish mot draft",
    "platform_core.workflow.dinh_nghia:luu_draft": "ghi de ban nhap",
    # gắn credential
    "platform_core.api_keys:dat_credential": "gan credential",
    "platform_core.api_keys:lay_credential": "doc credential tho",
    "platform_core.api_keys:tao_key": "tao khoa API",
    # nộp việc không qua cổng trần báo giá của cầu nối
    "platform_core.jobs:submit": "nop job thang, bo qua tran bao gia",
}

#: Tên gọi ĐỘNG — đồ thị tĩnh mù với chúng, nên cấm hẳn trong tập với tới được.
GOI_DONG = frozenset({"getattr", "eval", "exec", "__import__", "globals"})


# ── Dựng đồ thị gọi ─────────────────────────────────────────────────────────

def _ten_mo_dun(p: pathlib.Path) -> str:
    rel = p.relative_to(GOC.parent).with_suffix("")
    phan = list(rel.parts)
    if phan[-1] == "__init__":
        phan.pop()
    return ".".join(phan)


def nap_nguon(ghi_de: dict | None = None) -> dict:
    """`{tên mô-đun: mã nguồn}` cho cả `platform_core/`. `ghi_de` thay một tệp."""
    ra = {}
    for p in sorted(GOC.rglob("*.py")):
        if "__pycache__" in p.parts:
            continue
        ra[_ten_mo_dun(p)] = p.read_text(encoding="utf-8")
    ra.update(ghi_de or {})
    return ra


def _bi_danh(cay: ast.AST, mo_dun: str) -> tuple[dict, dict]:
    """`({bí danh mô-đun: mô-đun}, {tên đã import: "mô-đun:tên"})`."""
    bd_mod: dict[str, str] = {}
    bd_ten: dict[str, str] = {}
    for n in ast.walk(cay):
        if isinstance(n, ast.Import):
            for a in n.names:
                bd_mod[a.asname or a.name.split(".")[0]] = a.name
        elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
            for a in n.names:
                # `from x.y import z` — `z` là mô-đun con hay một cái tên?
                # Ghi cả hai cách hiểu; chỉ một cách khớp thật sẽ có cạnh.
                bd_mod[a.asname or a.name] = f"{n.module}.{a.name}"
                bd_ten[a.asname or a.name] = f"{n.module}:{a.name}"
    return bd_mod, bd_ten


def _dinh_nghia_trong(cay: ast.AST) -> dict:
    """`{tên hàm: node}` — hàm cấp mô-đun và phương thức `Lop.ham`."""
    ra = {}
    for n in cay.body:                                   # type: ignore[attr-defined]
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            ra[n.name] = n
        elif isinstance(n, ast.ClassDef):
            for m in n.body:
                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    ra[f"{n.name}.{m.name}"] = m
    return ra


def do_thi_goi(nguon: dict) -> tuple[dict, dict]:
    """`({"mo_dun:ham": {đích…}}, {"mo_dun:ham": {tên gọi động…}})`."""
    canh: dict[str, set] = {}
    dong: dict[str, set] = {}
    for mod, ma in nguon.items():
        try:
            cay = ast.parse(ma)
        except SyntaxError:                              # pragma: no cover
            continue
        bd_mod, bd_ten = _bi_danh(cay, mod)
        trong = _dinh_nghia_trong(cay)
        for ten, than in trong.items():
            khoa = f"{mod}:{ten}"
            ra: set = canh.setdefault(khoa, set())
            dg: set = dong.setdefault(khoa, set())
            for c in ast.walk(than):
                if not isinstance(c, ast.Call):
                    continue
                f = c.func
                if isinstance(f, ast.Name):
                    if f.id in GOI_DONG:
                        dg.add(f.id)
                    elif f.id in trong:
                        ra.add(f"{mod}:{f.id}")
                    elif f.id in bd_ten:
                        ra.add(bd_ten[f.id])
                elif isinstance(f, ast.Attribute) and isinstance(f.value,
                                                                 ast.Name):
                    goc = bd_mod.get(f.value.id)
                    if goc:
                        ra.add(f"{goc}:{f.attr}")
                    if f.attr in GOI_DONG:
                        dg.add(f.attr)
            # Import cục bộ trong thân hàm: `_bi_danh` đã quét CẢ cây nên bí
            # danh của chúng có mặt — cố ý, vì một `import` trong thân hàm là
            # cách rẻ nhất để giấu một cạnh khỏi phép dò chỉ đọc đầu tệp.
    return canh, dong


def lan_toi(canh: dict, goc: set) -> dict:
    """`{đích với tới được: đường đi}` từ tập `goc`."""
    duong = {g: [g] for g in goc}
    hang = deque(goc)
    while hang:
        k = hang.popleft()
        for t in canh.get(k, ()):  # type: ignore[union-attr]
            if t not in duong:
                duong[t] = duong[k] + [t]
                hang.append(t)
    return duong


def _goc_supervisor() -> set:
    from platform_core.agent import supervisor
    mod = "platform_core.agent.supervisor"
    return ({f"{mod}:{f.__name__}" for f in supervisor.HANH_DONG.values()}
            | {f"{mod}:lam", f"{mod}:quet"})


GOC_SOAN = {"platform_core.agent.ke_hoach_v3:soan_draft",
            "platform_core.agent.ke_hoach_v3:chuan_hoa",
            "platform_core.agent.ke_hoach_v3:kiem"}


# ── 1. Phép dò có THẤY GÌ không (⛔ không đo trên một đồ thị rỗng) ───────────

def test_doi_chung_do_thi_goi_KHONG_rong():
    canh, _dong = do_thi_goi(nap_nguon())
    assert len(canh) > 500, f"chi doc duoc {len(canh)} ham -- doc nham cho?"
    goc = _goc_supervisor()
    assert len(goc) == 6
    duong = lan_toi(canh, goc)
    # Supervisor CÓ gọi ra ngoài: nếu tập với tới được chỉ bằng chính nó thì
    # phép dò đang mù, và "không tới được hàm cấm" là một câu nói rỗng.
    assert len(duong) > 20, sorted(duong)
    assert "platform_core.workflow.may_trang_thai:chuyen_node" in duong


def test_moi_dia_chi_trong_CAM_la_mot_ham_CO_THAT():
    """🔑 Một địa chỉ gõ sai thì không bao giờ với tới được, và bánh cóc xanh
    vĩnh viễn. Đối chiếu với `ast` của chính tệp ấy."""
    nguon = nap_nguon()
    for dia_chi in CAM:
        mod, ten = dia_chi.split(":")
        assert mod in nguon, dia_chi
        assert ten in _dinh_nghia_trong(ast.parse(nguon[mod])), dia_chi


# ── 2. 🔴 MỆNH ĐỀ CHÍNH ─────────────────────────────────────────────────────

def test_hanh_dong_CAM_khong_co_duong_goi_tu_supervisor():
    canh, _dong = do_thi_goi(nap_nguon())
    duong = lan_toi(canh, _goc_supervisor())
    cham = {d: duong[d] for d in CAM if d in duong}
    assert not cham, "\n".join(
        f"{d} ({CAM[d]}) qua: " + " -> ".join(p) for d, p in cham.items())


def test_cua_soan_draft_KHONG_publish():
    """§12.2: *"Agent không publish: nó ghi draft, người dùng bấm publish"*."""
    canh, _dong = do_thi_goi(nap_nguon())
    duong = lan_toi(canh, GOC_SOAN)
    cham = {d: duong[d] for d in CAM if d in duong}
    assert not cham, "\n".join(
        f"{d} ({CAM[d]}) qua: " + " -> ".join(p) for d, p in cham.items())


def test_khong_goi_DONG_trong_tap_voi_toi_duoc_cua_supervisor():
    """Bịt lối thoát của chính phép đo: `getattr`/`eval`/`exec`/`__import__`."""
    canh, dong = do_thi_goi(nap_nguon())
    duong = lan_toi(canh, _goc_supervisor())
    xau = {k: sorted(dong[k]) for k in duong if dong.get(k)}
    assert not xau, xau


def test_khong_SQL_tho_trong_supervisor():
    """`UPDATE workflow_version …` viết tay không đi qua hàm nào trong `CAM`."""
    ma = (GOC / "agent" / "supervisor.py").read_text(encoding="utf-8")
    for n in ast.walk(ast.parse(ma)):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            v = n.value.upper()
            assert not any(k in v for k in ("UPDATE ", "INSERT ", "DELETE ")), \
                n.value[:120]


# ── 3. ⭐ BÁNH CÓC PHẢI CẮN — tiêm lỗi ───────────────────────────────────────

@pytest.mark.parametrize("tiem,dia_chi", [
    ("    from platform_core.workflow import tien\n"
     "    tien.giu_cho_run(db, run)\n",
     "platform_core.workflow.tien:giu_cho_run"),
    ("    from platform_core.workflow import dinh_nghia\n"
     "    dinh_nghia.xuat_ban(db, '', {}, created_by='')\n",
     "platform_core.workflow.dinh_nghia:xuat_ban"),
    ("    from platform_core import api_keys\n"
     "    api_keys.dat_credential(db, None, '')\n",
     "platform_core.api_keys:dat_credential"),
])
def test_banh_coc_CAN_khi_tiem_mot_loi_gia(tiem, dia_chi):
    """Bản `supervisor.py` bị sửa TRONG BỘ NHỚ ⇒ phép dò phải báo đúng địa chỉ.

    ⛔ Không ghi vào cây: một bánh cóc chỉ đáng tin khi nó bắt được lỗi, và
       cách chứng minh điều đó là tiêm lỗi — không phải chạy lại nó.
    """
    mod = "platform_core.agent.supervisor"
    ma = (GOC / "agent" / "supervisor.py").read_text(encoding="utf-8")
    moc = "    wp = cho_doi.tao_waitpoint("
    assert moc in ma, "mo-dun doi hinh: sua diem tiem"
    hong = ma.replace(moc, tiem + moc, 1)

    canh, _dong = do_thi_goi(nap_nguon({mod: hong}))
    duong = lan_toi(canh, {f"{mod}:hoi_nguoi"})
    assert dia_chi in duong, f"banh coc KHONG can: {dia_chi} van khong thay"

    # 🔑 Vế đối chứng: bản THẬT không có cạnh ấy.
    canh2, _d2 = do_thi_goi(nap_nguon())
    assert dia_chi not in lan_toi(canh2, {f"{mod}:hoi_nguoi"})


def test_banh_coc_CAN_qua_MOT_TANG_TRUNG_GIAN():
    """Tiêm gián tiếp: `hoi_nguoi` -> một hàm mới -> hàm cấm. Nếu phép dò chỉ
    nhìn MỘT tầng thì nó xanh ở đây, và như thế là vô dụng."""
    mod = "platform_core.agent.supervisor"
    ma = (GOC / "agent" / "supervisor.py").read_text(encoding="utf-8")
    moc = "    wp = cho_doi.tao_waitpoint("
    hong = ma.replace(moc, "    _len_tay(db, run)\n" + moc, 1)
    hong += ("\n\ndef _len_tay(db, run):\n"
             "    from platform_core.workflow import tien\n"
             "    return tien.giu_cho_run(db, run)\n")
    canh, _dong = do_thi_goi(nap_nguon({mod: hong}))
    duong = lan_toi(canh, {f"{mod}:hoi_nguoi"})
    assert "platform_core.workflow.tien:giu_cho_run" in duong
    assert len(duong["platform_core.workflow.tien:giu_cho_run"]) == 3
