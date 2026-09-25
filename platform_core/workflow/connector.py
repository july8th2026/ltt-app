"""Cầu nối Python ⇄ **runner connector** (spec §11.1).

Một lệnh = một tiến trình Node, chạy **bên trong AppContainer** (`vo_boc.py`),
ra Internet **chỉ** qua proxy lọc miền (`proxy_egress.py`), có trần bộ nhớ và
`KILL_ON_JOB_CLOSE` (`job_object.py`).

```
    Python (worker)                      AppContainer, 0 capability mang
    ┌──────────────────┐                ┌──────────────────────────────┐
    │ connector.chay() │  vao.json ───▶ │ node src/runner.js           │
    │  proxy_egress ◀──┼── 127.0.0.1 ──┼─ HTTPS CONNECT (loc mien)     │
    │                  │  ◀─── ra.json  │ action.run(ctx)              │
    └──────────────────┘                └──────────────────────────────┘
```

## ⛔ Ba chỗ cố ý lệch spec, mỗi chỗ vì một phép ĐO

1. **Tệp thay cho stdin/stdout** (§11.1). Ống treo cứng trong AppContainer.
2. **Job Object không phải lớp mạng** (§11.2). Nó không lọc socket; ranh giới
   là AppContainer. Spec xếp nhầm vai.
3. **Egress hợp lệ đi qua proxy loopback**, không phải undici dispatcher
   (§11.2). Dispatcher chỉ chặn `fetch()`, để lọt `require('https')` và axios —
   tức để lọt phần lớn SDK của piece.

## Tiền và sổ sách

⛔ Mô-đun này **không** chạm sổ credit. Nó nhận tham số, chạy, trả kết quả.
Việc giữ/nhả tiền nằm ở `cau_noi.py` + `ket_so.py` như mọi node job khác — hai
nơi ghi sổ là đúng hình dạng lỗi "chi phí run con biến mất" đã đo ở phase 4.
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import time
import uuid
from dataclasses import dataclass, field

from platform_core.workflow import job_object, proxy_egress, vo_boc

GOC = pathlib.Path(__file__).resolve().parents[2]

#: Thư mục runner. Trên máy chủ nó nằm trong `app\` (bị thay TOÀN BỘ mỗi lần
#: cập nhật) — nên ⛔ không bao giờ ghi gì vào đây lúc chạy.
THU_MUC_RUNNER = pathlib.Path(
    os.environ.get("LTT_CONNECTOR_RUNNER", str(GOC / "connector_runner")))

#: Thư mục marketplace — NGOÀI `THU_MUC_RUNNER` cố ý (spec plan wfm 25/09).
#: Đây là nơi DUY NHẤT `platform_core/workflow/marketplace.py::cai_dat()`
#: được phép ghi allowlist/catalog/piece đã cài; nó nằm dưới `data/`, thư
#: mục sống sót qua deploy (⛔ khác `THU_MUC_RUNNER`, bị thay TOÀN BỘ mỗi lần
#: cập nhật — ghi allowlist marketplace ở đó thì piece vừa duyệt biến mất
#: sau bản cập nhật kế tiếp mà không ai báo).
THU_MUC_MARKETPLACE = pathlib.Path(
    os.environ.get("LTT_MARKETPLACE_DIR", str(GOC / "data" / "marketplace")))

#: Nơi đặt bản chép `node.exe` + thư mục tạm của từng lệnh. ⭐ Phải nằm ngoài
#: `C:\Program Files`: vỏ cần ACL đọc trên tệp `node.exe`, và ⛔ cấp ACL trong
#: `Program Files` là sửa quyền của một thư mục hệ thống (CLAUDE.md).
THU_MUC_LAM_VIEC = pathlib.Path(
    os.environ.get("LTT_CONNECTOR_TMP", str(GOC / "data" / "conn")))

#: Hạn giờ cứng (spec §11.2): `han_ms` của lệnh + biên, giết cứng ở 120 s.
HAN_CUNG_MS = 120_000
HAN_MAC_DINH_MS = 110_000


class LoiConnector(RuntimeError):
    """Runner không chạy được / trả sai hình dạng. ⛔ Khác hẳn *piece* báo lỗi:
    cái sau là `{"ok": false}` và là một kết quả hợp lệ của giao thức."""


@dataclass
class KetQua:
    ok: bool
    output: object = None
    store_ops: list = field(default_factory=list)
    files: list = field(default_factory=list)
    logs: list = field(default_factory=list)
    ma_loi: str = ""
    thong_diep: str = ""
    status: int = 0
    #: Số đo của lượt chạy (RAM đỉnh, CPU, độ trễ) — dùng cho `bench/` và cho
    #: nghiệm thu tải, ⛔ không phải để hiển thị cho khách.
    do: dict = field(default_factory=dict)


def _doc_allowlist_tinh() -> dict:
    with open(THU_MUC_RUNNER / "allowlist.json", encoding="utf-8") as f:
        return json.load(f)


def _doc_allowlist_marketplace() -> dict:
    """Allowlist marketplace — spec `platform_core/workflow/marketplace.py`.

    ⭐ Thiếu tệp ⇒ rỗng, không ném: chưa có piece marketplace nào được duyệt
       là trạng thái BÌNH THƯỜNG (fail closed đến từ chỗ tệp CHỈ được ghi bởi
       `marketplace.cai_dat()` SAU khi qua hết cổng duyệt, không phải từ chỗ
       thiếu tệp gây lỗi khởi động).
    """
    tep = THU_MUC_MARKETPLACE / "allowlist.json"
    if not tep.exists():
        return {"pieces": {}, "mien": {}, "palette": {}}
    with open(tep, encoding="utf-8") as f:
        return json.load(f)


def _doc_allowlist() -> dict:
    """Allowlist GỘP: tĩnh (đã review, `THU_MUC_RUNNER`) ⊕ marketplace (đã
    qua cổng duyệt runtime, `THU_MUC_MARKETPLACE`). Cùng luật với
    `connector_runner/src/piece_nap.js::docAllowlist()` — ⛔ một tên piece có
    mặt ở CẢ HAI nguồn là lỗi cấu hình, ném ngay, không để một bên âm thầm
    thắng.
    """
    tinh = _doc_allowlist_tinh()
    mkt = _doc_allowlist_marketplace()
    trung = set(mkt.get("pieces") or {}) & set(tinh.get("pieces") or {})
    if trung:
        raise LoiConnector(
            f"piece trung ten tinh va marketplace: {sorted(trung)}")
    return {
        "pieces": {**tinh.get("pieces", {}), **(mkt.get("pieces") or {})},
        "mien": {**tinh.get("mien", {}), **(mkt.get("mien") or {})},
        "palette": {**tinh.get("palette", {}), **(mkt.get("palette") or {})},
    }


def _doc_catalog_tep(tep: pathlib.Path) -> list:
    if not tep.exists():
        return []
    with open(tep, encoding="utf-8") as f:
        return list(json.load(f).get("nodes") or [])


def doc_catalog() -> list:
    """Mục catalog cho `nut.NGUON_PIECE`: tĩnh ⊕ marketplace. Thiếu tệp ⇒
    danh sách rỗng cho phần đó.

    ⭐ Rỗng chứ không ném: `catalog.json` sinh lúc build, và một máy dev chưa
       chạy `npm install` vẫn phải khởi động được — cùng lý do, catalog
       marketplace chỉ tồn tại sau lượt duyệt đầu tiên. Nhưng ⛔ **không** nuốt
       lỗi cú pháp — một catalog hỏng phải nổ lúc khởi động, không im lặng
       thành "palette không có connector nào".
    """
    return (_doc_catalog_tep(THU_MUC_RUNNER / "catalog.json")
            + _doc_catalog_tep(THU_MUC_MARKETPLACE / "catalog.json"))


def mien_cua_piece(piece: str) -> tuple:
    """Miền `piece` được phép nối tới. ⛔ Không có mục ⇒ **rỗng**, tức chặn
    hết — fail **closed**. Một piece thiếu khai miền phải hỏng ầm ĩ lúc chạy
    thử, không được lặng lẽ có toàn quyền ra Internet."""
    if piece == "@ltt/piece-gia":
        return ()
    return tuple((_doc_allowlist().get("mien") or {}).get(piece) or ())


def node_exe() -> pathlib.Path:
    """Bản chép `node.exe` trong thư mục làm việc (vỏ cần ACL đọc trên nó).

    ⭐ Công khai (không tiền tố `_`): `code_sandbox.py` dùng chung đúng bản
       chép này — cùng `THU_MUC_LAM_VIEC`, cùng lý do (vỏ cần ACL đọc trên nó).
    """
    nguon = os.environ.get("LTT_NODE_EXE") or shutil.which("node")
    if not nguon:
        raise LoiConnector("khong tim thay node.exe (dat LTT_NODE_EXE)")
    dich = THU_MUC_LAM_VIEC / "node.exe"
    nguon_p = pathlib.Path(nguon)
    if (not dich.exists()
            or dich.stat().st_size != nguon_p.stat().st_size):
        THU_MUC_LAM_VIEC.mkdir(parents=True, exist_ok=True)
        shutil.copy2(nguon_p, dich)
    return dich


_DA_CAP_ACL: set = set()


def chuan_bi_vo(ten_vo: str = vo_boc.TEN_VO_MAC_DINH) -> str:
    """Tạo vỏ, cấp ACL, mở loopback. Luỹ đẳng; gọi một lần mỗi tiến trình.

    🔴 Loopback **bắt buộc**: không có nó, mọi lệnh connector sẽ hết giờ ở
       130 s thay vì chạy. Đo 24/09: trong vỏ chưa miễn trừ,
       `connect 127.0.0.1` trả `ETIMEDOUT`; miễn trừ xong trả 200. Miễn trừ
       **không** mở Internet — cùng lượt đo, `https://example.com` vẫn TIMEOUT.
    """
    sid = vo_boc.sid_cua_vo(ten_vo)
    if sid in _DA_CAP_ACL:
        return sid
    THU_MUC_LAM_VIEC.mkdir(parents=True, exist_ok=True)
    node_exe()
    vo_boc.cap_acl(str(THU_MUC_RUNNER), sid, "(OI)(CI)(RX)")
    vo_boc.cap_acl(str(THU_MUC_LAM_VIEC), sid, "(OI)(CI)(M)")
    if not vo_boc.ap_dung_loopback(sid):
        raise LoiConnector(
            "khong mo duoc mien tru loopback cho vo (can quyen quan tri): "
            "thieu no thi moi lenh connector se HET GIO, khong phai chay cham")
    _DA_CAP_ACL.add(sid)
    return sid


def go_vo(ten_vo: str = vo_boc.TEN_VO_MAC_DINH) -> None:
    """Gỡ sạch: ACL + miễn trừ loopback + hồ sơ vỏ. Lệnh gỡ của báo cáo."""
    sid = vo_boc.sid_cua_vo(ten_vo)
    vo_boc.go_loopback(sid)
    vo_boc.go_acl(str(THU_MUC_RUNNER), sid)
    vo_boc.go_acl(str(THU_MUC_LAM_VIEC), sid)
    vo_boc.xoa_vo(ten_vo)
    _DA_CAP_ACL.discard(sid)


def chay(op: str, *, piece: str, version: str, name: str,
         props=None, auth=None, store=None, han_ms: int = HAN_MAC_DINH_MS,
         prop: str = "", run_id: str = "", public_url: str = "",
         ten_vo: str = vo_boc.TEN_VO_MAC_DINH, moi_truong_them=None,
         giu_tmp: bool = False) -> KetQua:
    """Một lệnh connector. Luôn dọn `tmp_dir`, kể cả khi ném.

    `giu_tmp=True` giữ lại thư mục tạm (gồm `log.txt` — **stdout/stderr thật
    của tiến trình trong vỏ**). ⛔ Chỉ dùng để chẩn đoán và cho phép đo nghiệm
    thu: mã piece ghi được vào thư mục đó, nên giữ nó trên đường production là
    để lại rác mà bên thứ ba kiểm soát nội dung.
    """
    bat_dau = time.monotonic()
    chuan_bi_vo(ten_vo)
    tmp = THU_MUC_LAM_VIEC / f"j-{uuid.uuid4().hex[:16]}"
    # ⛔ KHÔNG `cap_acl` cho từng thư mục lệnh. `THU_MUC_LAM_VIEC` đã được cấp
    #    `(OI)(CI)(M)` — hai cờ ấy nghĩa là **kế thừa cho thư mục con và tệp
    #    con**, nên một thư mục mới tạo bên trong đã có đúng quyền.
    #
    # 🔴 Đo 24/09, và nó là một con số đáng nhớ: một lượt `icacls` tốn **~430
    #    ms**, tức **83 %** độ trễ của cả lệnh (518 ms → 88 ms sau khi bỏ). Một
    #    dòng "cho chắc" đắt gấp năm lần toàn bộ việc thật — và nó không mua
    #    thêm quyền nào.
    tmp.mkdir(parents=True)
    pr = proxy_egress.mo(mien_cua_piece(piece))
    try:
        yc = {
            "op": op, "piece": piece, "version": version, "name": name,
            "props": props or {}, "auth": auth, "store": store or {},
            "tmp_dir": str(tmp), "han_ms": int(han_ms), "prop": prop,
            "run_id": run_id, "public_url": public_url,
            "proxy_port": pr.cong,
        }
        (tmp / "vao.json").write_text(json.dumps(yc), encoding="utf-8")
        moi = vo_boc.moi_truong_toi_thieu(proxy=pr.url, them=moi_truong_them)
        kq = vo_boc.chay(
            # 🔴 CẢ HAI cờ symlink, ⛔ không chỉ `--preserve-symlinks-main`.
            #    Đo 24/09: chỉ cờ `-main` thì module CHÍNH nạp được, nhưng
            #    `require('./piece_nap')` vẫn đi qua `realpath` và chết
            #    `EPERM: lstat 'D:'` — vỏ không đọc được gốc ổ đĩa, và nó
            #    KHÔNG được đọc. Spike P6B chỉ chạy tệp đơn nên không gặp.
            [str(THU_MUC_LAM_VIEC / "node.exe"), "--preserve-symlinks",
             "--preserve-symlinks-main",
             str(THU_MUC_RUNNER / "src" / "runner.js"),
             str(tmp / "vao.json"), str(tmp / "ra.json")],
            ra_log=str(tmp / "log.txt"), ten_vo=ten_vo,
            moi_truong=moi,
            han_ms=min(int(han_ms) + 5_000, HAN_CUNG_MS),
            bo_nho_mb=job_object.BO_NHO_MAC_DINH_MB,
            thu_muc=str(THU_MUC_RUNNER))
        do = dict(kq.so_lieu)
        do["do_tre_ms"] = int((time.monotonic() - bat_dau) * 1000)
        do["mien_da_qua"] = list(pr.chinh_sach.da_qua)
        do["mien_bi_chan"] = list(pr.chinh_sach.da_chan)
        log = ""
        try:
            log = (tmp / "log.txt").read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
        if kq.het_gio:
            return KetQua(ok=False, ma_loi="het_gio", do=do,
                          thong_diep=f"runner bi giet sau {han_ms} ms",
                          logs=[log[-2000:]] if log else [])
        try:
            ra = json.loads((tmp / "ra.json").read_text(encoding="utf-8"))
        except (OSError, ValueError) as loi:
            # ⛔ Không đoán "chắc là lỗi provider": runner không ghi được
            #    `ra.json` là lỗi CỦA TA, và log của tiến trình là bằng chứng
            #    duy nhất còn lại.
            raise LoiConnector(
                f"runner khong tra ra.json (exit={kq.ma_thoat}): {loi}; "
                f"log={log[-800:]!r}") from loi
        if ra.get("ok"):
            return KetQua(ok=True, output=ra.get("output"),
                          store_ops=list(ra.get("store_ops") or []),
                          files=list(ra.get("files") or []),
                          logs=list(ra.get("logs") or []), do=do)
        loi_d = dict(ra.get("error") or {})
        return KetQua(ok=False, ma_loi=str(loi_d.get("ma") or "provider_loi"),
                      thong_diep=str(loi_d.get("thong_diep") or ""),
                      status=int(loi_d.get("status") or 0),
                      store_ops=list(ra.get("store_ops") or []),
                      logs=list(ra.get("logs") or []), do=do)
    finally:
        pr.dung()
        # `tmp_dir` xoá sau MỖI lệnh (spec §11.2). Mã piece ghi được vào đây.
        if not giu_tmp:
            shutil.rmtree(tmp, ignore_errors=True)


#: Tên tham số JOB mang **ref** credential của khách (spec §9.4). ⛔ Không
#: phải bí mật: ref là một id, chỗ duy nhất giải mã nó là tiến trình job
#: (`apps/connector_runner/jobs.py::_bi_mat`).
#:
#: ⭐ Hằng đặt Ở ĐÂY, không phải trong `apps/connector_runner/jobs.py`: cả
#:    hai phía của hợp đồng đọc nó — `cau_noi._nop_job_connector` (GHI, nộp
#:    job) và `jobs.handle` (ĐỌC, giải mã). `apps/` được phép import
#:    `platform_core/`, chiều ngược lại thì không — nên hằng phải sống ở
#:    `platform_core/` và `jobs.py` import nó, không phải khai tay hai lần
#:    một chuỗi `"credential"` ở hai đầu một job param.
THAM_SO_CREDENTIAL = "credential"

__all__ = ["HAN_CUNG_MS", "HAN_MAC_DINH_MS", "KetQua", "LoiConnector",
           "THAM_SO_CREDENTIAL", "THU_MUC_LAM_VIEC", "THU_MUC_MARKETPLACE",
           "THU_MUC_RUNNER", "chay", "chuan_bi_vo", "doc_catalog", "go_vo",
           "mien_cua_piece", "node_exe"]
