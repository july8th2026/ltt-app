# PLAN TRIỂN KHAI V1 — CHI TIẾT

Ngày 07/09/2026. **Tệp này thay bốn bản plan trước** (xem §7).

Số liệu: **không chép vào đây** — ở `DU_LIEU_DA_DO.md`.
Quyết định sản phẩm: `QUYET_DINH_DA_KHOA_V1.md` (đã sửa A5 ở
`SOAT_TINH_NANG_WANGP_VA_GUI.md` §1).

---

## 0. Nguyên tắc xếp thứ tự — **gom việc cần GPU lại**

Mỗi lần bật pod tốn **~9 phút** và mang **rủi ro không thuê được card**
(06/09: hơn một giờ). Nên thứ tự không xếp theo "dễ trước", mà theo:

> **Mọi việc cần pod dồn vào ít lượt bật nhất. Mọi việc không cần pod làm trước
> và làm hết.**

### 🔴 Một phụ thuộc tôi ghi SAI hôm qua, và đã sửa

Bảng việc hôm qua ghi *"V1 — ảnh chụp `metadata` 226 model — ❌ không cần GPU"*.

**Sai.** `metadata` **không** nằm trong `defaults/*.json`; nó do
`init_model_def()` + `family_handler.query_model_def()` **tính ra lúc chạy**
(`wgp.py:3256`). Muốn có nó thì phải **chạy WanGP**.

⇒ Ảnh chụp `metadata` chuyển sang **lượt pod**, gộp cùng nâng bộ và tải model.
Tự tính lại `metadata` ngoại tuyến là **chép logic thượng nguồn** — đúng thứ
luật cấm.

---

## 1. Bản đồ phụ thuộc

```
T0 nang bo pod (CHO DUYET)
      |
      +--> T1 anh chup `metadata` 226 model      \
      +--> T2 tai i2v_2_2 + vace_14B              |  MOT luot pod
      +--> T3 tai bo mo rong prompt (Qwen3.8-27B) |
      +--> T4 do lai: TF32 + --compile + teacache /
                |
   (khong can pod, lam SONG SONG ngay tu bay gio)
      T5 dieu phoi vien pod        T6 lich su + tien do + huy
      T7 dinh media vao composer   T8 thao tac thu 7 `/hau_ky`
      T9 giu 3 ngay                T10 do dai 15s
                |
                v
            T11 nghiem thu E2E  (can pod)
```

---

## 2. Việc **không cần pod** — làm ngay

### T5 — Điều phối viên pod

**Tệp**
- Tạo: `apps/lttvideo/dieu_phoi.py`
- Sửa: `apps/lttvideo/jobs.py`
- Test: `tests/test_727_lttvideo_dieu_phoi.py`

**Giao diện**
- Dùng: `WanGPClient.health()`
- Cung cấp:
  ```python
  class TrangThaiMay(str, Enum):
      TAT = "tat"; DANG_BAT = "dang_bat"; SAN_SANG = "san_sang"; KHONG_CO_CARD = "khong_co_card"

  class DieuPhoi:
      def __init__(self, *, api, pod_id: str, client, cho_toi_da_s: float = 900.0) -> None: ...
      def bat_va_cho(self) -> TrangThaiMay: ...
      def tat_neu_ranh(self) -> bool: ...
  ```

**Bước**
1. Viết test: `bat_va_cho` trả `KHONG_CO_CARD` khi API tạo pod báo hết GPU — **không** ném lỗi, vì `B3` cần một trạng thái để hoàn credit.
2. Chạy test, thấy đỏ.
3. Viết `DieuPhoi` tối thiểu: gọi `start`, rồi hỏi `/health` tới khi `ok` hoặc hết `cho_toi_da_s`.
4. Test xanh.
5. Test: chờ quá hạn ⇒ trả `TAT`, **không** treo. Trần mặc định 900 giây (đo được ~530 + biên).
6. Test: `tat_neu_ranh()` **không** tắt khi còn job trong sổ.
7. Commit.

⛔ `DieuPhoi` **không** được gọi `stop` khi còn job đang chạy — đó là mất cả lượt
sinh và cả tiền của khách.

---

### T6 — Lịch sử · tiến độ · huỷ

**Tệp**
- Tạo: `apps/lttvideo/tables.py` (`table_prefix` trong manifest)
- Sửa: `apps/lttvideo/routes.py`, `server/templates/lttvideo.html`
- Test: `tests/test_728_lttvideo_lich_su.py`

