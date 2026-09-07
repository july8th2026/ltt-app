"""`MayThat` — nói chuyện với WanGP qua HTTP. **Chuyển tiếp, không diễn giải.**

## 🔴 User-Agent là bắt buộc, và đây là lý do

Đường tới C-CLOUD đi qua proxy của RunPod, mà proxy ấy nằm sau Cloudflare.
Cloudflare chặn User-Agent mặc định của `urllib` (`Python-urllib/3.x`) và trả
**HTTP 403 `error code: 1010`** — chặn theo chữ ký trình duyệt, **trước khi**
yêu cầu chạm tới pod.

Đây là kiểu hỏng khó lần nhất trong cả tuyến, vì mọi dấu hiệu đều chỉ sai chỗ:

- dịch vụ phía C-CLOUD **đang chạy đúng**
- log phía C-CLOUD **sạch không một dòng lỗi** — yêu cầu chưa từng tới nơi
- `curl` từ **cùng máy** lại trả 200

Đo 06/09/2026: bốn biến thể header xác thực đều 403; đổi mỗi User-Agent thì 200
ngay. `test_739` chốt cả chuỗi `Mozilla/5.0` lẫn chú thích này — vì mất lời giải
thích thì lần sau lại mất luôn cái header.

## Vì sao lớp này mỏng đến mức nhàm chán

Mỗi phép biến đổi đặt ở đây là một chỗ để hai bên hiểu khác nhau. Bản cũ
(`wangp_client.WanGPClient`) đã bắt đầu mỏng rồi dần mọc thêm: `KetQua.da_huy`
tự **dò chuỗi** `"cancelled"` trong thông điệp lỗi để đoán người dùng có bấm huỷ
không — một phép phân biệt **về tiền** đặt trên cách diễn đạt của thượng nguồn.

⇒ Nay cầu nối phơi thẳng `GenerationResult.cancelled` thành trường `huy`, và lớp
  này chỉ đọc nó.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from apps.lttvideo.cong.giao_uoc import LoiMay

#: Header mang khoá — để đường `GET` cũng xác thực được.
HEADER_KHOA = "X-LTTV-Key"

#: ⛔ Bắt buộc. Xem chú thích đầu tệp: thiếu nó là 403 `error code: 1010` với
#:   log phía pod hoàn toàn sạch.
UA_TRINH_DUYET = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)

#: Nạp media có thể là ảnh vài MB qua proxy — rộng hơn hẳn các đường khác.
CHO_NAP_MEDIA_S = 180.0
CHO_TAI_VE_S = 300.0
CHO_MAC_DINH_S = 30.0


class MayThat:
    """Hiện thực `May` qua HTTP tới `tools/wangp/dich_vu_ccloud.py`."""

    def __init__(self, goc: str, *, khoa: str = "", goi=None) -> None:
        """`goi` chỉ để phép kiểm tiêm hàm vận chuyển vào — mã sản phẩm không
        truyền. Không có nó thì mọi phép kiểm về lớp này phải mở socket thật,
        và một lớp chỉ kiểm được khi có mạng là một lớp sẽ không được kiểm.
        """
        self.goc = goc.rstrip("/")
        self.khoa = khoa
        self._tiem = goi

    # ── một chỗ duy nhất chạm mạng ─────────────────────────────────────────

    def _goi(self, method: str, duong: str, *, than: Any = None,
             tho: bytes | None = None, timeout: float = CHO_MAC_DINH_S,
             nhi_phan: bool = False) -> Any:
        # 🔴 Duong TIEM phai nam TRONG khoi bat loi, khong nam truoc no.
        #    Ban dau no nam truoc: mot ngoai le tu ham tiem thoat thang ra
        #    ngoai, khong duoc boc thanh `LoiMay` — tuc duong tiem hanh xu
        #    KHAC duong that. Mot diem tiem lam duoc dieu do thi moi phep kiem
        #    di qua no deu do mot he thong khong ton tai.
        try:
            if self._tiem is not None:
                ra = self._tiem(method, duong, than=than, tho=tho,
                                timeout=timeout, nhi_phan=nhi_phan)
                return ra if nhi_phan or ra is not None else {}
            url = f"{self.goc}{duong}"
            du_lieu = tho if tho is not None else (
                json.dumps(than).encode("utf-8") if than is not None else None)
            req = urllib.request.Request(url, data=du_lieu, method=method)
            req.add_header("Content-Type",
                           "application/octet-stream" if tho is not None
                           else "application/json")
            req.add_header("User-Agent", UA_TRINH_DUYET)
            if self.khoa:
                req.add_header(HEADER_KHOA, self.khoa)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                byte = r.read()
        except LoiMay:
            raise                       # da dung kieu roi, dung boc hai lan
        except urllib.error.HTTPError as e:
            try:
                chi_tiet = e.read().decode("utf-8", "replace")[:300]
            except Exception as e_doc:  # noqa: BLE001
                # ⛔ KHONG nuot. Than loi doc khong duoc thi noi ra — mot dong
                #    "khong doc duoc than loi" con dan duong hon mot chuoi rong,
                #    vi chuoi rong trong y het "may chu khong noi gi".
                chi_tiet = f"(khong doc duoc than loi: {type(e_doc).__name__})"
            goi_y = ""
            if e.code == 403:
                goi_y = (" — 403 o day thuong la Cloudflare chan User-Agent "
                         "(error code 1010), KHONG phai khoa sai; log phia pod "
                         "se sach vi yeu cau chua toi noi")
            raise LoiMay(
                f"{method} {duong}: HTTP {e.code}{goi_y} {chi_tiet}") from e
        except Exception as e:  # noqa: BLE001 — gom moi duong loi ve MOT kieu
            raise LoiMay(f"{method} {duong}: {type(e).__name__}: {e}") from e
        if nhi_phan:
            return byte
        tho_str = byte.decode("utf-8") if byte else ""
        if not tho_str:
            return {}
        try:
            return json.loads(tho_str)
        except json.JSONDecodeError as e:
            raise LoiMay(f"{method} {duong}: dap an khong phai JSON: "
                         f"{tho_str[:200]}") from e

    # ── tra cứu ────────────────────────────────────────────────────────────

    def liet_ke_model(self, **loc: Any) -> list[dict]:
        cap: list[tuple[str, str]] = []
        for k, v in loc.items():
            if v is None:
                continue
            for x in (v if isinstance(v, (list, tuple, set)) else [v]):
                cap.append((k, str(x)))
        q = f"?{urllib.parse.urlencode(cap)}" if cap else ""
        return list(self._goi("GET", f"/model{q}").get("model") or [])

    def so_do(self, model_type: str) -> dict | None:
        duong = f"/model/{urllib.parse.quote(model_type)}/so-do"
        return self._goi("GET", duong).get("so_do")

    def mac_dinh(self, model_type: str) -> dict:
        duong = f"/model/{urllib.parse.quote(model_type)}/mac-dinh"
        return dict(self._goi("GET", duong).get("mac_dinh") or {})

    def kha_dung(self, model_type: str) -> dict:
        duong = f"/model/{urllib.parse.quote(model_type)}/kha-dung"
        return dict(self._goi("GET", duong).get("kha_dung") or {})

    # ── đưa media vào ──────────────────────────────────────────────────────

    def nap_media(self, du_lieu: bytes, *, duoi: str = "png") -> str:
        if not du_lieu:
            raise LoiMay("nap_media: du lieu rong")
        duong = f"/nap_media?duoi={urllib.parse.quote(duoi)}"
        dap = self._goi("POST", duong, tho=du_lieu, timeout=CHO_NAP_MEDIA_S)
        d = (dap or {}).get("duong")
        if not d:
            raise LoiMay("/nap_media khong tra ve duong dan")
        return str(d)

    # ── chạy việc ──────────────────────────────────────────────────────────

    def gui_viec(self, settings: dict) -> str:
        """Gửi **nguyên văn** bộ tham số. Không thêm, không bớt, không sửa."""
        dap = self._goi("POST", "/submit",
                        than={"khoa": self.khoa, "settings": settings},
                        timeout=60.0)
        ma = (dap or {}).get("job_id")
        if not ma:
            raise LoiMay(f"/submit khong tra job_id: {json.dumps(dap)[:200]}")
        return str(ma)

    def tien_do(self, ma_viec: str) -> dict:
        return dict(self._goi("GET", f"/progress/{ma_viec}", timeout=15.0) or {})

    def ket_qua(self, ma_viec: str) -> dict:
        d = self._goi("GET", f"/result/{ma_viec}") or {}
        return {
            "tep": [str(x) for x in (d.get("generated_files") or [])],
            "loi": [str(x) for x in (d.get("errors") or [])],
            # 🔴 Doc THANG truong `huy` cua cau noi (= `GenerationResult.
            #    cancelled`). Ban cu do chuoi "cancelled" trong thong diep loi —
            #    mot phep phan biet VE TIEN dat tren cach dien dat thuong nguon.
            "huy": bool(d.get("huy")),
        }

    def huy(self, ma_viec: str) -> None:
        self._goi("POST", f"/cancel/{ma_viec}", than={"khoa": self.khoa})

    # ── lấy ra và dọn ──────────────────────────────────────────────────────

    def tai_ve(self, ma_viec: str, chi_so: int = 0) -> bytes:
        return self._goi("GET", f"/tai/{ma_viec}/{int(chi_so)}",
                         timeout=CHO_TAI_VE_S, nhi_phan=True)

    def don_dep(self, ma_viec: str) -> None:
        self._goi("POST", f"/cleanup/{ma_viec}", than={"khoa": self.khoa})
