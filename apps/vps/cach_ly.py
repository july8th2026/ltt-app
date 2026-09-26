"""Cửa chặn bán cho KHÁCH THỨ HAI khi node chưa thật sự cách ly khách với khách.

## Vì sao có tệp này

Đo 25-26/09/2026: `ipfilter`/`macfilter` đặt trên từng VM là **no-op**, vì Proxmox
đòi một phép AND ba tầng (`cluster/firewall/options.enable`, cờ `firewall=1` trên
NIC, `qemu/<id>/firewall/options.enable`) và **hai tầng đang tắt**. ⇒ Không có lớp
nào chặn khách A giả mạo IP/MAC của khách B trên cùng bridge.

Và đo tiếp: node hiện có 2 máy, **cùng một chủ**. ⇒ Mọi rủi ro đó là rủi ro **giữa
các khách**, nên hôm nay chúng chưa tồn tại. Chúng bật lên đúng lúc **một khách lạ
đầu tiên** có máy trên cùng node.

⇒ Cái mốc đúng ⛔ không phải *"bật tường lửa ngay"* — làm vậy là ngắt máy chủ dự án
  đang làm việc, cho một rủi ro chưa có, và `ipfilter` với một ipset rỗng **cắt
  mạng máy khách** (tài liệu Proxmox: *"equivalent to adding an **empty**
  `ipfilter-net<id>` ipset"*, và IP chỉ được tự thêm cho **container**).

  Mốc đúng là: ⛔ **không được có khách thứ hai trong lúc còn hở.**

🔴 Và nó phải **cơ học**. Một việc "cần làm trước khi có khách thật" mà chỉ nằm
   trong đầu người hoặc trong một tệp kế hoạch thì **sẽ** bị quên — đúng lúc nó quan
   trọng nhất, vì lúc ấy ta đang mừng vì có khách mới.

## ⚠️ Cửa này ⛔ không chứng minh rằng cách ly HOẠT ĐỘNG

Nó chỉ trả lời *"ba tầng đã bật chưa"*. Đó là điều kiện **cần**, ⛔ chưa phải điều
kiện đủ: chính Proxmox thừa nhận một lỗi *"packets sometimes passing"* qua bộ lọc,
vá ở tầng kernel netfilter 11/09/2025 và đang backport (diễn đàn Proxmox, luồng
155335). Và một ca thật 10/2024 trong cùng luồng cho thấy với `policy_in: ACCEPT`
thì `ipfilter` **không filter** — phải `policy_in: DROP` cộng một luật tường minh
tới `+ipfilter-net0`.

⇒ Trước khi tuyên bố với khách rằng máy được cách ly, phải có **một phép thử giữa
  hai máy thật**. Cửa này chỉ ngăn ta bán trong lúc điều kiện cần còn chưa có.
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)

#: Câu mở đầu lý do khi ta **không đo được**. Tách khỏi lý do "đã đo và còn hở" vì
#: hai thứ đó đòi hai hành động khác nhau: một cái đi bật tường lửa, một cái đi
#: xem vì sao không hỏi được Proxmox.
CHUA_DO_DUOC = "khong do duoc"


def _so_may_theo_chu(db, profile_id: str) -> dict[str, list[int]]:
    from sqlalchemy import select

    from apps.vps.tables import VpsInstance

    ra: dict[str, list[int]] = {}
    for may in db.execute(select(VpsInstance).where(
            VpsInstance.infrastructure_profile_id == profile_id)).scalars():
        if str(getattr(may, "trang_thai", "")) == "da_xoa":
            continue
        ra.setdefault(str(may.user_id), []).append(int(may.vmid or 0))
    return ra


def chan_khach_moi(db, profile, user_id: str, *, do_hieu_luc) -> tuple[bool, str]:
    """`(chan, ly_do)` — có chặn lượt tạo máy này không.

    `do_hieu_luc(vmid) -> (hieu_luc, ly_do_ho)`: thường là
    `functools.partial(proxmox.tuong_lua_hieu_luc, client)`.

    Chặn **chỉ khi cả ba** điều sau đúng:

    1. `user_id` **chưa có** máy nào trên hồ sơ này (tức là một khách MỚI ở đây);
    2. đã có **ít nhất một** máy của một chủ **khác**;
    3. một trong các máy đang có **chưa** ở trạng thái cách ly hiệu lực — hoặc ta
       **không đo được** điều đó.

    ⛔ Chủ hiện tại ⛔ không bị chặn: rủi ro là cross-tenant, và một chủ thêm máy
       thứ ba của chính mình ⛔ không tạo ra khách thứ hai nào. Chặn họ vì một lỗi
       đo là làm hại người không liên quan.
    """
    try:
        theo_chu = _so_may_theo_chu(db, getattr(profile, "id", ""))
    except Exception as exc:                  # noqa: BLE001 - xem docstring cuoi ham
        # Cua nay nam tren duong ban. Mot ngoai le lot ra la mot trang 500 cho
        # khach thay vi mot cau giai thich.
        log.warning("VPS cach ly: khong dem duoc may theo chu (%s)",
                    type(exc).__name__)
        return True, f"{CHUA_DO_DUOC}: khong dem duoc may tren node"

    if str(user_id) in theo_chu:
        return False, ""                      # chu hien tai
    may_nguoi_khac = [v for chu, ds in theo_chu.items() if chu != str(user_id)
                      for v in ds]
    if not may_nguoi_khac:
        return False, ""                      # node trong

    ho: list[str] = []
    for vmid in sorted(may_nguoi_khac):
        try:
            hieu_luc, ly_do = do_hieu_luc(vmid)
        except Exception as exc:              # noqa: BLE001
            log.warning("VPS cach ly: khong do duoc tuong lua vm %s (%s)",
                        vmid, type(exc).__name__)
            return True, (f"{CHUA_DO_DUOC}: khong hoi duoc tuong lua cua may "
                          f"{vmid} ({type(exc).__name__})")
        # ⛔ Mot may ho la mot duong vao. "Phan lon may da cach ly" khong phai
        #    mot trang thai an toan.
        if not hieu_luc:
            ho.append(f"may {vmid}: {ly_do}")
    if ho:
        return True, ("node da co khach khac va cach ly chua hieu luc — "
                      + "; ".join(ho))
    return False, ""