**Bảng** (`C3`: lưu prompt · `C2`: giữ 3 ngày)
```python
class LtvVideoJob:
    id: int; nguoi_dung_id: int; job_wangp: str
    prompt: str                    # C3
    khoa_r2: str | None
    trang_thai: str                # cho | dang_chay | xong | huy | hong
    tao_luc: datetime
    het_han_luc: datetime          # tao_luc + 3 ngay  (C2)
    credit_giu: int; credit_tru: int
```

**Bước**
1. Test: tạo job ⇒ `het_han_luc` đúng **3 ngày** sau `tao_luc`.
2. Đỏ → viết bảng → xanh.
3. Test: route lịch sử **chỉ** trả job của chính người dùng (chốt rò rỉ chéo).
4. Test: `/progress` của LTT chuyển tiếp `phase` + `current_step`/`total_steps`.
5. Test: huỷ ⇒ `trang_thai == "huy"` và `credit_tru == 0`.
6. GUI: bảng lịch sử + thanh tiến độ + nút Huỷ.
7. Kiểm bằng trình duyệt thật (luật CLAUDE.md mục 5).
8. Commit.

---

### T7 — Đính media vào composer

**Tệp**
- Sửa: `apps/lttvideo/routes.py`, `server/templates/lttvideo.html`
- Tạo: `apps/lttvideo/chon_model.py`
- Test: `tests/test_729_lttvideo_chon_model.py`

**Giao diện**
```python
def chon_model(*, co_anh: bool, co_video: bool, kho_metadata: dict) -> str:
    """Trả `model_type`. Đọc `metadata.media_inputs` — KHÔNG có bảng tự chế."""
```

**Bước**
1. Test dùng fixture `metadata` (từ `T1`): không media ⇒ model có `capabilities.text_to_video`.
2. Test: có ảnh ⇒ model có `media_inputs.image.start`.
3. Test: có video ⇒ model có `media_inputs.video.control` hoặc `.continue`.
4. **Test chốt kiến trúc**: đọc AST của `chon_model.py`, khẳng định nó **không chứa** chuỗi `"t2v_2_2"` / `"i2v_2_2"` / `"vace"` nào — chọn model phải suy từ dữ liệu, không từ tên gán cứng.
5. Dùng `platform_core.image_input.validate_reference` cho ảnh tải lên — **không chép lại** phép kiểm.
6. GUI: ô kéo-thả cạnh prompt.
7. Commit.

⚠️ `T7` **phụ thuộc fixture của `T1`**. Làm phần mã + test trước với một fixture
**tay, nhỏ, có ghi rõ là tạm**; thay bằng ảnh chụp thật ngay khi `T1` xong.

---

### T8 — Thao tác thứ 7 `/hau_ky` + nút Upscale

**Tệp**
- Sửa: `tools/wangp/dich_vu_ccloud.py`, `apps/lttvideo/wangp_client.py`
- Test: `tests/test_725_...` (mở rộng), `tests/test_722_...`

**Giao diện**
```python
# C-CLOUD
@app.post("/hau_ky")   # {khoa, duong_media, spatial_upsampling, temporal_upsampling}
# -> session.submit_media_postprocessing(...)

# LTT
def hau_ky(self, *, duong_media: str, spatial_upsampling: str = "lanczos*2") -> str
```

**Bước**
1. Test: `/hau_ky` đòi khoá (cùng khuôn sáu đường kia).
2. Test: gọi `submit_media_postprocessing`, **không** gọi `submit_task`.
3. Test chốt: giá trị `spatial_upsampling` **không được** là một VAE upsampler — `API.md` cấm dùng VAE cho hậu kỳ.
4. GUI: nút **Nâng nét** trên mỗi video trong lịch sử.
5. Commit.

---

### T9 — Dọn theo hạn 3 ngày

**Tệp**: `apps/lttvideo/jobs.py` (job dọn), test `tests/test_730_...`

**Bước**
1. Test: job quá `het_han_luc` ⇒ khoá R2 bị xoá **và** hàng sổ đánh dấu đã dọn.
2. Test: job **chưa** hết hạn ⇒ **không** đụng tới.
3. Test: xoá R2 hỏng ⇒ **không** đánh dấu đã dọn (không nói dối sổ).
4. Commit.

---

### T10 — Độ dài tới 15 giây

**Tệp**: `apps/lttvideo/routes.py`, `ho_so.py`

**Bước**
1. `DO_DAI_S = (5, 10, 15)`.
2. Gửi `video_length = "15s"` — **chuỗi**, để `apply_video_length_duration()` tự quy khung. Không tự tính 241.
3. Test: gửi đi là **chuỗi giây**, không phải số khung (chốt bằng AST/giá trị).
4. GUI: hiện cảnh báo của WanGP khi chọn ≥10 giây — *artifact tích luỹ, nhận dạng nhân vật trôi*.
5. Commit.

