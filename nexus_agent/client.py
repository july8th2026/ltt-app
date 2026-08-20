"""Nửa ĐỘC QUYỀN của endpoint: ghép máy, nhịp tim, nhận vé. Không chạm AGPL.

Endpoint Windows là **hai tiến trình** (Q93 ràng buộc 4). Đây là tiến trình A:
danh tính, enrollment, presence, vé phiên. Nó **không** bắt màn hình, không nhận
phím chuột, không truyền dữ liệu — những việc đó thuộc tiến trình B (engine
AGPL), và ranh giới ấy vừa là ranh giới giấy phép vừa là ranh giới bảo mật.

Nhờ vậy file này **viết được ngay** trong khi D1 (legal review) và D2 (relay)
còn mở: nó không phụ thuộc engine nào cả.

## Nó cố ý KHÔNG làm gì

* không khởi động engine — đó là N3.2, sau khi có câu trả lời pháp lý;
* không mở cổng, không nghe kết nối vào. Agent chỉ **gọi ra**, nên máy khách
  không cần mở cổng nào và không thành một bề mặt tấn công mới;
* không tự nâng quyền.

## Vòng nhịp tim và cái nó phải tôn trọng

Server trả `revoked: true` khi thiết bị đã bị thu hồi. Lúc đó agent **dừng hẳn
và xoá danh tính**, không thử lại. Một agent tiếp tục gõ cửa sau khi bị thu hồi
là một agent biến nút "Thu hồi" của khách thành nút trang trí — và cũng là một
agent tự đưa mình vào trần giới hạn nhịp mãi mãi.
"""
from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request

from nexus_agent.keystore import Keystore, KeystoreError

log = logging.getLogger("nexus_agent")

#: Nhịp gửi. Server coi là offline sau 180 giây (`devices.OFFLINE_AFTER_S`), nên
#: 60 giây cho phép mất hai nhịp liên tiếp mà máy vẫn hiện "đang bật".
NHIP_S = 60

#: Chờ tối đa cho một lời gọi. Ngắn: agent thà bỏ một nhịp còn hơn treo một
#: luồng vô hạn trên máy khách.
TIMEOUT_S = 20

USER_AGENT = "LTT-Nexus-Agent/1"


class AgentError(Exception):
    """Gọi server không thành. Không bao giờ chứa khoá hay vé."""


