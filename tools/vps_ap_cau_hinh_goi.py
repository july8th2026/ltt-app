"""Áp CPU/RAM của **gói** lên máy đang chạy, và báo máy nào đang lệch.

## Vì sao cần một công cụ riêng

`jobs._cau_hinh_may_trong` đặt `cores`/`memory` **một lần duy nhất, lúc tạo
máy**. Không đường nào đọc lại chúng về sau. Nên khi bảng giá đổi (26/09/2026:
gói Nhỏ 1 vCPU/2 GB → 2 vCPU/4 GB), sổ của ta nói một đằng còn máy thật chạy một
nẻo — và ⛔ không có gì báo.

⭐ Đó đúng là khuôn *"hai chỗ khai cùng một điều mà không ai bắt khớp"*: khách
   trả tiền cho 2 vCPU và nhận 1, hoặc ngược lại, và cả hai bên đều "đúng" theo
   nguồn của mình.

## Vì sao ⛔ KHÔNG tự áp trong vòng bảo trì

Đổi `cores`/`memory` của QEMU đòi **tắt máy rồi bật lại** (hotplug CPU/RAM phải
bật từ trước, và bật nó cũng cần một lần khởi động lại). Một vòng bảo trì tự
khởi động lại máy khách là một sự cố, ⛔ không phải một lần sửa.

⇒ Vòng bảo trì chỉ **đo và báo** (`bao_tri.lech_cau_hinh_goi`); việc khởi động
  lại là quyết định của người, và đi qua công cụ này.

## Dùng

    python tools\\vps_ap_cau_hinh_goi.py                 # chỉ SOI, không sửa
    python tools\\vps_ap_cau_hinh_goi.py --ap --vmid 204 # áp cho MỘT máy
    python tools\\vps_ap_cau_hinh_goi.py --ap --tat-ca   # áp cho mọi máy lệch

⚠️ `--ap` **tắt máy khách rồi bật lại**. Chỉ chạy khi chủ máy đã đồng ý.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))


def _nap_env(duong_dan: str) -> None:
    """Nạp biến môi trường theo đúng giao ước của `api_prod_canary.py`."""
    from tools.tai_khoan_thu import nap_env

    nap_env(duong_dan)


def doc_cau_hinh(client, vmid: int) -> dict:
    """`cores`/`memory` **trong sổ cấu hình** — tức thứ lần boot SAU sẽ dùng."""
    cfg = client._goi(
        "GET", f"/nodes/{client.config.node}/qemu/{int(vmid)}/config") or {}
    return {"cores": int(cfg.get("cores") or 0) * int(cfg.get("sockets") or 1),
            "memory": int(cfg.get("memory") or 0)}


def doc_dang_chay(client, vmid: int) -> dict:
    """`cores`/`memory` mà tiến trình QEMU **đang thật sự** cấp cho khách.

    🔴 26/09/2026 — chính cái bẫy này đã bắt tôi: công cụ đọc **sổ cấu hình** và
       in "khớp", trong khi hai máy khách vẫn đang chạy 1 vCPU / 2 GB. Cấu hình
       đã được đổi, nhưng QEMU **chốt CPU/RAM lúc khởi động**; hai máy đã chạy
       liên tục 25 giờ nên chúng vẫn giữ con số cũ.

    ⭐ *Thứ tôi đang hỏi có SẴN ở chỗ tôi đang đứng không?* Câu hỏi là **khách
       đang được cấp bao nhiêu**, và `config` ⛔ không trả lời câu đó — nó trả
       lời *"lần boot sau sẽ là bao nhiêu"*. Hai câu khác nhau, và chúng chỉ
       trùng nhau khi ⛔ không ai sửa gì kể từ lần bật máy.

    Máy đã tắt thì ⛔ không có số nào để đọc: trả `{}` (⛔ không phải 0 — *chưa
    đo được* ⛔ không phải *bằng không*).
    """
    st = client.trang_thai_vm(int(vmid)) or {}
    if str(st.get("status")) != "running":
        return {}
    return {"cores": int(st.get("cpus") or 0),
            "memory": int(st.get("maxmem") or 0) // (1024 * 1024)}


def ap_cho_mot_may(db, may, client, *, cho_giay: int = 20) -> dict:
    """Đặt `cores`/`memory` theo gói rồi **tắt hẳn và bật lại**.

    ⚠️ Phải là `stop` + `start`, ⛔ **không** phải `reboot`: QEMU chốt CPU/RAM
    lúc tiến trình khởi động, và `reboot` của Proxmox khởi động lại **guest**
    trong cùng tiến trình cũ — máy sẽ boot lại mà vẫn giữ nguyên 1 vCPU / 2 GB,
    và mọi thứ trông như đã xong.

    Đọc lại **cả hai** sau khi làm: sổ cấu hình (Proxmox đã *giữ* chưa) và tiến
    trình đang chạy (khách đã *nhận* chưa). Một lệnh trả 200 chỉ nói nó đã
    **nhận** yêu cầu.
    """
    from apps.vps import trang_thai_may as tt
    from apps.vps.cost import lay_plan
    from apps.vps.services.provisioning import ghi_su_kien

    plan = lay_plan(may.plan_id)
    if plan is None:
        raise SystemExit(f"may {may.vmid}: khong co goi {may.plan_id!r}")

    vmid = int(may.vmid)
    mong_muon = {"cores": plan.vcpu, "memory": plan.ram_mb}
    truoc_ch = doc_cau_hinh(client, vmid)
    truoc_chay = doc_dang_chay(client, vmid)
    if truoc_ch == mong_muon and truoc_chay == mong_muon:
        return {"vmid": vmid, "da_dung": True, **truoc_chay}

    node = client.config.node
    client._goi("POST", f"/nodes/{node}/qemu/{vmid}/status/stop")
    for _ in range(cho_giay):
        if str((client.trang_thai_vm(vmid) or {}).get("status")) == "stopped":
            break
        time.sleep(1)
    if truoc_ch != mong_muon:
        client.dat_cau_hinh(vmid, sockets=1, **mong_muon)

    sau_ch = doc_cau_hinh(client, vmid)
    if sau_ch != mong_muon:
        # Bật lại rồi mới ném: bỏ máy khách ở trạng thái TẮT vì một lần đọc
        # ngược không khớp là biến một lỗi cấu hình thành một lần mất dịch vụ.
        client._goi("POST", f"/nodes/{node}/qemu/{vmid}/status/start")
        raise SystemExit(f"may {vmid}: dat {mong_muon} nhung doc lai ra {sau_ch}")

    client._goi("POST", f"/nodes/{node}/qemu/{vmid}/status/start")
    for _ in range(cho_giay):
        sau_chay = doc_dang_chay(client, vmid)
        if sau_chay:
            break
        time.sleep(1)
    tt.ghi_quan_sat(may, tt.CHAY)
    ghi_su_kien(db, may.id, "doi_cau_hinh", boi="quan_tri",
                truoc=truoc_chay or truoc_ch, sau=sau_chay, goi=may.plan_id)
    db.commit()
    if sau_chay != mong_muon:
        raise SystemExit(
            f"may {vmid}: cau hinh dung nhung tien trinh dang chay van {sau_chay}")
    return {"vmid": vmid, "da_dung": False,
            "truoc": truoc_chay or truoc_ch, "sau": sau_chay}


def _may_dang_song(db):
    from sqlalchemy import select

    from apps.vps.tables import VpsInstance

    return db.execute(select(VpsInstance).where(
        VpsInstance.vmid.isnot(None),
        VpsInstance.trang_thai != "da_xoa")).scalars().all()


def main() -> int:
    bo = argparse.ArgumentParser(description=__doc__)
    bo.add_argument("--env", default=r"C:\LTTPlatform\secrets\app.env")
    bo.add_argument("--ap", action="store_true",
                    help="THUC SU sua — tat may khach roi bat lai")
    bo.add_argument("--vmid", type=int, default=0)
    bo.add_argument("--tat-ca", action="store_true")
    doi = bo.parse_args()
    _nap_env(doi.env)

    from apps.vps import bao_tri
    from apps.vps.cost import lay_plan
    from apps.vps.services import backend_factory
    from apps.vps.tables import VpsInfrastructureProfile
    from platform_core.db import get_session

    so_lech = 0
    for db in get_session():
        for may in _may_dang_song(db):
            profile = db.get(VpsInfrastructureProfile,
                             may.infrastructure_profile_id)
            if profile is None:
                print(f"  vm {may.vmid}: chua ghim ho so — bo qua")
                continue
            client = backend_factory.compute_backend(profile).client
            plan = lay_plan(may.plan_id)
            ch = doc_cau_hinh(client, may.vmid)
            chay = doc_dang_chay(client, may.vmid)
            lech_ch = bao_tri.lech_cau_hinh_goi(plan, ch)
            lech_chay = bao_tri.lech_cau_hinh_goi(plan, chay)
            if lech_ch:
                dau = "LECH (ca so cau hinh)"
            elif lech_chay:
                dau = "CHO KHOI DONG LAI (so dung, tien trinh cu)"
            else:
                dau = "khop"
            print(f"  vm {may.vmid} ({may.plan_id}): {dau}\n"
                  f"       goi      = {plan.vcpu} vCPU / {plan.ram_mb} MB\n"
                  f"       so       = {ch['cores']} vCPU / {ch['memory']} MB\n"
                  f"       dang chay= " + (
                      f"{chay['cores']} vCPU / {chay['memory']} MB" if chay
                      else "(may dang tat — khong do duoc)"))
            if not (lech_ch or lech_chay):
                continue
            so_lech += 1
            if not doi.ap:
                continue
            if doi.vmid and int(may.vmid) != doi.vmid and not doi.tat_ca:
                continue
            if not doi.vmid and not doi.tat_ca:
                print("     (can --vmid hoac --tat-ca de thuc su ap)")
                continue
            kq = ap_cho_mot_may(db, may, client)
            print(f"     -> da ap: {kq}")
        break
    print(f"RESULT: {so_lech} may lech cau hinh goi")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