---

## 3. Việc **cần pod** — gom vào MỘT lượt

### T0 — Nâng bộ ⛔ CHỜ DUYỆT (xoá tài nguyên cloud)

**Tệp**: `tools/wangp/cai_dat.sh` (viết lại), `tools/wangp/tao_pod.py`

**Bước**
1. `DELETE` pod cũ; `POST /pods` ảnh **CUDA 13 devel**, `gpuTypeIds` **cả danh sách**, `dataCenterIds=["US-KS-2"]`, `containerDiskInGb=20`, `minRAMPerGPU=64`, `ports="8888/http"`.
2. `cai_dat.sh` mới: miniconda ở `/data/conda` → `python=3.11.14` → `torch 2.10.0 --index-url .../cu130` → `requirements.txt` → SageAttention → **bánh xe GGUF `py311/cu130`**.
3. ⛔ **Giữ** `/data/venv` cũ tới khi bộ mới nghiệm thu xong.
4. Cổng kiểm **thứ thật**, y khuôn hiện tại: `command -v python3`, `-x .../python`, `import torch, mmgp` chạy được.
5. Xác nhận `[GGUF] kernels` **không còn** báo `unavailable`.

### T1 — Ảnh chụp `metadata`

```python
tu = {m: s.get_model_schema(m) for m in s.list_model_defs()}
```
Ghi ra `tests/fixtures/wangp_metadata/<sha>.json`. Đây là **bằng chứng**, không
phải bản chép tay ⇒ `T7` chốt vào nó.

### T2 — Tải `i2v_2_2` + `vace_14B`
Đo `du -sh` **thật**, ghi vào `DU_LIEU_DA_DO.md` §7.

### T3 — Tải bộ mở rộng prompt `Qwen3.8-27B` (GGUF Q4)
Bật ở `Configuration`; chọn chế độ **theo cả chữ và ảnh**.

### T4 — Đo lại ở cấu hình WanGP khuyến nghị
`--compile` + `--teacache 2.0` + chín biến của `entrypoint.sh`. Một lượt
`832x480/30 bước/profile 1`. Ghi giây/bước và VRAM đỉnh.

⛔ Đây **không** phải A/B thẩm định thượng nguồn (đã bỏ). Đây là **lấy con số
cho hồ sơ vận hành** ở cấu hình cuối cùng.

---

## 4. T11 — Nghiệm thu E2E

1. Người dùng thật (`akakenly.design@gmail.com`, **không** dùng admin) mở GUI.
2. Gõ prompt + **đính một ảnh** ⇒ hệ thống tự chọn `i2v_2_2`, người dùng không thấy tên model.
3. Xem tiến độ chạy; bấm **Huỷ** ở lượt thử riêng ⇒ credit **không** bị trừ.
4. Lượt thật chạy xong ⇒ video trong lịch sử, phát được, prompt hiển thị.
5. Bấm **Nâng nét** ⇒ ra bản độ phân giải cao hơn.
6. Kiểm trên **URL công khai**, không chỉ loopback (CLAUDE.md mục 5b).
7. Pod tự tắt khi sổ rỗng; `kiem-ke` thấy `pods` rỗng.

---

## 5. Tự soát plan

**Phủ quyết định** — 11 quyết định đã khoá, mỗi cái có việc mang nó:

| | Việc |
|---|---|
| A1 composer đầy đủ | T7 (media) + T1 (metadata) |
| A2 15 giây | T10 |
| A3 nút Upscale | T8 |
| A4 không mở seed/negative | *không việc* — giữ nguyên `KHOA_NGUOI_DUNG_DOI_DUOC` |
| A5 mở rộng prompt | T3 |
| B1 pod theo nhu cầu | T5 |
| B2 tuần tự | *không việc* — WanGP tự xếp hàng |
| B3 hết card ⇒ hoàn credit | T5 (`KHONG_CO_CARD`) |
| C1 giữ vai | *không việc* |
| C2 3 ngày | T6 (cột) + T9 (dọn) |
| C3 lưu prompt | T6 (cột) |

**Ba chỗ nhất quán đã kiểm**
- `chon_model()` nhận `kho_metadata` — cùng cấu trúc `T1` sinh ra ✓
- `DieuPhoi.bat_va_cho()` trả enum, `jobs.handle` phân nhánh trên nó ✓
- `hau_ky()` nhận `duong_media`, tức đường **phía C-CLOUD** — nên `T8` phải đẩy tệp từ R2 sang C-CLOUD trước, **hoặc** hậu kỳ ngay khi tệp còn ở đó ⚠️ **chưa quyết**