class NexusClient:
    """Một thiết bị nói chuyện với control plane."""

    def __init__(self, base_url: str, keystore: Keystore, engine=None):
        self.base_url = str(base_url or "").rstrip("/")
        self.ks = keystore
        #: Bộ chuẩn bị engine cho một phiên. Đối tượng có `chuan_bi_phien() ->
        #: (engine_id, secret)`: xoay mật khẩu RustDesk + lấy ID (N3.2). `None`
        #: nghĩa là máy này chưa gắn engine — agent vẫn chạy (danh tính/presence),
        #: chỉ không phục vụ điều khiển. Tiêm được để test không cần RustDesk.
        self.engine = engine

    # ── HTTP ────────────────────────────────────────────────────────────────

    def _goi(self, path: str, body: bytes, headers: dict) -> tuple:
        """Trả `(status, dict)`. Không ném khi server trả lỗi có cấu trúc.

        Lỗi của server là **dữ liệu**, không phải sự cố: `401` và `429` đều là
        câu trả lời hợp lệ mà vòng lặp phải xử lý khác nhau. Chỉ lỗi mạng mới
        ném.
        """
        req = urllib.request.Request(
            self.base_url + path, data=body, method="POST",
            headers={"Content-Type": "application/json",
                     "User-Agent": USER_AGENT, **headers})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                return resp.status, json.loads(resp.read() or b"{}")
        except urllib.error.HTTPError as exc:
            raw = exc.read() or b"{}"
            try:
                return exc.code, json.loads(raw)
            except ValueError:
                # Server tra HTML o mot duong may-goi-may la mot su co dang bao,
                # khong duoc nuot: no thuong nghia la mot proxy dang tra loi thay.
                return exc.code, {"error": {"code": "non_json",
                                            "message": raw[:200].decode(
                                                "utf-8", "replace")}}
        except urllib.error.URLError as exc:
            raise AgentError(f"khong ket noi duoc control plane: {exc.reason}") from exc

    def _ky(self, path: str, body: bytes) -> dict:
        from platform_core.nexus.agent_auth import (HEADER_DEVICE,
                                                    HEADER_SIGNATURE,
                                                    HEADER_TIMESTAMP,
                                                    sign)

        ts = str(int(time.time()))
        chu_ky = sign(self.ks.doc_khoa(), method="POST", path=path,
                      timestamp=ts, body=body)
        return {HEADER_DEVICE: self.ks.doc_device_id(),
                HEADER_TIMESTAMP: ts, HEADER_SIGNATURE: chu_ky}

    # ── Ba việc ─────────────────────────────────────────────────────────────

    def ghep(self, ma: str, *, ten_may: str = "", platform: str = "",
             agent_version: str = "1") -> str:
        """Đổi mã ghép lấy danh tính. Trả `device_id`.

        Sinh khoá **trước** khi gọi, và chỉ gửi phần công khai. Nếu server từ
        chối thì khoá vừa sinh bị bỏ đi — không giữ lại một khoá mà server không
        biết, vì nó chỉ gây nhầm lẫn ở lần chạy sau.
        """
        moi = not self.ks.da_co_khoa()
        public = self.ks.sinh_khoa() if moi else self.ks.doc_public()

        body = json.dumps({
            "code": str(ma or ""), "public_key": public,
            "display_name": ten_may, "platform": platform,
            "agent_version": agent_version,
        }).encode("utf-8")

        status, data = self._goi("/nexus-agent/enroll", body, {})
        if status != 200:
            if moi:
                self.ks.xoa()
            raise AgentError(_thong_diep(data, "ghep may that bai"))

        device_id = str(data.get("device_id") or "")
        if not device_id:
            raise AgentError("server khong tra device_id")
        self.ks.luu_device_id(device_id)
        return device_id

    def nhip_tim(self) -> dict:
        """Một nhịp. Trả dict của server; ném `AgentError` khi không gọi được."""
        path = "/nexus-agent/heartbeat"
        status, data = self._goi(path, b"", self._ky(path, b""))
        if status == 401:
            # Server khong con nhan danh tinh nay. Coi nhu bi thu hoi: tiep tuc
            # go cua bang mot danh tinh khong chung minh duoc la vo nghia.
            return {"ok": False, "revoked": True, "sessions": []}
        if status != 200:
            raise AgentError(_thong_diep(data, f"nhip tim that bai ({status})"))
        return data

    def doi_ve(self, ve: str) -> dict:
        path = "/nexus-agent/session/redeem"
        body = json.dumps({"ticket": str(ve or "")}).encode("utf-8")
        status, data = self._goi(path, body, self._ky(path, body))
        if status != 200:
            raise AgentError(_thong_diep(data, "doi ve that bai"))
        return data

    def bao_engine(self, session_id: str, engine_id: str, secret: str) -> dict:
        """Báo chi tiết kết nối cho một phiên (W3). Ký như mọi request khác.

        `secret` là mật khẩu một-lần — nó chỉ đi trong body đã ký của đúng request
        này, không vào log, không cất xuống đĩa.
        """
        path = "/nexus-agent/session/engine"
        body = json.dumps({"session_id": str(session_id or ""),
                           "engine_id": str(engine_id or ""),
                           "secret": str(secret or "")}).encode("utf-8")
        status, data = self._goi(path, body, self._ky(path, body))
        if status != 200:
            raise AgentError(_thong_diep(data, "bao engine that bai"))
        return data

    def _chuan_bi_cho_bao(self, cho_bao: list) -> None:
        """Với mỗi vé mới: xoay mật khẩu engine + lấy ID rồi báo lên server.

        Mỗi phiên độc lập: một phiên hỏng (engine lỗi, mạng chớp) **không** được
        làm hỏng các phiên khác hay cả vòng nhịp tim — nên mỗi cái bọc riêng.
        """
        if not cho_bao:
            return
        if self.engine is None:
            log.warning("co %d phien cho dieu khien nhung may nay chua gan engine",
                        len(cho_bao))
            return
        for phien in cho_bao:
            sid = phien.get("session_id")
            try:
                engine_id, secret = self.engine.chuan_bi_phien()
                self.bao_engine(sid, engine_id, secret)
                log.info("da chuan bi phien %s", sid)
            except Exception as exc:                          # noqa: BLE001
                # Bao gio cung nuot-va-log o day: mot phien loi khong duoc dung
                # ca vong. Loi that (engine hong) van hien trong log de con go.
                log.warning("khong chuan bi duoc phien %s: %s", sid, exc)

    # ── Vòng chạy ───────────────────────────────────────────────────────────

    def chay(self, *, so_nhip: int = 0, ngu=time.sleep) -> str:
        """Vòng nhịp tim. Trả lý do dừng.

        `so_nhip=0` là chạy mãi. Tham số `ngu` để test tua nhanh mà không phải
        chờ thật — một vòng lặp chỉ kiểm được bằng cách chờ 60 giây là một vòng
        lặp không ai kiểm.
        """
        dem, cho = 0, NHIP_S
        while True:
            try:
                tra_loi = self.nhip_tim()
                cho = NHIP_S
            except AgentError as exc:
                # Mat mang la chuyen thuong tren may khach. Lui dan, toi da 10
                # phut, roi thu lai — khong dung han.
                log.warning("nhip tim loi: %s", exc)
                cho = min(cho * 2, 600)
                tra_loi = {}

            if tra_loi.get("revoked"):
                self.ks.xoa()
                return "revoked"

            # Vé mới → chuẩn bị engine (xoay mật khẩu + báo). Làm TRƯỚC khi log
            # phiên đang mở, vì chuẩn bị xong thì phiên mới chuyển sang "đang mở".
            self._chuan_bi_cho_bao(tra_loi.get("cho_bao") or [])

            for phien in tra_loi.get("sessions") or []:
                log.info("co phien dang mo: %s (%s)",
                         phien.get("session_id"), phien.get("quyen"))

            dem += 1
            if so_nhip and dem >= so_nhip:
                return "het so nhip"
            ngu(cho)


def _thong_diep(data: dict, mac_dinh: str) -> str:
    loi = (data or {}).get("error") or {}
    return str(loi.get("message") or mac_dinh)


__all__ = ["AgentError", "NHIP_S", "NexusClient", "TIMEOUT_S"]
