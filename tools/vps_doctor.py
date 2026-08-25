"""Kiem duong noi toi Proxmox va in ra nhung so ma H39 dang can (P0a).

Chay tren may A, sau khi da dat bien trong `secrets/app.env`:

    python tools/vps_doctor.py

Cong cu nay ton tai vi mot ly do cu the: bi mat cua token **khong duoc roi khoi
may**. Thay vi doc gia tri token cho ai do, chu san pham dat no vao app.env roi
chay lenh nay, va chi gui lai PHAN IN RA — trong do khong co bi mat nao.

No tra loi dung ba cau hoi dang chan P0b:

  1. Kho `PVE-Data` la LVM-thin hay ZFS? (noi bang hai lenh khac nhau; lam nham
     la hong kho)
  2. Con bao nhieu dia va RAM that?
  3. Token co du quyen cho tung viec app se lam khong? — hoi tung endpoint mot,
     thay vi de mot loi 403 hien ra giua chung mot lan clone that.
"""
from __future__ import annotations

import os
import pathlib
import sys

GOC = pathlib.Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))


def _nap_app_env() -> None:
    """Nap bien moi truong. **Ban DA CAI truoc, cay nguon sau.**

    Thu tu nay quan trong: `secrets/app.env` trong cay nguon giu mat khau CSDL
    CU, va dung no thi loi hien ra la `password authentication failed for user
    ltt_app` -- mot cau chi thang vao Postgres trong khi nguyen nhan la doc nham
    tep. Da mat thi gio vi no hai lan.
    """
    for tep in (pathlib.Path("C:/LTTPlatform/secrets/app.env"),
                GOC / "secrets" / "app.env"):
        if not tep.exists():
            continue
        for dong in tep.read_text(encoding="utf-8-sig").splitlines():
            if "=" in dong and not dong.strip().startswith("#"):
                k, v = dong.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def _gb(byte) -> float:
    return round(int(byte or 0) / 1024 ** 3, 1)


def _doi_chieu_bon_nguon(client) -> int:
    """In bao cao doi chieu. Phep quet nam o `apps/vps/doi_chieu.py`.

    Tep nay chi HIEN THI. Chep logic quet vao day nghia la co hai ban, va
    ban trong vong bao tri (thu that su chay hang ngay) se la ban bi quen.
    """
    from apps.vps import doi_chieu
    from platform_core.db import get_session

    print()
    print("== Doi chieu bon nguon su that ==")
    gen = get_session()
    db = next(gen)
    try:
        kq = doi_chieu.quet(db, client)
        for x in kq.khong_doc_duoc:
            print(f"  khong doc duoc {x}")
        for lech in kq.lech:
            print(f"  MO COI {lech.nhan}: {list(lech.muc)}")
            print(f"         -> {lech.hau_qua}")
        if not kq.lech:
            print(f"  sach ({kq.so_may} may, {kq.so_ip} IP) - khong co gi mo coi")
        return kq.tong_mo_coi
    finally:
        gen.close()

