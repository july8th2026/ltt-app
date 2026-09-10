"""
tham_so_cong_khai.py — vài hằng số mà CẢ HAI phía cùng phải biết.

🔴 VÌ SAO TỆP NÀY TỒN TẠI THAY VÌ IMPORT `voice_sidecar.tham_so`:

   `apps/ltt_voice/` chạy trong **venv nền tảng**; `voice_sidecar/` chạy trong
   **venv cách ly** có torch và vieneu. Một `import voice_sidecar.tham_so` từ
   manifest sẽ kéo theo cả cây phụ thuộc đó vào tiến trình web và worker — tức
   đúng thứ mà venv cách ly sinh ra để tránh.

   Nên hằng số dùng chung sống ở đây, và `tests/test_331_ltt_voice_tham_so.py`
   chốt hai bên khớp nhau. Hai bản sao không có phép kiểm là hai bản sao sẽ lệch;
   hai bản sao **có** phép kiểm là một hợp đồng.
"""
from __future__ import annotations

#: Trần của MỘT LƯỢT SINH. Phải khớp `voice_sidecar.tham_so.TRAN_KY_TU_MOT_LUOT`.
#:
#: Đây là TRẦN CHẤT LƯỢNG (Q119), không phải trần hiệu năng: upstream #168 báo
#: giọng bắt đầu trôi từ khoảng 3.000 ký tự. Đo 30/08 cho thấy 3.000 ký tự vẫn
#: SINH RA ĐƯỢC (17,6 giây, không lỗi) — nên con số này không đến từ giới hạn kỹ
#: thuật, nó đến từ chỗ chất lượng bắt đầu tụt. Nới nó phải qua cổng V10.
TRAN_MOI_LUOT_SINH = 1500

