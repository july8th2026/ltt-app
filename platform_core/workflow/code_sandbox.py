"""Cầu nối Python ⇄ **lớp thứ hai** cho `core.code` — spec P-D mục 2.

⛔ **Node `core.code` CHƯA đăng ký** (prompt gốc §33: không đưa Code Node vào
   early phase khi sandbox chưa xong). Mô-đun này chỉ dựng và ĐO cái vỏ; không
   có đường nào từ `cau_noi.py` gọi tới đây.

## Hai lớp, không phải một

```
    AppContainer (vo_boc.py)        <- RANH GIỚI. Đo 24/09, có đối chứng.
      └── tiến trình Node runner
            └── isolated-vm Isolate <- LỚP SIẾT THÊM, KHÔNG phải ranh giới.
                  (code_sandbox.js)    Lịch sử CVE của sandbox JS trong-tiến-
                                       trình dài (`vm2` CVSS 10.0; `isolated-
                                       vm`/`vm` của n8n sau khi bỏ `vm2` vẫn
                                       dính CVE-2026-25049). Coi nó ngang một
                                       piece có thể bị vượt qua.
```

⭐ Vì vậy mọi lệnh gọi ở đây đi qua **`vo_boc.chay`** y hệt một piece — cùng
   ACL, cùng Job Object, cùng (không) capability mạng. `code_sandbox.js` chỉ
   thêm: hạn thực thi ĐỒNG BỘ chặt hơn (mili-giây, không phải giây) và một
   trần bộ nhớ V8 riêng, tách khỏi `--max-old-space-size` của tiến trình
   ngoài.

## Vỏ RIÊNG cho code, không dùng chung với `ltt-connector-runner`

`TEN_VO_CODE` là một hồ sơ AppContainer khác — mã người dùng tự viết là một
mức tin cậy khác hẳn một piece đã qua allowlist. Vỏ này **không** có domain
nào được phép: `chay()` ở đây **không** mở `proxy_egress` (khác
`connector.chay`, luôn mở một `DangChay`). Không có proxy nghĩa là biến môi
trường `HTTPS_PROXY` không tồn tại — Node 24 (`NODE_USE_ENV_PROXY=1`) không
có gì để đi theo, và mọi lưu lượng mạng (nếu isolate có cách nào đó chạm tới
`net`/`https`, thứ nó **không nên** chạm được vì `require` không tồn tại
trong isolate) rơi thẳng vào AppContainer.
"""
from __future__ import annotations

import json
import shutil
import time
import uuid
from dataclasses import dataclass, field

from platform_core.workflow import connector, job_object, vo_boc

#: Hồ sơ AppContainer riêng cho code — KHÔNG dùng chung với piece runner.
TEN_VO_CODE = "ltt-code-runner"

#: Trần bộ nhớ ISOLATE (V8 heap riêng, không phải job object). §11.2 dùng
#: 512 MB cho tiến trình ngoài; con số ở đây phải NHỎ hơn hẳn — nó là hạn mức
#: cho một script thuần, không phải cho cả runtime Node + SDK piece.
BO_NHO_ISOLATE_MAC_DINH_MB = 128

#: Hạn thực thi ĐỒNG BỘ bên trong isolate — mili-giây. ⛔ Không nhầm với
#: `han_ms` của `vo_boc.chay` (thời gian TRÔI của cả tiến trình): tham số
#: này là `timeout` của `isolate.compileScript(...).run()`, đo bởi chính V8,
#: và nó cắt được một `while(true){}` mà không cần đợi tới hạn giờ ngoài.
HAN_ISOLATE_MAC_DINH_MS = 8_000


class LoiCodeSandbox(RuntimeError):
    """Runner code không chạy được / trả sai hình dạng."""


@dataclass
class KetQuaCode:
    ok: bool
    output: object = None
    ma_loi: str = ""
    thong_diep: str = ""
    do: dict = field(default_factory=dict)


_DA_CAP_ACL: set = set()


def chuan_bi_vo_code(ten_vo: str = TEN_VO_CODE) -> str:
    """Tạo vỏ RIÊNG cho code, cấp ACL, mở loopback. Luỹ đẳng.

    ⭐ Loopback vẫn cần dù `chay()` không mở proxy egress: `vo_boc.chay` không
       biết trước một lệnh có định gọi loopback hay không, và vỏ chưa miễn
       trừ loopback thì MỌI thao tác cần 127.0.0.1 (kể cả của chính hạ tầng
       đo, nếu có sau này) sẽ hết giờ ở 130 s thay vì chạy nhanh.
    """
    sid = vo_boc.sid_cua_vo(ten_vo)
    if sid in _DA_CAP_ACL:
        return sid
    connector.THU_MUC_LAM_VIEC.mkdir(parents=True, exist_ok=True)
    connector.node_exe()  # cùng bản chép node.exe với connector (dùng chung thư mục)
    vo_boc.cap_acl(str(connector.THU_MUC_RUNNER), sid, "(OI)(CI)(RX)")
    vo_boc.cap_acl(str(connector.THU_MUC_LAM_VIEC), sid, "(OI)(CI)(M)")
    if not vo_boc.ap_dung_loopback(sid):
        raise LoiCodeSandbox(
            "khong mo duoc mien tru loopback cho vo code (can quyen quan tri)")
    _DA_CAP_ACL.add(sid)
    return sid


