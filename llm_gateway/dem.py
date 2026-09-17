"""
dem.py — số cộng dồn theo NHÓM KẾT CỤC, thứ duy nhất chỉ cổng này nhìn thấy.

⭐ VÌ SAO KHÔNG DỰNG MỘT HỆ QUAN TRẮC. Vì phần lớn thứ cần đo **đã được đếm sẵn
   ở tầng dưới**, và việc của module này là **không** đếm lại chúng:

     llama.cpp `/metrics`            token vào/ra, prefill/decode, KV cache,
                                     slot bận, tỉ lệ chấp nhận suy đoán
     llama-swap `/api/metrics/*`     vòng đời model, hoạt động, bền qua restart
     llama-swap `/api/hardware`      GPU/VRAM
     `gioi_han.trang_thai()`         đồng thời, `giu_lau_nhat_giay`
     `/health` -> `gpu`, `trong_tai` trạng thái tức thời

   Còn lại đúng một khoảng trống, và nó là khoảng trống **thật**: mọi lượt cổng
   **từ chối** thì llama.cpp *không bao giờ thấy*. Một buổi mà 89/117 lượt của
   một khách ăn 429 sẽ không để lại **một dấu vết nào** trong `/metrics` của
   engine — vì không lượt nào chạm tới engine.

🔴 ĐÓ KHÔNG PHẢI GIẢ THUYẾT. Sự cố 31/08 đúng là như vậy: một suất treo,
   `max_dong_thoi=1`, cổng trả 429 suốt sáu giờ trong khi GPU rảnh và model chưa
   nạp. `gioi_han` nay có `giu_lau_nhat_giay` để nhìn ra **trạng thái**; module
   này thêm vế còn thiếu — **lịch sử**: "hôm nay đã từ chối bao nhiêu lượt, vì
   cái gì". Trạng thái nói *đang* hỏng; số cộng dồn nói *đã* hỏng bao lâu.

⛔ CHỈ ĐẾM, KHÔNG GIỮ NỘI DUNG. Không prompt, không phản hồi, không tên khách,
   không thân request. §27 của chương trình đặt mặc định TẮT cho việc bắt nội
   dung, và llama-swap có sẵn `/api/captures/*` mà ta **cố ý không dùng**.
   Một con số không rò rỉ được gì; một prompt thì rò rỉ tất cả.

⛔ KHÔNG BỀN QUA KHỞI ĐỘNG LẠI, VÀ ĐÓ LÀ CHỦ Ý. Bền nghĩa là một tệp/CSDL trên
   máy B, tức một thứ nữa để hỏng, để đầy đĩa, để khoá. llama-swap **đã** có kho
   hoạt động bền (`/api/metrics/activity`); nếu cần lịch sử dài thì lấy ở đó,
   đừng dựng kho thứ hai. Ở đây chỉ cần "từ lần khởi động này tới giờ".
"""
from __future__ import annotations

import threading

#: Các nhóm kết cục. **Danh sách đóng** — thêm nhóm mới thì thêm ở đây, đừng
#: truyền một chuỗi tuỳ ý vào `cong()`.
#:
#: ⭐ VÌ SAO TÁCH BA LOẠI 429. Với máy A cả ba đều là `BanError` và **đó là
#:    đúng** — nó không được `danh_dau_loi` cho lượt nào trong ba. Nhưng với
#:    người trực thì ba nhóm ấy đòi ba hành động khác hẳn nhau:
#:
#:      ban_day       cổng hết suất  -> lượt trước chưa trả suất, hoặc khách dồn
#:      ban_trong_tai máy B bận      -> ComfyUI/video đang giữ card, chờ là đúng
#:      ban_card      card chưa sạch -> ComfyUI giữ VRAM và không nhả
#:
#:    Gộp thành một con số "429" là vứt đi đúng phần trả lời được câu *"tôi phải
#:    làm gì bây giờ"*.
NHOM = (
    "ok",             # 2xx, cửa đồng bộ
    "ok_stream",      # 2xx, cửa SSE (suất còn giữ tới khi luồng hết)
    "ban_day",        # 429 — hàng rào đồng thời của chính cổng
    "ban_trong_tai",  # 429 — trọng tài nói máy B bận
    "ban_card",       # 429 — dọn card không đạt ngưỡng sạch
    "ban_pool",       # 429 - be KV cua model day (hoac luot khong khai token)
    # "ban_whale" DA GO (phuong an C buoc 3, O-01): cong khong con khoa whale.
    "ban_vram",       # 429 - VRAM trong cua card duoi san (5060 Ti, D06)
    "qua_tran",       # 413 — vượt ngân sách token/ảnh
    "khong_co_model", # 404 — model không mở (fail-closed)
    # 499 — HỦY theo yêu cầu (`POST /v1/huy`). **KHÔNG** phải hỏng, và cũng
    # không phải "bận": cổng đã nhận, đã chạy, rồi được bảo là thôi.
    #
    # ⚠️ NÓ RƠI VÀO `tu_choi` CỦA `trang_thai()`, vì tổng ấy suy ra từ "không
    #    phải `ok*`". Đã cân nhắc đặt tên `ok_huy` để nó vào `phuc_vu` và **bỏ**:
    #    một lượt hủy không hề được phục vụ, nên đếm nó là phục vụ là nói sai về
    #    phía dễ chịu. Cái giá của lựa chọn này là `ti_le_tu_choi` cao lên khi
    #    khách hay bấm dừng — nên ai đọc tỉ lệ ấy phải xem `theo_nhom["huy"]`
    #    ngay cạnh, và dòng này ở đây để họ biết mà xem.
    "huy",
    "het_gio",        # 504 — thượng nguồn không trả lời kịp. **KHÔNG** phải hỏng.
    "loi_thuong_nguon",  # 502 — llama-swap/llama-server hỏng hoặc không với tới
)


