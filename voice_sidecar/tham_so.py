"""
tham_so.py — tham số sinh mẫu của LTT VOICE. **MỘT chỗ duy nhất, có phiên bản.**

⛔ ĐÂY KHÔNG PHẢI NÚT VẶN CỦA KHÁCH (Q119). Không khai trong `params_schema`,
   không ra `api_contract`, không lên giao diện. Đổi một con số dưới đây là đổi
   thứ khách **nghe được**, nên nó phải đi qua cổng chất lượng V10 như đổi model.

🔴 HAI LÝ DO ĐỘC LẬP, cả hai đọc được từ mã upstream:

   ① `src/vieneu/v3_turbo_serve/engine.py` giữ

          self._graphs = {}   # (B, temperature, top_k, top_p) -> CudaGraphedFrame

      Mỗi tổ hợp mới = **một CUDA graph mới** + một bộ đệm tĩnh trên card + ba
      lượt warmup. Cho khách chỉnh ba tham số đó là mời họ làm nở cache graph
      trên GPU của ta cho tới khi hết VRAM.

   ② `temperature` cao làm **lệch tông giữa các đoạn** — upstream issue #173,
      "giọng đọc giữa các câu giống như cùng một người nhưng ở các tâm trạng
      hoặc cao độ hơi khác nhau".

   Hai lý do khác nhau hoàn toàn, cùng dẫn tới một quyết định. Nếu sau này ai đó
   phá được lý do ① (ví dụ upstream bỏ cache graph) thì lý do ② **vẫn còn**.

⚠️ Giá trị khởi điểm lấy đúng mặc định của SDK (`v3turbo.py::infer`), **không
   phải** một bộ tự nghĩ ra. Đường đúng để đổi: đo ở V10 rồi mới sửa, kèm tăng
   `PHIEN_BAN_THAM_SO`.
"""
from __future__ import annotations

#: Đổi bất cứ con số nào bên dưới thì **phải** đổi chuỗi này. Không có phiên bản
#: thì không đối chiếu được một tệp tiếng cũ với bộ tham số đã sinh ra nó.
PHIEN_BAN_THAM_SO = "ltt-voice-2026-08-30a"

#: Mặc định của SDK. Giữ nguyên cho tới khi có số đo nói khác.
TEMPERATURE = 0.8
TOP_K = 25
TOP_P = 0.95
REPETITION_PENALTY = 1.2

#: Trần frame cho một chunk. SDK mặc định 300; engine tự kẹp thêm theo độ dài
#: phoneme (`max_expected_frames`) nên đây chỉ là chặn trên tuyệt đối.
MAX_NEW_FRAMES = 300

#: Chia đoạn cấp engine. `config.yaml` upstream: `max_chars_per_chunk: 256`.
#: ⛔ Đây KHÁC với trần một lượt sinh (`TRAN_KY_TU_MOT_LUOT` dưới đây). Một lượt
#:    gồm NHIỀU chunk; trần chunk là của model, trần lượt là của chất lượng.
MAX_CHARS_CHUNK = 256

#: 🔴 TRẦN CHẤT LƯỢNG, KHÔNG PHẢI TRẦN HIỆU NĂNG (Q119).
#:
#:    Upstream issue #168, người thử báo ngày 06/07 **sau khi tác giả đã sửa
#:    drift**: *"lỗi sẽ xuất hiện nhiều khi xử lý text dài khoảng 3.000 ký tự trở
#:    lên. Giọng Xuân Vĩnh sẽ dễ bị đổi giọng khác (chuyển sang giọng như miền
#:    Trung). Các giọng khác đôi lúc đọc sang tiếng khác như Thái... chỉ một đoạn
#:    rồi quay lại Việt."*
#:
#:    1.500 là **một nửa** ngưỡng đó — biên an toàn cho tới khi V1/V10 đo được
#:    ngưỡng thật trên chính bộ giọng của ta.
#:
#: ⛔ Đừng nới cho tiện. Dài hơn thì đi đường long-form nhiều lượt sinh.
TRAN_KY_TU_MOT_LUOT = 1500

#: Trần số văn bản trong một lượt batch. `max_batch_size` mặc định của SDK là 32;
#: giữ thấp hơn cho tới khi đo được VRAM thật của từng bậc batch.
TRAN_SO_VAN_BAN_BATCH = 8

#: Tần số lấy mẫu của v3 Turbo. Đọc lại từ engine lúc chạy để chốt, hằng số này
#: chỉ dùng cho phép kiểm và cho thông điệp lỗi.
SAMPLE_RATE = 48_000


def bo_tham_so() -> dict:
    """Bộ tham số truyền thẳng vào `infer` / `infer_stream` / `infer_batch`."""
    return {
        "temperature": TEMPERATURE,
        "top_k": TOP_K,
        "top_p": TOP_P,
        "repetition_penalty": REPETITION_PENALTY,
        "max_new_frames": MAX_NEW_FRAMES,
        "max_chars": MAX_CHARS_CHUNK,
    }


def cong_bo() -> dict:
    """Thứ `/v1/capabilities` công bố. Không lộ giá trị — chỉ lộ PHIÊN BẢN.

    Vì sao không lộ giá trị: một tích hợp nhìn thấy `temperature=0.8` sẽ bắt đầu
    coi nó là hợp đồng, và ngày ta đổi nó sau một lượt đo là ngày ta phá hợp đồng
    mà không hề khai.
    """
    return {
        "phien_ban_tham_so": PHIEN_BAN_THAM_SO,
        "tran_ky_tu_mot_luot": TRAN_KY_TU_MOT_LUOT,
        "tran_so_van_ban_batch": TRAN_SO_VAN_BAN_BATCH,
        "max_chars_chunk": MAX_CHARS_CHUNK,
    }