def go_vo_code(ten_vo: str = TEN_VO_CODE) -> None:
    sid = vo_boc.sid_cua_vo(ten_vo)
    vo_boc.go_loopback(sid)
    vo_boc.go_acl(str(connector.THU_MUC_RUNNER), sid)
    vo_boc.go_acl(str(connector.THU_MUC_LAM_VIEC), sid)
    vo_boc.xoa_vo(ten_vo)
    _DA_CAP_ACL.discard(sid)


def chay(nguon: str, inputs: dict | None = None, *,
         han_isolate_ms: int = HAN_ISOLATE_MAC_DINH_MS,
         bo_nho_isolate_mb: int = BO_NHO_ISOLATE_MAC_DINH_MB,
         han_ms: int = connector.HAN_MAC_DINH_MS,
         ten_vo: str = TEN_VO_CODE, moi_truong_them=None,
         giu_tmp: bool = False) -> KetQuaCode:
    """Chạy `nguon` (module CJS, `module.exports.code = function(inputs){}`)
    trong vỏ code. ⛔ **Không** mở `proxy_egress` — code không có domain nào
    được phép, nên không có gì để cấu hình cho một proxy egress.
    """
    bat_dau = time.monotonic()
    chuan_bi_vo_code(ten_vo)
    tmp = connector.THU_MUC_LAM_VIEC / f"c-{uuid.uuid4().hex[:16]}"
    tmp.mkdir(parents=True)
    try:
        yc = {
            "op": "run_code", "code": str(nguon), "props": inputs or {},
            "code_han_ms": int(han_isolate_ms),
            "code_bo_nho_mb": int(bo_nho_isolate_mb),
            "tmp_dir": str(tmp), "han_ms": int(han_ms),
        }
        (tmp / "vao.json").write_text(json.dumps(yc), encoding="utf-8")
        # ⛔ KHONG `proxy=` — xem docstring mo-dun. moi_truong_toi_thieu() vẫn
        # là nguồn DUY NHẤT của môi trường: không kế thừa bí mật của worker.
        moi = vo_boc.moi_truong_toi_thieu(them=moi_truong_them)
        kq = vo_boc.chay(
            [str(connector.THU_MUC_LAM_VIEC / "node.exe"), "--preserve-symlinks",
             "--preserve-symlinks-main",
             str(connector.THU_MUC_RUNNER / "src" / "runner.js"),
             str(tmp / "vao.json"), str(tmp / "ra.json")],
            ra_log=str(tmp / "log.txt"), ten_vo=ten_vo, moi_truong=moi,
            han_ms=min(int(han_ms) + 5_000, connector.HAN_CUNG_MS),
            bo_nho_mb=job_object.BO_NHO_MAC_DINH_MB,
            thu_muc=str(connector.THU_MUC_RUNNER))
        do = dict(kq.so_lieu)
        do["do_tre_ms"] = int((time.monotonic() - bat_dau) * 1000)
        log = ""
        try:
            log = (tmp / "log.txt").read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
        if kq.het_gio:
            return KetQuaCode(ok=False, ma_loi="het_gio", do=do,
                              thong_diep=f"runner code bi giet sau {han_ms} ms "
                                         f"(vo AppContainer, khac han isolate "
                                         f"{han_isolate_ms} ms)")
        try:
            ra = json.loads((tmp / "ra.json").read_text(encoding="utf-8"))
        except (OSError, ValueError) as loi:
            raise LoiCodeSandbox(
                f"runner code khong tra ra.json (exit={kq.ma_thoat}): {loi}; "
                f"log={log[-800:]!r}") from loi
        if ra.get("ok"):
            return KetQuaCode(ok=True, output=ra.get("output"), do=do)
        loi_d = dict(ra.get("error") or {})
        return KetQuaCode(ok=False, ma_loi=str(loi_d.get("ma") or "provider_loi"),
                          thong_diep=str(loi_d.get("thong_diep") or ""), do=do)
    finally:
        if not giu_tmp:
            shutil.rmtree(tmp, ignore_errors=True)


__all__ = ["BO_NHO_ISOLATE_MAC_DINH_MB", "HAN_ISOLATE_MAC_DINH_MS",
           "KetQuaCode", "LoiCodeSandbox", "TEN_VO_CODE", "chay",
           "chuan_bi_vo_code", "go_vo_code"]
