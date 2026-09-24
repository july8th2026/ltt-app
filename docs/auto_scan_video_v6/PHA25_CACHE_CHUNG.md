# Pha 25 — Cache dùng chung xuyên lần chạy

**Trạng thái: XONG phần tái dùng — MỘT PHẦN ở vế "một tính, các bên kia chờ".**
Ngày 11/09/2026.

Đề bài: *tái dùng xuyên lần chạy cho ASR/OCR/scene/VLM/artifact đắt; một tính
nhiều chờ; an toàn chủ sở hữu/riêng tư; vô hiệu hoá + phiên bản.*

## 0. Đo trước — cái gì đắt, và nó có phụ thuộc lần chạy không

Báo cáo nghiệm thu thật (`nghiem_thu_hien_hanh.json`, model thật + giọng thật)
chạy **hai cánh trên CÙNG một nguồn** — đúng ca khách nộp lại một video:

| giai đoạn | cánh 1 | cánh 2 | phụ thuộc thiết lập của lần chạy? |
|---|---|---|---|
| `audio_prepare` (tách nguồn) | 24,8 s | 20,7 s | **không** — đọc thẳng tệp nguồn |
| `transcribe` (chép lời) | 123,3 s | 45,4 s | chỉ `ngon_ngu_nguon` + có phân vai hay không |
| `voice_synthesis` | 205,1 s | 182,3 s | có — lời + giọng của lần chạy |

⇒ Cánh 2 đã tính lại **66 s** cho hai giai đoạn có **cùng đầu vào** với cánh 1 —
cùng khách, cùng tệp nguồn, cùng ngôn ngữ (`test_448` nộp hai cánh bằng MỘT client).
⚠️ 123 s và 45 s khác nhau vì cánh 1 gánh cả lần nạp model; con số tiết kiệm
thật là thời gian của cánh sau, không phải của cánh đầu.

| tên trong đề bài | ở ASV hiện nay | pha này |
|---|---|---|
| ASR | `transcribe` | **chia sẻ** |
| artifact đắt | `audio_prepare` (demucs) | **chia sẻ** |
| scene | nằm trong `edit_plan`, phụ thuộc cắt đầu/cuối của lần chạy | không |
| VLM | `qc_ai`, chấm **bản kết xuất** của lần chạy | không — không có gì để trùng |
| OCR | chưa có engine (pha 15, hạng MÓNG) | — |

## 1. Vì sao không dùng vân tay giai đoạn làm khoá

🔴 `thi_hanh.van_tay` gom stage + hợp đồng + **toàn bộ** settings + đầu ra
thượng nguồn + engine — nhưng **không có danh tính nội dung nguồn**. Hai video
khác nhau, cùng settings, ra cùng vân tay ở `media_prepare`. Tra cứu xuyên lần
chạy theo vân tay đó sẽ giao bản chép lời của video A cho video B.

`test_478::test_noi_dung_KHAC_cung_settings_van_TINH_LAI` giữ đúng ca này. Đối
chứng: thay checksum trong khoá bằng một hằng số ⇒ **đỏ**.

## 2. Thiết kế — `apps/auto_scan_video/cache_chung.py`

**Khoá = địa chỉ nội dung**: sha256 của (phiên bản cache · chủ sở hữu · giai đoạn ·
hợp đồng · `phien_ban_engine` · checksum của **đúng tệp giai đoạn đọc** · **đúng**
những thiết lập giai đoạn đọc).

| giai đoạn | tệp nó đọc | thiết lập nó đọc |
|---|---|---|
| `audio_prepare` | `run.source_key` — checksum do `media_prepare` tính, nay ghi vào tóm tắt | không có |
| `transcribe` | bản 16 kHz của `media_prepare` (không phải đầu ra `audio_prepare` đứng trước nó trong đồ thị) | `ngon_ngu_nguon`, `che_do_giong` (qua `can_phan_vai`) + `MODEL_ASR` |

⭐ *"Đúng những thiết lập nó đọc"* được **chốt bằng AST**, không bằng lời hứa:
`test_478` đọc mọi thuộc tính lấy từ `cd.doc(run)` trong `giai_doan_chep_loi.py`
và đòi tập đó ⊆ tập trong khoá. Thêm một phép đọc thiết lập mà quên thêm vào khoá
⇒ **đỏ**. Thiếu một thiết lập thì cache dùng sai; thừa một thì cache mất âm thầm.

