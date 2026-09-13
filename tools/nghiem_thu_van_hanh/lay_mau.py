"""lay_mau.py — chụp trạng thái hệ **trong lúc** tải đang chạy.

Điểm vào của chương trình: `docs/VAN_HANH_THAT.md`.

🔴 Vì sao tệp này tồn tại: rà soát 13/09 cho thấy **26/43 kỳ vọng (60%) của ma
   trận chưa bao giờ được kiểm** — vì `nop_tai` chỉ biết những gì một *khách*
   nhìn thấy (mã HTTP, số mảnh), còn `dinh_lease`, `tran_tai_khoan`,
   `khong_cho_trang` là những đại lượng chỉ quan sát được **từ bên trong, trong
   lúc đang chạy**. Nộp xong rồi mới đo là đo một hệ đã rảnh.

⛔ **Một `subprocess` mỗi giây là không chấp nhận được.** Bản nháp đầu định gọi
   `python -c` mỗi lần lấy mẫu — mỗi lần ~1 s khởi động, tức chính phép đo thành
   nguồn nhiễu lớn hơn thứ nó đo. Ở đây một `engine` duy nhất, poll 1 s.
"""
from __future__ import annotations

import threading
import time
from typing import Any


class BoLayMau(threading.Thread):
    """Chụp mỗi giây: lease theo tài nguyên **và theo tài khoản**, số người chờ."""

    def __init__(self, db_url: str, nhip_s: float = 1.0):
        super().__init__(daemon=True)
        self.db_url = db_url
        self.nhip_s = nhip_s
        self.mau: list[dict] = []
        self._dung = threading.Event()
        self._eng: Any = None

    def _engine(self):
        if self._eng is None:
            from sqlalchemy import create_engine

            self._eng = create_engine(self.db_url)
        return self._eng

    def run(self) -> None:
        from sqlalchemy import text

        eng = self._engine()
        t0 = time.monotonic()
        while not self._dung.wait(self.nhip_s):
            try:
                with eng.connect() as c:
                    hang = c.execute(text(
                        "SELECT resource, CAST(user_id AS varchar), COUNT(*), "
                        "SUM(CASE WHEN la_whale THEN 1 ELSE 0 END) "
                        "FROM execution_leases WHERE mode='stream' "
                        "GROUP BY resource, CAST(user_id AS varchar)")).all()
                    cho = c.execute(text(
                        "SELECT COUNT(*) FROM llm_waiters "
                        "WHERE trang_thai='cho'")).scalar()
                self.mau.append({
                    "t": round(time.monotonic() - t0, 2),
                    "lease": [{"res": r[0], "user": str(r[1])[:8], "n": int(r[2]),
                               "whale": int(r[3] or 0)}
                              for r in hang],
                    "tong_lease": sum(int(r[2]) for r in hang),
                    "dang_cho": int(cho or 0),
                })
            except Exception as e:  # noqa: BLE001 - lay mau hong khong duoc giet lo do
                self.mau.append({"t": round(time.monotonic() - t0, 2),
                                 "loi": str(e)[:120]})

    def dung(self) -> None:
        self._dung.set()

    # ── các đại lượng ma trận hỏi ────────────────────────────────────────
    def dai_luong(self) -> dict[str, Any]:
        """Rút các đại lượng `mong_doi` của ma trận ra từ chuỗi mẫu.

        ⚠️ Trả **thiếu khoá** khi không đủ dữ kiện, chứ không trả một số đoán.
           `chay._cham` biến khoá thiếu thành *"chưa chấm được"* — đúng thứ ta
           muốn, vì một con số đoán trông y hệt một con số đo.
        """
        co = [m for m in self.mau if "tong_lease" in m]
        if not co:
            return {}

        dinh = max(m["tong_lease"] for m in co)
        dinh_cho = max(m["dang_cho"] for m in co)

        # Suất tối đa MỘT tài khoản giữ được, **chỉ tính lúc có người khác chờ**
        # — vì trần tài khoản chỉ bật khi ấy. Tính cả lúc không ai chờ là đo
        # nhầm một kịch bản khác.
        moi_tk = 0
        for m in co:
            if m["dang_cho"] <= 0:
                continue
            theo_tk: dict[str, int] = {}
            for x in m["lease"]:
                theo_tk[x["user"]] = theo_tk.get(x["user"], 0) + x["n"]
            if theo_tk:
                moi_tk = max(moi_tk, max(theo_tk.values()))

        # Whale dong thoi toi da — cot `la_whale` co san tren lease.
        whale = max((sum(x.get("whale", 0) for x in m["lease"]) for m in co),
                    default=0)
        # Dinh lease cua MOT tai nguyen — J12 hoi dung con so nay: hai khoa cua
        # cung mot tai khoan KHONG duoc vuot tran cua mot card.
        dinh_res = 0
        for m in co:
            theo_res: dict[str, int] = {}
            for x in m["lease"]:
                theo_res[x["res"]] = theo_res.get(x["res"], 0) + x["n"]
            if theo_res:
                dinh_res = max(dinh_res, max(theo_res.values()))

        ra: dict[str, Any] = {"dinh_lease": dinh, "dinh_cho": dinh_cho,
                              "whale_toi_da": whale, "dinh_moi_tai_nguyen": dinh_res}
        from tools.nghiem_thu_van_hanh.kich_ban import TRAN_MOI_MODEL
        # ⭐ "Khoa khong cong suat" khong phai mot y kien — no la mot bat dang
        #    thuc do duoc: dinh cua MOT card khong duoc vuot tran cua card ay,
        #    bat ke tai di qua bao nhieu khoa.
        ra["khoa_khong_cong_suat"] = dinh_res <= TRAN_MOI_MODEL
        if moi_tk:
            ra["moi_tai_khoan_toi_da"] = moi_tk
            ra["tran_tai_khoan"] = moi_tk
        # Hai tài nguyên khác nhau cùng có lease ⇒ hai card chạy song song thật.
        for m in co:
            if len({x["res"] for x in m["lease"]}) >= 2:
                ra["resource_khac_nhau"] = True
                break
        # Mỗi tài khoản xuất hiện ít nhất một lần ⇒ không ai chờ trắng.
        thay = {x["user"] for m in co for x in m["lease"]}
        if len(thay) >= 2:
            ra["khong_cho_trang"] = True
        return ra

    def do_nha_suat(self, t_cat_s: float) -> dict[str, Any]:
        """Từ lúc khách CẮT tới lúc số lease thật sự tụt — thước đo của L-08.

        ⚠️ Đo mốc **tụt**, không đo mốc về 0: các lượt khác vẫn đang giữ suất,
           nên chờ tới 0 là chờ cả lô chạy xong và ta lại đo thời gian SINH.
        """
        co = [m for m in self.mau if "tong_lease" in m and m["t"] >= t_cat_s]
        if len(co) < 2:
            return {}
        dau = co[0]["tong_lease"]
        for m in co[1:]:
            if m["tong_lease"] < dau:
                return {"nha_lease_toi_da_s": round(m["t"] - t_cat_s, 2)}
        return {}