class Dem:
    """Bộ đếm an toàn nhiều luồng.

    ⚠️ PHẢI CÓ KHOÁ. `uvicorn` chạy các endpoint **đồng bộ** trong một
       threadpool, nên hai yêu cầu cộng cùng lúc là chuyện bình thường chứ không
       phải trường hợp hiếm. `+= 1` trên `dict` của Python *thường* nguyên tử
       nhờ GIL, nhưng "thường" không phải một hợp đồng — và cái ta đang đếm
       chính là thứ người ta sẽ dùng để phán đoán lúc sự cố.
    """

    __slots__ = ("_khoa", "_so", "_ttft_tong", "_ttft_dem", "_ttft_max")

    def __init__(self) -> None:
        self._khoa = threading.Lock()
        self._so = {ten: 0 for ten in NHOM}
        # TTFT — thời gian tới byte đầu tiên, **như khách thấy**.
        self._ttft_tong = 0.0
        self._ttft_dem = 0
        self._ttft_max = 0.0

    def cong(self, nhom: str) -> None:
        if nhom not in self._so:                 # sai tên = lỗi lập trình
            raise KeyError("nhom la: " + ", ".join(NHOM))
        with self._khoa:
            self._so[nhom] += 1

    def ghi_ttft(self, giay: float) -> None:
        """Ghi một lượt TTFT.

        🔴 VÌ SAO ĐO Ở ĐÂY CHỨ KHÔNG DÙNG SỐ CỦA llama.cpp. `/metrics` của engine
           đo từ lúc **nó** nhận việc. Nhưng thứ khách chịu còn gồm ba khoản
           engine không bao giờ thấy:

             * chờ suất ở hàng rào đồng thời
             * dọn card (`bao_dam_sach` chờ tới **18 giây**)
             * llama-swap nạp/đổi hồ sơ (đo được tới **2,5 phút**)

           Một TTFT 150 giây mà engine báo "prefill 4 giây" thì con số của engine
           đúng và **vô dụng** — nó trả lời một câu hỏi khác. Đây là chỗ duy
           nhất nhìn thấy cả ba khoản kia.
        """
        if giay < 0:
            return
        with self._khoa:
            self._ttft_tong += giay
            self._ttft_dem += 1
            if giay > self._ttft_max:
                self._ttft_max = giay

    def trang_thai(self) -> dict:
        with self._khoa:
            so = dict(self._so)
            dem, tong, cao = self._ttft_dem, self._ttft_tong, self._ttft_max
        # ⛔ ĐỪNG LIỆT KÊ LẠI TAY. Bản cũ gõ bảy tên ở đây, và ngày thêm ba nhóm
        #    429 (`ban_pool`/`ban_whale`/`ban_vram`, Dual-model 4.2 — `ban_whale`
        #    đã gỡ ở phương án C) thì `tu_choi`
        #    sẽ **đếm thiếu** — một tỉ lệ từ chối thấp giả, tức đúng chiều làm
        #    người trực yên tâm sai. Suy ra từ `NHOM`: phục vụ là `ok*`, còn lại
        #    là từ chối, nên một nhóm mới không thể lọt khỏi tổng.
        phuc_vu = so["ok"] + so["ok_stream"]
        tu_choi = sum(v for k, v in so.items() if not k.startswith("ok"))
        tong_luot = phuc_vu + tu_choi
        return {
            "theo_nhom": so,
            "phuc_vu": phuc_vu,
            "tu_choi": tu_choi,
            # ⭐ Tỉ lệ, vì con số tuyệt đối không nói được gì nếu không biết mẫu
            #    số. "300 lượt 429" là thảm hoạ trên 320 lượt và là bình thường
            #    trên 30.000.
            "ti_le_tu_choi": round(tu_choi / tong_luot, 4) if tong_luot else None,
            "ttft": {
                "so_luot": dem,
                "trung_binh_giay": round(tong / dem, 2) if dem else None,
                "cao_nhat_giay": round(cao, 2) if dem else None,
            },
        }


