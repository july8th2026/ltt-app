"""Dòng lệnh của agent: `enroll`, `run`, `status`, `forget`.

    python -m nexus_agent enroll --url https://app.lttstudios.com --code ABCD-EFGH
    python -m nexus_agent run    --url https://app.lttstudios.com
    python -m nexus_agent status
    python -m nexus_agent forget

Bốn lệnh, và `forget` có mặt vì một lý do: khi khách bấm thu hồi trên web, agent
tự xoá danh tính ở nhịp kế tiếp — nhưng nếu máy đang tắt lúc đó thì nó sẽ tỉnh
dậy và gõ cửa bằng một danh tính đã chết. `forget` là đường cho người vận hành
dọn tay mà không phải đi tìm file.

**Không lệnh nào in ra khoá riêng**, kể cả `status`. Một giá trị đã được in là
một giá trị đã vào lịch sử terminal, ảnh chụp màn hình, và log của phần mềm hỗ
trợ từ xa mà chính sản phẩm này sẽ cài.
"""
from __future__ import annotations

import argparse
import logging
import os
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nexus_agent.client import AgentError, NexusClient      # noqa: E402
from nexus_agent.keystore import Keystore, KeystoreError    # noqa: E402
from nexus_agent.service import ServiceError                # noqa: E402

#: Nơi cất danh tính. `%ProgramData%` chứ không `%AppData%`: agent chạy như một
#: dịch vụ, nên hồ sơ người dùng có thể không được nạp lúc nó khởi động.
def _thu_muc_mac_dinh() -> Path:
    thu_cong = os.environ.get("LTT_NEXUS_AGENT_DIR", "").strip()
    if thu_cong:
        return Path(thu_cong)
    if sys.platform.startswith("win"):
        return Path(os.environ.get("ProgramData", r"C:\ProgramData")) / "LTTNexus"
    return Path.home() / ".ltt-nexus"


def _client(args) -> NexusClient:
    return NexusClient(args.url, Keystore(args.dir))


def cmd_enroll(args) -> int:
    client = _client(args)
    device_id = client.ghep(args.code, ten_may=args.name or socket.gethostname(),
                            platform=sys.platform)
    print(f"da ghep. device_id={device_id}")
    print(f"danh tinh cat tai: {args.dir}")
    return 0


def cmd_run(args) -> int:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    # `run` la che do phuc vu dieu khien -> gan engine that. Lazy: no chi cham
    # RustDesk khi co ve moi, nen may chua cai RustDesk van chay (danh tinh/
    # presence), chi bao loi theo tung phien.
    from nexus_agent.engine_runner import RustDeskEngine

    client = NexusClient(args.url, Keystore(args.dir), engine=RustDeskEngine())
    ly_do = client.chay(so_nhip=args.beats)
    print(f"dung: {ly_do}")
    # `revoked` KHONG phai loi: khach da bam thu hoi va he thong lam dung viec.
    # Tra ma khac 0 se lam Windows Service Manager coi la su co va khoi dong lai
    # mai — dung thu no vua duoc bao la phai dung.
    return 0


def cmd_status(args) -> int:
    ks = Keystore(args.dir)
    print(f"thu muc      : {ks.dir}")
    print(f"co khoa      : {ks.da_co_khoa()}")
    try:
        print(f"device_id    : {ks.doc_device_id()}")
    except KeystoreError:
        print("device_id    : (chua ghep)")
    try:
        # In khoa CONG KHAI thi an toan — no la thu duoc gui len server.
        print(f"khoa cong khai: {ks.doc_public()}")
    except KeystoreError:
        print("khoa cong khai: (chua co)")
    return 0


def cmd_forget(args) -> int:
    Keystore(args.dir).xoa()
    print("da xoa danh tinh thiet bi tren may nay.")
    return 0


def cmd_install(args) -> int:
    """Cai lich tu chay khi dang nhap. CAN quyen admin MOT LAN (Q99): task chay
    `/rl HIGHEST` de xoay mat khau RustDesk duoc; tao task do doi admin luc cai,
    nhung sau do chay khong hoi UAC lai."""
    from nexus_agent import service

    service.cai(sys.executable, args.url, thu_muc=args.dir)
    print(f"da cai lich chay: task '{service.TASK_NAME}' se chay (nang quyen) khi "
          f"ban dang nhap.")
    print("neu bao 'Access is denied': chay lai cua so nay bang quyen Administrator.")
    print("go bang: python -m nexus_agent uninstall")
    return 0


def cmd_uninstall(args) -> int:
    from nexus_agent import service

    if service.go():
        print(f"da go lich chay '{service.TASK_NAME}'.")
    else:
        print("khong co lich chay nao de go.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="nexus_agent",
                                     description=__doc__.splitlines()[0])
    parser.add_argument("--dir", default=str(_thu_muc_mac_dinh()),
                        help="thu muc cat danh tinh")
    sub = parser.add_subparsers(dest="lenh", required=True)

    p = sub.add_parser("enroll", help="doi ma ghep lay danh tinh")
    p.add_argument("--url", required=True)
    p.add_argument("--code", required=True)
    p.add_argument("--name", default="")
    p.set_defaults(func=cmd_enroll)

    p = sub.add_parser("run", help="vong nhip tim")
    p.add_argument("--url", required=True)
    p.add_argument("--beats", type=int, default=0, help="0 = chay mai")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("status", help="may nay dang o trang thai nao")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("forget", help="xoa danh tinh tren may nay")
    p.set_defaults(func=cmd_forget)

    p = sub.add_parser("install", help="cai lich tu chay khi dang nhap")
    p.add_argument("--url", required=True)
    p.set_defaults(func=cmd_install)

    p = sub.add_parser("uninstall", help="go lich tu chay")
    p.set_defaults(func=cmd_uninstall)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (AgentError, KeystoreError, ServiceError) as exc:
        # Mot cau, khong stack trace: nguoi doc thong bao nay la KHACH dang cai
        # phan mem, khong phai lap trinh vien. Loi khac (bug that) van noi len
        # nguyen ven de con go duoc.
        print(f"LOI: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