**Tái dùng bằng CHÉP, không bằng TRỎ.** Artifact được chép vào khoá staging của
lần chạy mới rồi đi qua `promote_va_ghi` như mọi kết quả engine — lineage, kiểm
hợp lệ và hạn giữ đi đúng đường cũ. Xoá lần chạy cho (`don_theo_run`) không làm
hỏng lần chạy nhận.

## 3. Bốn lần từ chối — mỗi lần một phép kiểm đỏ khi gỡ chốt

| từ chối khi | vì sao | đối chứng |
|---|---|---|
| **khách khác**, cùng nội dung | I19: checksum trùng là sự thật về nội dung, không phải giấy phép. Chủ sở hữu nằm **trong khoá và trong WHERE** | gỡ cả hai ⇒ đỏ |
| artifact của lần cho **mất / hỏng / hết hạn** | `kiem_toan_ven` từng cái; thiếu một cái là không dùng, không phải "dùng phần còn lại" | gỡ kiểm ⇒ đỏ |
| **lần thử lại** (`attempt > 1`) | khách bấm "thử lại" là khách không tin kết quả; trả lại đúng nó là làm ngơ câu hỏi. Lệch về phía **tính lại** | gỡ chốt ⇒ đỏ |
| bản chép lời **phân vai `khong_kha_dung`** | phân vai là năng lực phụ — thiếu sidecar thì bản chép lời vẫn ra. Dùng lại nó khi sidecar đã sống là biến sự cố tạm thời hôm qua thành kết quả vĩnh viễn hôm nay | gỡ chốt ⇒ đỏ |

🔴 **Lượt đối chứng đầu bắt được một phép kiểm SAI chứ không phải mã sai.** Test
phân vai xanh cả khi đã gỡ chốt, vì helper chỉ đặt `AUTO_MATCH` cho lần chạy thứ
hai ⇒ hai khoá lệch ⇒ tính lại vì *khoá khác*, không vì *chốt suy giảm*. Bản sửa
khẳng định **khoá trùng** trước khi đếm engine, và thêm vế dương (phân vai chạy
được ⇒ dùng lại). Tám lần tiêm, tám lần đỏ; tệp trả nguyên byte.

## 4. Vô hiệu hoá + phiên bản

* `phien_ban_engine(stage)` nằm trong khoá ⇒ nâng `PHIEN_BAN_TACH` hay
  `PHIEN_BAN_MA` là trượt mọi khoá cũ (`test_478` nâng `PHIEN_BAN_TACH` ⇒ tính lại).
* `PHIEN_BAN_CACHE_CHUNG` — nâng khi đổi cách dựng khoá.
* ⚠️ Giữ nguyên nợ của vân tay giai đoạn: `phien_ban_engine(TRANSCRIBE)` không mang
  `MODEL_ASR`, nên khoá chung mang **riêng** `MODEL_ASR`.
* **Không nâng** hằng số engine nào ⇒ báo cáo nghiệm thu hiện hành vẫn hiệu lực.

## 5. Chưa làm — nói thẳng

> ✅ Đã làm ở asv-final — `docs/auto_scan_video_final/L_CACHE_LEASE.md`. Đoạn dưới giữ làm lịch sử.

**Một tính, các bên kia chờ.** Hai lần chạy cùng video nộp **cùng lúc** vẫn tính
hai lần; lần sau chỉ hưởng cache khi lần trước đã xong. Làm đúng cần một lease
theo `khoa_chung` (`platform_core/leases.py` có sẵn) **và** một đường chờ không
giữ worker GPU trong lúc chờ. Đó là thay đổi ở tầng điều phối, không phải ở
`chay_giai_doan`.

**Tiền.** Lần dùng lại vẫn giữ credit như lần tính (`CHI_PHI_GIA = 0`, hai giai
đoạn này không có đơn vị việc). Có trừ ít hơn cho lần dùng lại hay không là quyết
định giá — thuộc pha 30.

**Đo thật.** Lượt nghiệm thu thật kế tiếp chạy hai cánh trên cùng nguồn, nên cánh
2 phải mang `tu_cache_chung: true` ở cả hai giai đoạn. Đó là phép đo đầu tiên
trên model thật; phép kiểm ở đây dùng engine giả lập.
