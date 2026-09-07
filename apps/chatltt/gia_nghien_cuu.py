"""gia_nghien_cuu.py — giá của một vòng NGHIÊN CỨU. (H44 B6 bước 3)

## 🔴 Kết luận đi ngược §2 D3 của kế hoạch, và đây là lý do

`13_KE_HOACH_B6_NGHIEN_CUU.md` D3 viết: *"Báo giá TRƯỚC, và giá theo LƯỢT MODEL
THẬT… ước trần trước khi bấm, quyết toán theo số lượt thật sự chạy, hoàn phần
giữ dư"* — tức khuôn `gia_trich`: job **giữ** credit rồi **quyết toán**.

Khuôn ấy đúng cho `trich_tep` và **sai** ở đây, vì một sự thật đo được:

    platform_core/runtime_noi_bo/luong.py
      -> moi loi goi model GIU credit theo tran token, roi HOAN ve token that
         (`billing.updated {credit_giu, credit_thu, credit_hoan}`)

Vòng nghiên cứu không làm gì tốn tiền **ngoài** những lượt model ấy: nó đọc
`chatltt_doan` của chính người hỏi (một truy vấn CSDL) rồi ghép chữ. Nên nếu
job này cũng giữ-và-thu theo lượt, mỗi lượt bị **tính hai lần** — một lần ở
`runtime_noi_bo`, một lần ở đây.

⛔ Và `manifest.py` đã cảnh báo đúng câu này từ đầu: *"ChatLTT là **client** của
   ba năng lực đã có giá… Khai `job_types` ở đây là mời một sổ tiền thứ hai."*

⭐ Bài học `san-lam-tron-la-mot-tang-khac-voi-bang-gia` là bài học này: bảng giá
   đúng mà **tiền thu ra sai**. Câu phải hỏi không phải *"giá mỗi lượt bao
   nhiêu?"* mà *"một lượt điển hình bị trừ bao nhiêu, cộng hết mọi tầng?"*

⇒ `credit_cost` của job này là **0**, và số 0 ấy **không phải** một mặc định vô
  hại — nó là một khẳng định: *"tầng này không thu gì, tiền chảy ở tầng dưới"*.

## Nhưng 0 mở một lỗ khác, nên có một cửa THỨ HAI

`credit_cost = 0` nghĩa là job vào hàng đợi mà **không giữ chỗ**. Một tài khoản
0 credit vẫn nộp được, worker vẫn chạy, rồi lượt model đầu tiên trả `ThieuCredit`
— khách chờ vô ích và máy chủ làm không công. Đúng cái lỗ mà cửa credit của
`upload_sessions` sinh ra để bịt.

⇒ Cửa ấy chuyển sang **điều kiện trước khi nộp**: route từ chối khi số dư dưới
  `uoc_tran()`. Đó là một **điều kiện**, không phải một **giá** — nên nó không
  nằm trong sổ tiền, và nó không tính hai lần thứ gì.

## Ước trần đến từ đâu

Neo vào giá đã có thật, không bịa: `apps/ltt_llm` bán **400 credit / 1M token**.
Một lượt của vòng này mang ngữ cảnh vài nghìn ký tự nguồn:

    ~4.000 token vao + ~1.000 token ra = ~5.000 token
    5.000 x 400 / 1.000.000              = 2 credit

⚠️ Ước phải **cao hơn** thật, cùng luật `gia_trich.uoc_tran`: ước thấp thì khách
   bấm đồng ý rồi lượt hỏng giữa chừng vì hết tiền — hỏng **sau** khi đã hứa.
   Nên lấy **3**, và cộng một lượt cho bước tổng hợp cuối.

🟡 Đây là một **neo**, không phải một phép đo. Đo lại sau 20–50 lượt thật rồi
   chốt — cùng hạng mục M3 của B4 và §6 của P06.
"""
from __future__ import annotations

#: Ước credit cho MỘT vòng (kế hoạch → thu → trích). Xem docstring.
CREDIT_UOC_MOI_VONG = 3

#: Bước tổng hợp cuối cũng là một lượt model, và nó mang ngữ cảnh **dài nhất**
#: (toàn bộ nguồn đã thu). Đếm nó riêng thay vì gộp vào trần vòng.
CREDIT_UOC_TONG_HOP = 4

#: Phiên bản giá — đi vào bản ghi để đối soát. Chữ `tam` có chủ đích, cùng lý do
#: `gia_trich.PHIEN_BAN_GIA`: ngày chốt giá thật, mọi bút toán cũ lọc ra được.
PHIEN_BAN_GIA = "nghien-cuu-v0-tam"


def uoc_tran(tran_vong: int) -> int:
    """Credit ước **cao** cho một lượt nghiên cứu `tran_vong` vòng.

    Đây là số **hiện ra cho khách trước khi bấm** và là ngưỡng số dư route đòi.
    Nó KHÔNG được giữ và KHÔNG được thu — xem docstring đầu tệp.
    """
    n = max(1, int(tran_vong))
    return n * CREDIT_UOC_MOI_VONG + CREDIT_UOC_TONG_HOP


def credit_cost(params: dict) -> int:
    """Giá của job nghiên cứu: **0**, có chủ đích.

    ⛔ Đừng "sửa" số này thành một con số dương vì thấy nó trông như quên. Mọi
       credit của tính năng này chảy qua `runtime_noi_bo` theo từng lượt model,
       đã giữ và đã hoàn đúng token thật. Một số dương ở đây là **thu hai lần**.
    """
    return 0