def main() -> int:
    _nap_app_env()

    from apps.vps.services import capacity, proxmox

    try:
        cfg = proxmox.doc_cau_hinh()
    except proxmox.ChuaCauHinh as exc:
        print("CHUA CAU HINH:", exc)
        print("\nDat cac bien sau vao secrets/app.env roi chay lai:")
        print("  LTT_VPS_PROXMOX_URL=https://192.168.2.168:8006")
        print("  LTT_VPS_PROXMOX_TOKEN_ID=vpsapp@pve!ltt")
        print("  LTT_VPS_PROXMOX_TOKEN_SECRET=<bi mat token>")
        print("  LTT_VPS_PROXMOX_NODE=pve")
        return 2

    print(f"URL   : {cfg.base_url}")
    print(f"NODE  : {cfg.node}")
    print(f"TOKEN : {cfg.token_id}          (bi mat KHONG in ra)")
    print()

    client = proxmox.ProxmoxClient(cfg)
    loi = 0

    # ── 1. Duong noi + token ────────────────────────────────────────────────
    try:
        v = client.phien_ban()
        print(f"[OK  ] ket noi + token   -> Proxmox VE {v.get('version', '?')}")
    except proxmox.ProxmoxError as exc:
        print(f"[FAIL] ket noi + token   -> {exc}")
        return 1

    # ── 2. RAM that cua node ────────────────────────────────────────────────
    tt = {}
    try:
        tt = client.trang_thai_node()
        mem = tt.get("memory") or {}
        print(f"[OK  ] doc trang thai node -> RAM tong {_gb(mem.get('total'))} GB, "
              f"dang dung {_gb(mem.get('used'))} GB")
    except proxmox.ProxmoxError as exc:
        loi += 1
        print(f"[FAIL] doc trang thai node -> {exc}")
        print("       thieu quyen Sys.Audit tren /nodes/<node>")

    # ── 3. Kho luu tru: KIEU va DUNG LUONG — cau hoi chinh cua P0a ─────────
    kho = []
    try:
        kho = client.kho_luu_tru()
        print("[OK  ] doc kho luu tru:")
        print(f"       {'ten':<16} {'kieu':<12} {'noi dung':<22} "
              f"{'tong':>9} {'da dung':>9} {'%':>6}")
        for k in sorted(kho, key=lambda x: -int(x.get("total") or 0)):
            tong = int(k.get("total") or 0)
            dung = int(k.get("used") or 0)
            ty = f"{dung / tong * 100:.1f}" if tong else "-"
            print(f"       {str(k.get('storage')):<16} {str(k.get('type')):<12} "
                  f"{str(k.get('content')):<22} {_gb(tong):>8} G {_gb(dung):>8} G "
                  f"{ty:>6}")
    except proxmox.ProxmoxError as exc:
        loi += 1
        print(f"[FAIL] doc kho luu tru -> {exc}")
        print("       thieu quyen Datastore.Audit tren /storage")

    # ── 4. Liet ke VM (de biet template dang o dau) ────────────────────────
    try:
        vms = client.danh_sach_vm()
        tpl = [v for v in vms if int(v.get("template") or 0) == 1]
        print(f"[OK  ] doc danh sach VM -> {len(vms)} VM, {len(tpl)} template")
        for v in tpl:
            print(f"       template vmid={v.get('vmid')} ten={v.get('name')}")
        if not tpl:
            print("       (chua co template nao — P1/P5 se dung)")
    except proxmox.ProxmoxError as exc:
        loi += 1
        print(f"[FAIL] doc danh sach VM -> {exc}  (thieu VM.Audit)")

    try:
        print(f"[OK  ] xin VMID ke tiep -> {client.vmid_ke_tiep()}")
    except proxmox.ProxmoxError as exc:
        loi += 1
        print(f"[FAIL] xin VMID ke tiep -> {exc}")

    # ── 5. Ket luan: suc chua theo dung phep tinh app se dung ──────────────
    if tt and kho:
        goc = capacity.suc_chua_tu_proxmox(tt, kho)
        ram_ck, dia_ck, vcpu_ck = capacity.cam_ket_tu_vm(vms if 'vms' in dir() else [])
        lon = capacity.kho_lon_nhat(kho)
        sc = capacity.SucChua(
            ram_mb_tong=goc.ram_mb_tong, dia_gb_tong=goc.dia_gb_tong,
            cpu_tong=goc.cpu_tong, vcpu_da_hua=vcpu_ck,
            ram_mb_da_hua=ram_ck, dia_gb_da_hua=dia_ck,
            dia_gb_dang_dung=int(lon.get("used") or 0) // 1024 ** 3)
        print()
        print("SUC CHUA (theo dung phep tinh cua apps/vps/services/capacity.py):")
        print(f"  RAM tong {sc.ram_mb_tong // 1024} GB "
              f"| chua {capacity.RAM_DU_PHONG_MB // 1024} GB cho Proxmox "
              f"| VM hien co da cam ket {sc.ram_mb_da_hua // 1024} GB "
              f"-> CON {sc.ram_mb_con // 1024} GB")
        print(f"  Dia (CHIA SE, V14) {sc.dia_gb_tong} GB "
              f"| chua {capacity.DIA_TEMPLATE_GB} GB template "
              f"| da hua {sc.dia_gb_da_hua} GB | DUNG THAT "
              f"{sc.dia_gb_dang_dung} GB "
              f"-> con {sc.dia_gb_con_that} GB truoc phanh "
              f"{capacity.NGUONG_CHAN_BAN * 100:.0f}%")
        print(f"     ban chong {sc.ty_le_ban_chong:.2f}x "
              f"(tran {capacity.TRAN_BAN_CHONG:.1f}x)")
        qt = capacity.kho_qua_tai(int(lon.get("used") or 0),
                                  int(lon.get("total") or 0))
        print(f"  Kho lon nhat: {lon.get('storage')} ({lon.get('type')}) — "
              f"{'CON CHO' if qt.cho_phep else 'QUA TAI: ' + qt.ly_do}")
        print()
        for pid in ("vps-nho", "vps-vua", "vps-lon"):
            from apps.vps.cost import lay_plan
            p = lay_plan(pid)
            n = 0
            while capacity.cho_phep_ban(
                capacity.SucChua(
                    ram_mb_tong=sc.ram_mb_tong, dia_gb_tong=sc.dia_gb_tong,
                    ram_mb_da_hua=sc.ram_mb_da_hua + n * p.ram_mb,
                    dia_gb_da_hua=sc.dia_gb_da_hua + n * p.disk_gb,
                    dia_gb_dang_dung=sc.dia_gb_dang_dung), pid).cho_phep:
                n += 1
                if n > 500:
                    break
            print(f"  Neu ban toan {pid:<8} -> {n} may")

    # ── Dia cai dat: da khai chua ───────────────────────────────────────────
    #
    # Fail-closed: chua khai thi job tu choi tao may. Kiem o day de biet TRUOC
    # khi mot khach bam mua, thay vi de ho gap loi.
    print()
    print("== Dia cai dat cua tung he dieu hanh ==")
    from apps.vps import os_images
    for img in os_images.OS_IMAGES:
        if not img.khach_thay:
            continue
        volid = os_images.dia_cai_dat(img.id)
        if not volid:
            print(f"  {img.id:<18} CHUA KHAI {os_images.khoa_moi_truong(img.id)}")
            loi += 1
            continue
        co = any(str(x.get("volid", "")) == volid
                 for x in (client._goi(
                     "GET", f"/nodes/{client.config.node}/storage/"
                            f"{volid.split(':')[0]}/content") or []))
        print(f"  {img.id:<18} {volid}  {'OK' if co else 'KHONG THAY TREN NODE'}")
        if not co:
            loi += 1

    # ── Ban sao luu cua cong vao co con khop khong ───────────────────────────
    #
    # Bo luat tren cong vao doi ma ban sao luu khong doi => kich ban dung lai se
    # sinh ra mot cong vao KHAC cai dang chay, va khong ai biet cho toi luc phai
    # dung no. Kiem o day vi day la cho duy nhat chay dinh ky va doc duoc CA HAI.
    print()
    print("== Ban sao luu cong vao ==")
    import subprocess
    from pathlib import Path as _P

    sao_luu = _P("secrets/cong_vao/nftables.conf")
    if not sao_luu.exists():
        print("  CHUA SAO LUU — cong vao chet la khong dung lai duoc")
        print("  (khoa rieng WireGuard chi ton tai tren chinh con VPS ay)")
        loi += 1
    else:
        try:
            that = subprocess.run(
                ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
                 "ltt-gw", "cat /etc/nftables.conf"],
                capture_output=True, text=True, timeout=30).stdout
        except Exception as exc:                 # noqa: BLE001
            that = ""
            print(f"  khong doc duoc cong vao: {str(exc)[:60]}")
        if that:
            cu = [d.strip() for d in sao_luu.read_text(encoding="utf-8").splitlines()
                  if d.strip() and not d.strip().startswith("#")]
            moi = [d.strip() for d in that.splitlines()
                   if d.strip() and not d.strip().startswith("#")]
            if cu == moi:
                print("  nftables.conf: KHOP ban dang chay")
            else:
                print("  nftables.conf: LECH ban dang chay — sao luu lai")
                loi += 1
        for ten in ("wg_private.key", "wg_public.key"):
            print(f"  {ten}: {'co' if (sao_luu.parent / ten).exists() else 'THIEU'}")

    try:
        loi += _doi_chieu_bon_nguon(client)
    except Exception as exc:                     # noqa: BLE001
        # Doi chieu can CSDL + router + gateway + Vultr. Bat ky cai nao khong
        # tra loi cung khong duoc lam mat cac phep kiem DA CHAY XONG o tren --
        # nguoi chay doctor thuong dang tim mot su co, va mot traceback thay cho
        # bao cao la mot buoc lui.
        print()
        print("== Doi chieu bon nguon su that ==")
        print(f"  KHONG CHAY DUOC: {type(exc).__name__}: "
              f"{str(exc)[:90]}")
        loi += 1

    print()
    print("RESULT:", "PASS" if loi == 0 else f"CO {loi} MUC CAN XEM")
    return 0 if loi == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