🔴 **Lỗ hổng tự soát tìm ra.** `T8` giả định tệp còn nằm trên C-CLOUD, nhưng
`jobs.handle` gọi `cleanup` **xoá tệp tạm ngay sau khi lên R2**. Nên nút Nâng nét
bấm sau đó sẽ **không có tệp để nâng**. Hai lối:

| | Lối | Đổi lại |
|---|---|---|
| a | Nâng nét **ngay trong cùng lượt sinh**, trước `cleanup` | rẻ, nhưng người dùng phải quyết **trước** khi xem kết quả |
| b | Đẩy ngược từ R2 lên C-CLOUD rồi mới hậu kỳ | đúng ý "nút bấm sau", tốn một vòng truyền |

*Đề xuất **(b)*** — `A3` nói rõ là nút trên video **đã có**. Cần thêm một đường
nhận tệp ở cầu nối. ⚠️ Đây là câu hỏi cần chủ dự án xác nhận trước khi code `T8`.

**Chưa có chỗ giữ chỗ nào** — mọi bước đều có tệp, chữ ký, và phép kiểm cụ thể.

---

## 5b. Trạng thái 07/09 — sau lượt làm

| Việc | GPU | Trạng thái |
|---|---|---|
| **T0** nâng pod lên bộ chính chủ (CUDA 13 · py3.11 · cu130) | ⚠️ | ✅ cài xong · ⛔ **nhân GGUF vẫn chưa nạp được** |
| **T5** điều phối viên pod (`dieu_phoi.py`) | ❌ | ✅ |
| **V3** nối `DieuPhoi` vào job — `B1` bật theo nhu cầu, `B3` hoàn credit | ❌ | ✅ |
| tự tắt khi rảnh (`nen_tat` + `tools/wangp/canh_pod.py`) | ❌ | ✅ |
| **G1** template về `apps/lttvideo/templates/` | ❌ | ✅ |
| **G2** ô đính media (macro `_o_chon_tep`) | ❌ | ✅ |
| **G3** `chon_model()` đọc `metadata` | ❌ | ✅ mã xong · ⏳ chờ ảnh chụp thật |
| **G4** nút Nâng nét → `upscalevideo` (GPU máy A) | ❌ | ✅ |
| **G5** cảnh báo trôi chất lượng ≥10 giây | ❌ | ✅ |
| **A2** độ dài 15 giây (truyền `"15s"`) | ❌ | ✅ |
| đường `/metadata` ở cầu nối | ❌ | ✅ |
| **T1** chụp `metadata` thật, thay fixture tạm | ⚠️ | ⏳ |
| **T2** tải `i2v_2_2` (+`vace_14B`) | ⚠️ | ⏳ |
| **T3** bộ mở rộng `Qwen3.8-27B` | ⚠️ | ⏳ **chặn bởi nhân GGUF** |
| **T4** đo lại ở cấu hình cuối | ⚠️ | ⏳ |
| **T11** nghiệm thu E2E | ✅ | ⏳ |

⇒ **Mọi việc không cần GPU đã xong.** Bốn việc còn lại gom vào **một lượt bật
pod**, đúng nguyên tắc §0.

### Hai thứ đổi so với plan gốc

🔴 **T8 (`/hau_ky` ở cầu nối) đã BỎ.** Chủ dự án chỉ ra LTT **đã có**
`apps/upscalevideo` chạy `realesrgan` trên GPU máy A. Việc còn lại là một dây
nối, không phải một thao tác mới — và điều đó xoá luôn lỗ hổng "tệp đã bị
`cleanup` xoá" ghi ở §5.

🔴 **T6 (lịch sử · tiến độ · huỷ) gần như BỎ.** Nền tảng đã có
`GET /jobs?app=lttvideo`, `/jobs/{id}/progress` (tự điều nhịp), `POST
/jobs/{id}/cancel`, `/artifacts/{i}`, và `Job.params` giữ prompt (`C3`). Xem
`THIET_KE_GUI.md` §1 — kèm **một lỗi mà trang lịch sử tự viết sẽ che mất**.

---

## 5c. Kế hoạch chốt: viết hết phần không cần GPU, rồi **MỘT** lượt pod cuối