def boc_do_ttft(luong, dem: Dem, bat_dau: float, bam_gio, ghi_moc=None):
    """Bọc một luồng SSE để ghi TTFT khi **khối đầu tiên** đi qua.

    `bat_dau` là mốc **lúc yêu cầu vào cổng**, không phải lúc mở luồng thượng
    nguồn — xem `Dem.ghi_ttft`: chờ suất, dọn card và nạp model đều nằm trước
    lúc mở luồng, và chúng chính là phần khách chịu mà engine không thấy.

    ⛔ PHẢI BỌC **TRONG** `boc_nhip_tim`, KHÔNG PHẢI NGOÀI.

       `nhip_tim` chèn một chú thích SSE mỗi 15 giây **trong lúc prefill**, tức
       nó phát byte **trước** khi model sinh token đầu tiên. Bọc ở ngoài nó thì
       "khối đầu tiên" ta thấy sẽ là một nhịp tim, và TTFT của **mọi** lượt dài
       sẽ ra đúng ~15 giây — một con số trông rất ổn định và hoàn toàn vô nghĩa.

       ⚠️ Sai kiểu đó không bao giờ tự lộ ra: nó không làm hỏng gì, không có lỗi
          nào, chỉ có một phép đo luôn luôn trả lời sai. Đó là lý do nó được
          viết ra đây chứ không để trong đầu người nối dây.

    ⛔ KHÔNG ĐƯỢC LÀM HỎNG LUỒNG. Lớp mỏng nhất có thể: `yield` lại đúng thứ nhận
       được, không phân tích, không gom, không sửa. `upstream.stream` đã ghi lý
       do — một harness cộng đồng dùng regex cắt delta đã làm mất chữ giữa dòng
       và người ta đổ lỗi cho engine.

    🔴 VÀ PHẢI CHUYỂN TIẾP `close()`. `nhip_tim` gọi `getattr(luong, "close")()`
       để bảo thượng nguồn dừng sinh chữ. Chèn một generator vào giữa mà không
       chuyển tiếp thì `close()` chỉ ném `GeneratorExit` vào **lớp này**; vòng
       `for` bị bỏ dở và `LuongUpstream.close()` **không bao giờ chạy** — tức
       `llama-server` sinh tiếp cho một yêu cầu không còn ai đọc.

       Đó đúng hình dạng sự cố 31/08 (một đường dọn dẹp phụ thuộc vào việc ai đó
       lặp hết generator). `finally` dưới đây là cùng khuôn `nhip_tim._di` dùng.

    ⭐ `ghi_moc` — CÙNG phép đo, hai người đọc. `dem` cộng dồn (trung bình, cao
       nhất, cho `/health`); `ghi_moc` nhận con số của **lượt này** để nó vào
       đúng dòng sổ của lượt ấy (`so_luot.Luot.ghi_ttft`). Đo hai lần ở hai chỗ
       là cách chắc chắn nhất để hai con số lệch nhau; ở đây chỉ có một phép đo,
       và nó được phát cho hai nơi.
    """
    dau_tien = True
    try:
        for khoi in luong:
            if dau_tien:
                dau_tien = False
                giay = bam_gio() - bat_dau
                dem.ghi_ttft(giay)
                if ghi_moc is not None:
                    ghi_moc(giay)
            yield khoi
    finally:
        dong = getattr(luong, "close", None)
        if dong is not None:
            dong()