#: Trần của MỘT YÊU CẦU của khách.
#:
#: 🔴 HAI TRẦN NÀY LÀ HAI THỨ KHÁC NHAU, và trước 31/08/2026 chúng là một con số.
#:
#:    Hệ quả của việc gộp: văn bản 3.000 ký tự bị **từ chối**, trong khi chính
#:    thông điệp lỗi của cổng đã nói *"Van ban dai hon phai di duong long-form
#:    nhieu luot sinh"* — con đường ấy chưa bao giờ được xây. `chia_doan()` có
#:    sẵn trong `text_pipeline.py` và **không được gọi ở đâu cả**; `jobs.py` gán
#:    cứng `so_doan=1`.
#:
#: ⭐ Tách hai trần ra thì mỗi con số nói đúng một điều:
#:      · `TRAN_MOI_LUOT_SINH`   — model đọc liền được bao nhiêu trước khi trôi
#:      · `TRAN_KY_TU_CONG_KHAI` — khách gửi được bao nhiêu trong một lần
#:    Yêu cầu dài hơn một lượt thì **chia rồi ghép**, không từ chối.
#:
#: ✅ MỞ 03/09/2026, VÀ CON SỐ MỚI KHÔNG CÒN NÓI VỀ MODEL NỮA.
#:
#: 🔴 ĐÂY LÀ CHỖ QUAN TRỌNG NHẤT: 1.500 là con số **của model** (chỗ giọng bắt
#:    đầu trôi). 100.000 là con số **của tài nguyên** (một job giữ GPU bao lâu
#:    thì còn công bằng với người khác). Đổi một trần cứng lấy một trần cứng
#:    khác thì vô nghĩa; đổi một trần CHẤT LƯỢNG lấy một trần NGÂN SÁCH mới là
#:    gỡ đúng thứ.
#:
#:    Trần của model vẫn còn nguyên và vẫn đúng — nó là `TRAN_MOI_LUOT_SINH` ở
#:    trên. Nó chỉ không còn **rò ra** thành trần của sản phẩm, vì
#:    `apps/ltt_voice/ban_doc_dai.py` hấp thụ nó: bài dài chia thành nhiều lượt
#:    ≤ trần ấy, mỗi lượt một artifact riêng trên đĩa, rồi ghép.
#:
#: ⭐ BẰNG CHỨNG (03/09, `tools/do_bai_dai.py`, sidecar dựng từ worktree):
#:
#:      chi so        1400(1 doan)   1500(2)   3000(3)   5000(4)   10000(7)
#:      CER               0,1121      0,0915    0,0897    0,0980    0,1077
#:      WER               0,2037      0,1969    0,1905    0,1906    0,2050
#:      ty le phu         0,9401      0,9630    0,9605    0,9528    0,9534
#:      F0 trung vi         91,8        89,7      89,7      90,8      90,8
#:      ty le hong             0           0         0         0         0
#:      RTF                0,214       0,199     0,168     0,163     0,152
#:
#:    Bản GHÉP **tốt hơn** bản một lượt trên mọi chỉ số ASR, ở mọi độ dài. Và
#:    RTF *cải thiện* theo độ dài — chi phí khởi động chia cho nhiều việc hơn.
#:
#:    Tương đồng người nói, so với **sàn nhiễu của chính nó** (cắt đôi từng đoạn
#:    rồi so hai nửa — hai nửa chắc chắn là cùng người, nên đó là mức giống nhau
#:    nhất mà thước đo này đạt được):
#:
#:      doan xau nhat <-> doan 1   0,9742   0,9797   0,9760   0,9710
#:      san nhieu (xau nhat)       0,9716   0,9650   0,9687   0,9684
#:
#:    Ở **mọi** độ dài, đoạn giống đoạn đầu ít nhất vẫn giống hơn hai nửa của
#:    cùng một đoạn. Độ dốc theo chỉ số đoạn đổi dấu giữa các bài ⇒ dao động,
#:    không phải một chiều.
#:
#: ⭐ VÌ SAO SUY RỘNG TỪ 10.000 LÊN 100.000 LÀ HỢP LỆ — lập luận về CƠ CHẾ, không
#:    phải về đường cong:
#:
#:      đường sinh **không mang trạng thái nào giữa các đoạn**. Mỗi đoạn là một
#:      lượt `infer` độc lập, cùng tham chiếu, cùng tham số. Không có gì tích
#:      luỹ, nên đoạn thứ 60 không thể khác đoạn thứ 7 vì lý do "bài dài hơn".
#:
#:    Số đo xác nhận đúng dự đoán ấy. Nếu số đo NGƯỢC lại thì mới là chuyện lớn,
#:    vì khi đó có một trạng thái ẩn mà ta không biết. Nó không ngược.
#:
#: ⚠️ GIỚI HẠN CỦA BẰNG CHỨNG: **một vòng đo**, không phải nhiều vòng như
#:    `tools/cong_chat_luong_voice.py` đòi để rút dung sai từ chính số đo. Bốn
#:    tài liệu độc lập và 17 đoạn cùng chỉ một hướng nên kết luận đứng được,
#:    nhưng ĐỪNG viết "đã qua cổng V10" — nó chưa qua.
#:
#: ⛔ VÀ MỘT ĐỐI CHỨNG ĐÃ KHÔNG CHẠY. `do_bai_dai.py` khai ba đối chứng; mục ③
#:    ("cùng văn bản, khác vị trí") trả rỗng ở cả bốn bài, vì phép chia cân bằng
#:    gộp đoạn văn khác đi nên không đoạn nào trùng độ dài. Chạy được **hai**.
#:
#: ── 100.000 ĐẾN TỪ ĐÂU ──────────────────────────────────────────────────────
#:
#:    Đo được: **19,86 ký tự mỗi giây audio**, RTF **0,152**
#:          ⇒ **0,00763 giây GPU cho mỗi ký tự**
#:
#:    Ba ràng buộc, và trần là cái NGẶT NHẤT:
#:
#:      thoi gian job (max_runtime_s = 3600, xem manifest)  ~ 236.000 ky tu
#:      RIFF/WAV 2 GiB (~6,2 gio audio)                     ~ 444.000 ky tu
#:      cong bang GPU: CHUA co bo xep lich uu tien          <- rang buoc that
#:
#: 🔴 Ràng buộc thứ ba mới là thứ chọn con số. Ở 100.000 ký tự một job giữ GPU
#:    khoảng 13 phút ở RTF đo được (≈23 phút nếu GPU chậm gấp đôi). Chưa có hàng
#:    đợi ưu tiên, nên suốt ngần ấy nó **chặn mọi người khác**. Mở tới trần định
#:    dạng (444.000 ≈ gần một giờ) là cố ý giao cho một người khả năng làm nghẽn
#:    cả hệ thống.
#:
#: ⭐ ĐIỀU KIỆN NÂNG TIẾP — ghi ra để người sau kiểm được mà không phải tin lời:
#:      · có bộ xếp lịch ưu tiên (yêu cầu tương tác chen trước job nền), HOẶC
#:      · một GPU được cấp riêng cho làn tài liệu dài
#:    Khi ấy trần kế tiếp là **định dạng tệp**, và trước khi chạm nó phải có
#:    RF64/WAVE64: WAV thường tràn ở ~2 GiB và nó hỏng **im lặng** — trình phát
#:    vẫn mở được phần đầu.
#:
#: ⚠️ TÀI LIỆU DÀI HƠN 100.000 KHÔNG BỊ TỪ CHỐI — nó đi đường **Dự án**: 200
#:    khối, mỗi khối một job riêng. Đó đúng là hình dạng mà một cuốn sách nên có.
TRAN_KY_TU_CONG_KHAI = 100_000