Chủ dự án đề xuất 07/09, và nó đúng nguyên tắc §0: mỗi lần bật pod tốn ~9 phút
cộng rủi ro không thuê được card (đã trả giá hôm nay — `stop` rồi 5 lượt `start`
đều hỏng, phải tạo pod mới).

### Đợt A — viết hết, không bật pod

| # | Việc | Vì sao chưa cần GPU |
|---|---|---|
| A-1 | **`C2` dọn theo hạn 3 ngày** | thao tác trên R2 + sổ job, không đụng engine |
| A-2 | **`B2` chống bấm hai lần** (`dedupe_key`) | nền tảng đã có cột; chỉ cần truyền |
| A-3 | **`A5` mở rộng prompt** — bật `prompt_enhancer` của WanGP | mã đường đi viết được; **model** thì tải ở đợt B |
| A-4 | **Kiểm GUI bằng trình duyệt thật** (`CLAUDE.md` mục 5) | app chạy cục bộ, job không cần chạy xong |
| A-5 | Gate đầy đủ trên cây đứng yên | |

### Đợt B — **một** lượt bật pod, chạy hết rồi tắt

Thứ tự trong cùng một lượt, xếp theo *"hỏng sớm thì rẻ"*:

1. **Nghiệm thu bộ mới bằng một video chữ** — bộ `py3.11/cu130` trên SM 9.0
   **chưa từng sinh video nào**. Nếu hỏng thì hỏng ở đây, trước khi tải 30 GB.
2. **Tải `i2v_2_2`** (WanGP tự tải ở lượt dùng đầu) + **video từ ảnh**, đi qua
   đúng đường `nap_media` → `image_start`.
3. **Tải bộ mở rộng prompt** (`Qwen3.5-9B Int8` — **không** phải 3.8-27B, xem
   §5d) và thử một lượt có mở rộng.
4. **Nút Nâng nét** trên video vừa sinh → job `upscalevideo` chạy ở máy A.
5. **Đo** giây/bước ở cấu hình cuối, ghi vào `DU_LIEU_DA_DO.md`.
6. `canh_pod.py --tat` và `kiem-ke` phải thấy `pods` rỗng.

⛔ Không xen việc viết mã vào giữa đợt B: mỗi phút pod chạy là $3,19, và sửa mã
giữa chừng thì phép nghiệm thu không còn nói về một cây đứng yên.

### 5d. 🔴 `Qwen3.8-27B` bị chặn — dùng `Qwen3.5-9B Int8`

Đo 07/09 trên pod, hỏi thẳng `_GGUF_CUDA_LOAD_ERROR` của WanGP:

```
GGUF nap duoc: False
RuntimeError: CUDA error: CUBLAS_STATUS_INVALID_VALUE
              when calling cublasSgemm(...)
```

Gói `llamacpp_gguf_cuda 1.0.14+torch210cu130py311` **cài được**, gói `gguf`
**có**, `Q4_0` **được hỗ trợ** — hỏng ở **phép tự kiểm số học** của WanGP. Đây
là lỗi thật giữa bánh xe dựng sẵn và ngăn xếp này, không phải thiếu cấu hình.

⇒ `Qwen3.8` dùng trọng số GGUF nên **bị chặn**. `Qwen3.5-9B` chạy backend
**Int8/quanto**, không đụng đường GGUF — và `PROMPTS.md` gọi nó là *"strong
quality/performance balance"*. Lên 27B là một bước riêng, sau khi thượng nguồn
sửa.

---

## 6. Không nằm trong V1

Tab Ảnh / Giọng nói / Nhạc · LoRA · VACE mask · nối video >15s · bán ra ngoài
(giấy phép WanGP cấm).

---

## 7. Tài liệu bị thay

| Tệp | Trạng thái |
|---|---|
| `FINAL_IMPLEMENTATION_PLAN.md` | **thay** |
| `PLAN_SUA_LAI_THEO_WANGP.md` | **thay** |
| `PLAN_TOAN_DIEN_THEO_TAI_LIEU_WANGP.md` | **thay** (phần đọc tài liệu vẫn đúng) |
| `P01_KE_HOACH_THUC_THI.md` · `P01_TRIEN_KHAI_THEO_WANGP.md` · `DAY_CHUYEN_TRIEN_KHAI.md` | lịch sử P01, giữ để tra |

Còn hiệu lực: `DU_LIEU_DA_DO.md` · `QUYET_DINH_DA_KHOA_V1.md` ·
`SOAT_TINH_NANG_WANGP_VA_GUI.md` · `TAI_NGUYEN_VA_CACH_DUNG_LAI.md` ·
`DECISIONS.md` · `PROJECT_STATE.md`.