#: Số lần thử cho một job giọng. **Không phải một con số tuỳ ý.**
#:
#: 🔴 ĐO THẬT 02/09/2026, giết cổng giọng rồi nộp một lượt đọc:
#:
#:      max_attempts = 3  ->  cua so thu lai ~30 giay  (cho 10s, roi 20s)
#:      job chet han sau  ~45 giay, trang thai `error`
#:
#:    Nhưng **một lần deploy dài hơn thế nhiều**: dừng `LTTStudioVoice`, chép
#:    `app\`, khởi động lại, và riêng phần **nạp model** đã đo được **39,9 s**
#:    (nguội) tới **73,1 s**. Tức mọi lượt đọc đang bay khi deploy đều chết.
#:
#: ⭐ Bản sửa 31/08 (`LoiHaTang`) làm job **được thử lại** thay vì hỏng ngay —
#:    đúng, nhưng chưa đủ: nó sửa việc **phân loại** lỗi mà không sửa **kết
#:    quả**. Ba lần thử trong 30 giây vẫn thua một lần khởi động lại.
#:
#: ⚠️ 5 chứ không phải 8. Cửa sổ 5 lần là 10+20+40+80 = **~150 giây**, gấp đôi
#:    lần nạp model chậm nhất đã đo. Nhiều hơn nữa thì một cổng hỏng THẬT bắt
#:    khách chờ năm phút mới được báo — và với một job mà đường bình thường chỉ
#:    mất 12–25 giây, im lặng năm phút là một kiểu hỏng khác.
#:
#: ⛔ Đừng đổi nó thành "thử lại mãi". `DangBanTam` (429) đã đi đường
#:    `defer_resource` — về hàng đợi **không tiêu lượt thử** — và đó là đường
#:    dành cho *bận*. Một cổng chưa cài mà cứ xếp lại vô hạn thì job nằm
#:    `queued` mãi mãi, không ai được báo: đúng cái hỏng mà `manifest.py` cảnh
#:    báo về làn worker `voice`.
SO_LAN_THU_JOB = 5
#: 🔴 ENGINE NÀY CẦN TA CHUẨN HOÁ TỚI ĐÂU (U-15 / T-07).
#:
#:    Hai vế, và chúng bật vì **hai lý do khác nhau** — đó là toàn bộ điểm của
#:    việc tách chúng ra thay vì dùng một cờ `chuan_hoa=True`:
#:
#:      "phien_am"  upstream #168 báo engine đọc `ch` thành `tr` ở một số từ,
#:                  và tên riêng thì không bảng nào đoán trước được.
#:      "doc_so"    engine đọc `1.250.000` theo từng chữ số.
#:
#: ⚠️ ĐỂ Ở ĐÂY, KHÔNG Ở `text_pipeline.py`, và đó không phải chuyện gọn gàng.
#:    Tệp này là chỗ giữ **sự thật về engine đang chạy** — cùng chỗ với
#:    `TRAN_MOI_LUOT_SINH` và `SO_LAN_THU_JOB`. Ngày có engine thứ hai, khuôn
#:    của nó nằm cạnh tham số của nó, chứ không nằm lẫn trong bộ chuẩn hoá.
#:
#: ⛔ ĐỔI KHUÔN LÀ ĐỔI TIỀN. `manifest._gia()` đếm ký tự **sau** chuẩn hoá:
#:    tắt `doc_so` làm hoá đơn nhỏ đi, bật `doc_so_tran` làm nó to lên. Nên nó
#:    không bao giờ là một tuỳ chọn của khách.
KHUON_CHUAN_HOA = {"phien_am": True, "doc_so": True, "doc_so_tran": False}
