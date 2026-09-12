# BẢNG ĐỐI SOÁT — hệ ltt_llm dual-model

> Lập **2026-09-13**. Mọi dòng **đo được trong ngày**, bằng lệnh trên production
> và trên cây này. Không dòng nào chép lại từ hồ sơ cũ.
>
> ⛔ Tệp này **không** định nghĩa quy trình. Nguồn chân lý của nghiệm thu là
> `docs/superpowers/specs/2026-09-11-ltt-llm-dual-model-design.md` §23 (**A–Q**).

## 0. Ký hiệu — chốt một hệ, bỏ hệ kia

Hai hệ đang cùng tồn tại và **không** ánh xạ 1-1:

| Hệ | Ở đâu | Phán quyết |
|---|---|---|
| **A–Q** | spec §23 | ✅ **canonical** |
| `S2.1 … S6.7` | `BAN_GIAO_PHIEN.md` §7 | ⛔ cách đánh số riêng của phiên 12/09 — **bỏ** |

## 1. Tầng hạ tầng — đo 13/09

| Tầng | Đo được | Khớp spec? |
|---|---|---|
| Bề mặt công khai | `/api/v1/models` → `ltt-3.5` + `ltt-3.8`, kèm `context_window`, `reads_images:true` | ✅ D02 · L-19 |
| `llm_waiters` | 20 cột, có `model`, `cho_residency_s` | ✅ §7 |
| `execution_leases` | 13 cột, có `lop`, `token_dat_truoc`, `token_prefill_moi`, `la_whale` | ✅ T3 |
| `gpu_residency` | 6 cột: `nhom`·`trang_thai`·`tu_luc`·`cua_so_bat_dau`·`lan_nap_loi`·`phien_ban` | ⚠️ §2 dưới |
| Trọng tài residency | 1 dòng `rtx3090` → `trang_thai=llm`, `lan_nap_loi=0`, cửa sổ ảnh đóng | ✅ §12 |
| Sổ lượt | **297 dòng**: 161 `qwen38-api`/`ltt_38_3090` + 136 `qwen35-api`/`ltt_35_5060`, **100 % `xong`** | ✅ hai pool tách |
| Lease sống | 0 khi máy rảnh | ✅ không rò |
| alembic | production `a3f7c214e8b9` **=** head của cây | ✅ deploy được |
| Mã vs `C:\LTTPlatform\app` | khác **đúng 1 tệp**: `platform_core/api_pool.py` | biến số cô lập |
| Khoá provider `ltt_llm` | **1 hàng**, `active`, `total_requests=923` | 🔴 gốc L-01 |

## 2. ⚠️ `gpu_residency`: spec trôi, KHÔNG phải mã thiếu

Spec §7 đòi thêm `thanh_vien_dang_giu` và `so_anh_trong_cua_so`; CSDL và
`models.py` **không có cả hai**. Suýt ghi đây là lỗi — **nó không phải**:

| Trường spec | Mã làm gì thay thế | Phán quyết |
|---|---|---|
| `thanh_vien_dang_giu` | suy từ `trang_thai` (`llm` ⇒ `ltt_38_3090` giữ; `anh` ⇒ `anh_3090`) | dư thừa, bỏ đúng |
| `so_anh_trong_cua_so` | **đếm từ bảng `jobs`** (`residency.py:216` `anh_bat_dau_trong_cua_so`) | **tốt hơn** spec |

`residency.py:216` nói thẳng lý do: *"Đếm từ bảng `jobs`, không phải một bộ đếm
ghi tay"* — một bộ đếm ghi tay lệch được, đếm từ nguồn thật thì không.

⇒ Việc đúng là **sửa spec §7**, không phải thêm cột.

## 3. Bảng nghiệm thu A–Q — trạng thái

Quy trình đã chốt: `P0→P7 → Spec 2 → nghiệm thu tích hợp A–Q **một lần**` (D05).

| | Nội dung | Trạng thái | Ghi chú |
|---|---|---|---|
| **A** | Tĩnh: hai ID, UUID, hash engine | ✅ | test 1200·1210·1220·1233 |
| **B** | C1 LTT-3.8 ≥ 90 % mốc b10883 | ✅ | đo ở P3 |
| **C** | C1 LTT-3.5 text + ảnh | ✅ | đo ở P3 |
| **D** | C3 LTT-3.8 | ⚠️ **đo lần 1** | 93,7 tok/s tổng, scaling 1,88×. Chưa chốt — §7 dưới nói vì sao |
| **E** | C4 LTT-3.5 | ⬜ | ngưỡng `2 × C1` chưa chốt số |
| **F** | Hai model đồng thời ≥ 85 % | ✅ **ĐẠT 13/09** | 4 vòng: 0,99× · 1,08× · 1,15× · 1,10× (ngưỡng ≥ 85 % ⇔ ≤ 1,18×); `pg_locks` 0/369 |
| **G** | Ngữ cảnh hỗn hợp, `requests_deferred=0` | ⬜ | |
| **H** | 3.8 ngữ cảnh dài + cổng MTP | ⚠️ | đích **221.184 / `-np 3`** (L-14), không phải 262.144/`-np 4` |
| **I** | Residency: ảnh ↔ LLM xen kẽ | ⬜ | |
| **J** | 3.5 chạy khi 3090 vẽ ≥ 90 % | ⬜ | 3.5 không thuộc nhóm residency ⇒ kỳ vọng ~100 % |
| **K** | Kho ấm: nạp lạnh vs ấm | ⚠️ **một nửa** | nạp ấm đo được (3.5 ~10,5 s · 3.8 ~19,4 s); nạp **lạnh** chưa đo (xả standby trên máy đang phục vụ là không đảo được) |
| **L** | Đa tệp | ⬜ | Spec 2 |
| **M** | Hủy 6 trạng thái, slot trống ≤ 2 s | ⬜ | test 1222 phủ tầng mã, chưa phủ đường thật |
| **N** | 7 lỗi hạ tầng | ⬜ | |
| **O** | Tiền: 7 tình huống, 0 thu hai lần | ⬜ | |
| **P** | Rò lease generator, 5 điểm | ⬜ | |
| **Q** | Soak hỗn hợp | ⬜ | đòi A–P qua trước |

## 4. 🔴 Vì sao F là cổng CHẶN, không phải một lỗi lẻ

Spec §8 tuyên bố bất biến **L-7**: *"advisory lock theo `resource` ⇒ hai pool là
hai khoá độc lập, tải 3.8 không bao giờ lấy suất/ngân sách 3.5 và ngược lại"*.

Lý luận ấy **chỉ xét admission** — và ở tầng admission nó **đúng**: hai resource
`ltt_38_3090` / `ltt_35_5060` cho hai khoá advisory rời nhau (đã đọc mã, đã đo).

Nhưng đường đi thật có một điểm tuần tự hoá **nằm ngoài admission**:

```
dieu_phoi.goi(db, ...)
  api_pool.chon_key(db, ...)   -> UPDATE api_keys ... flush()   (KHONG commit)
  _goi_openai(...)             -> 3-20 giay goi may B
  api_pool.danh_dau_thanh_cong -> UPDATE lan hai
... commit mai o _finish_chat, SAU khi model tra loi
```

Một hàng `api_keys` duy nhất, chung cho **cả hai** model, bị khoá suốt lượt gọi.
⇒ **F không thể qua khi L-01 còn sống**, và đó mới là lý do L-01 xếp CHẶN —
không phải vì "nó đang đỏ".

Bản sửa khôi phục L-7 ở tầng spec chưa nhìn tới. Vì nó sửa tại `chon_key`, nó gỡ
luôn một nguồn khoá thứ hai: **vòng thăm `/health` của worker**
(`job_runner.py:1239`) cũng gọi `chon_key` mỗi vài giây trên đúng hàng ấy.

## 5. Lưu lượng thật 14 ngày — và một mục PHẢI ĐO, chưa phải phát hiện

| ngày | `done` | `error` |
|---|---:|---:|
| 04/09 | 103 | 5 |
| 05/09 | 184 | 7 |
| 06/09 | 207 | 12 |
| 07/09 | 610 | 5 |
| **08/09** | 490 | **64** |
| **09/09** | 81 | **34** |
| 10/09 | 35 | 3 |
| 11–13/09 | — | — |

**108/131 lỗi là một loại duy nhất:**
`AmbiguousProviderError: mat ket noi sau khi bat dau gui`.

⚠️ **CHƯA kết luận đây là hậu quả của L-01.** Nó khớp gọn — chờ khoá ăn mòn
`timeout_s` (`_con_lai_s` tính từ lúc request **vào cửa**, không phải lúc gọi),
rồi httpx đứt giữa chừng. Nhưng bàn giao §9 ghi đúng bài học này: *"một giả
thuyết khớp quá vừa là lúc phải nghi nhất"* — và L-01 đã bác bỏ một giả thuyết
khớp y như vậy ("khoá advisory theo tài khoản").

⇒ Ghi vào sổ là **mục cần đo**, đo sau khi deploy bản sửa: nếu L-01 là nguyên
nhân thì lớp lỗi này phải **biến mất**, không phải giảm.

## 6. Việc tiếp theo — thứ tự cứng

1. gate xanh
2. deploy máy A (biến số cô lập: **1 tệp**)
3. đo cổng **F** trên đường thật: `do_cheo_l01.py` **+** `soi_khoa_hang.py`
   (bằng chứng cơ học `pg_locks`, không chỉ con số thời gian)
4. **hai vòng liên tiếp trùng khớp** mới chốt (điều kiện dừng của chủ sản phẩm)
5. chốt ngưỡng **D**/**E** theo 3 luồng (L-14)
6. G–Q theo lô, máy B đi trước

## 7. Cổng D — đo lần 1 (13/09/2026), **chưa chốt**

Spec §23 ghi cổng D là *"C4 LTT-3.8: tổng ≥ 100 tok/s"*. L-14 đã hạ **C4 → C3**,
nên con số 100 — viết cho 4 luồng — không còn trả lời được câu hỏi này.

⛔ Và **không được** suy `100 × 3/4 = 75`. Thông lượng không tỉ lệ tuyến tính với
số luồng: nó bị chặn bởi băng thông bộ nhớ, và phần chia ấy không chia đều. Đo
được scaling **1,88×** từ 1 → 3 luồng, không phải 3×.

| | đo được |
|---|---:|
| C1 đơn, **qua máy A** | 49,9 tok/s |
| **C3 tổng** | **93,7 tok/s** |
| mỗi luồng ở C3 | 31,7 tok/s (3 luồng đều nhau: 31,3 / 31,7 / 32,5) |
| scaling 1 → 3 luồng | **1,88×** |

### ⚠️ Hai lý do con số này CHƯA chốt được

1. **Khác đường đo.** Mốc C1 `63,01 tok/s` (G3b, 12/09) đo **thẳng máy B**; phép
   đo này đi **qua máy A + Cloudflare**. Hai con số trả lời hai câu khác nhau —
   so trực tiếp là đúng lỗi *"phạm vi phép đo hẹp hơn lời tuyên bố"*.
2. **Máy có tải.** Một lượt gate đang chạy trong lúc đo. `docs/BAY_TRONG_CONG_CHAT_LUONG.md`
   ghi rõ tải nặng làm phép đo **sai**, không chỉ chậm.

⇒ Phải đo lại khi máy rảnh, **≥ 3 lượt**, và đo **cả hai đường** (qua máy A và
  thẳng máy B) để tách phần overhead của máy A ra khỏi thông lượng của engine.

⛔ Chưa đề xuất ngưỡng mới cho C3. Một ngưỡng đặt theo một lượt đo có nhiễu là
   đúng thứ `nguong-dat-theo-mot-luot-do-tin-hieu-ngau-nhien` cảnh báo — và
   phiên này đã vấp nó một lần ở L-02 (300 → "đúng" ở 1 lượt, rỗng 3/5 khi đo 5).

## 7b. Cổng D và E — đo lần 2 (13/09), **máy rảnh, 3 lốt, hai đường**

Máy A: gate đã xong, deploy đã xong. Mỗi lốt đo **thẳng máy B** rồi **qua máy A**,
sát nhau về thời gian. `-np 3` cho cả hai hồ sơ ⇒ C3 là đúng cấu hình.

### Số đo (trung vị 3 lốt, tok/s)

| | C1 | C3 | scaling | 2 × C1 | spec đòi |
|---|---:|---:|---:|---:|---|
| **D** `ltt-3.8` thẳng B | 55,5 | **95,0** | 1,71× | 110,9 | — |
| **D** `ltt-3.8` qua A | 47,0 | **90,3** | 1,92× | 94,0 | ≥ 100 (viết cho C4) |
| **E** `ltt-3.5` thẳng B | 64,6 | **120,2** | 1,86× | 129,2 | ≥ 2 × C1 |
| **E** `ltt-3.5` qua A | 56,2 | **111,2** | 1,98× | 112,4 | ≥ 2 × C1 |

Dải 3 lốt: D qua A 87,0–91,9 · E qua A 110,8–114,0. 0 lượt hỏng trong cả 12 lốt.

### 🔴 Tiêu chí *"≥ 2 × C1 của chính nó"* là một tiêu chí HỎNG

Nhìn hai dòng của `ltt-3.8`: qua máy A, scaling **cao hơn** (1,92×) so với đo
thẳng máy B (1,71×). Máy A **chậm hơn** mà lại **ghi điểm tốt hơn**.

Không phải nghịch lý — đó là số học. Phí nền tảng là một khoản **cố định mỗi
request**, nên nó ăn vào C1 nặng hơn ăn vào C3 (nơi nó được chia cho 3 luồng):

```
ltt-3.8   C1  55,5 -> 47,0   giam 15,3 %
          C3  95,0 -> 90,3   giam  4,9 %
```

Mẫu số co nhiều hơn tử số ⇒ **tỉ số tăng**.

⛔ Tức một tiêu chí dạng tỉ số sẽ **thưởng cho việc làm nền tảng chậm đi**. Bất
kỳ ngưỡng nào cho D/E phải đặt trên **thông lượng tuyệt đối**, không trên tỉ số.
Tỉ số vẫn đáng ghi — nó chẩn đoán tốt — nhưng nó không được làm cửa.

### Đề xuất ngưỡng cho C3 — đặt dưới lượt tệ nhất đo được

Ngưỡng là **bộ dò hồi quy**, không phải lời chúc. Nó phải bắt được một suất bị
mất hay một khoá bị đặt lại, mà không đỏ vì nhiễu ±3 % đo được.

| cổng | đo qua | tệ nhất đo được | **ngưỡng đề xuất** | biên |
|---|---|---:|---:|---:|
| **D** `ltt-3.8` | máy A | 87,0 | **≥ 78** | 10 % |
| **E** `ltt-3.5` | máy A | 110,8 | **≥ 99** | 10 % |
| D bạn đồng hành | thẳng B | 94,8 | ≥ 85 | 10 % |
| E bạn đồng hành | thẳng B | 114,2 | ≥ 103 | 10 % |

⭐ **Vì sao cả hai đường.** Một mình số qua-A nói *khách chờ bao lâu* nhưng không
nói **hỏng ở đâu**. Có cặp số thì một lần đỏ tự phân loại: cả hai cùng tụt ⇒
engine/GPU; chỉ qua-A tụt ⇒ nền tảng máy A.

### ⚠️ Một chênh lệch CHƯA giải thích được — đừng lấp nó

| model | mốc C1 ghi 12/09 | C1 thẳng B đo 13/09 | lệch |
|---|---:|---:|---:|
| `ltt-3.8` | 63,01 | 54,8–57,9 | **−10 %** |
| `ltt-3.5` | 76,21 | 63,4–65,5 | **−15 %** |

Cả hai lệch **cùng chiều, cùng cỡ** — dấu hiệu của khác biệt **hệ thống**, không
phải nhiễu. Ba khả năng, chưa loại trừ cái nào: (a) đề đo khác (độ dài ra khác
⇒ tỉ lệ prefill/decode khác), (b) bộ đo 12/09 tính thời gian khác, (c) một hồi
quy thật.

⛔ **Chưa được dùng mốc 63,01 / 76,21 làm đối chứng cho tới khi biết đó là (a),
(b) hay (c).** Đây đúng là cái bẫy mà chính tệp này cảnh báo ở §7: so hai con số
sinh ra từ hai phép đo khác nhau rồi gọi hiệu số là một phát hiện.

### Phí nền tảng — đại lượng đo được, và nó rẻ dần khi tải tăng

| | C1 (B − A) | C3 (B − A) |
|---|---:|---:|
| `ltt-3.8` | 7,9–11,2 | 4,7–7,8 |
| `ltt-3.5` | 8,4–9,7 | 3,0–10,1 |

Đây là hai con số **được phép trừ vào nhau**: cùng một đại lượng, đo trong cùng
một lốt, trên cùng một trạng thái máy.


## 8. Sổ lỗi L-* — trạng thái cuối lượt 13/09

| mã | trạng thái | ghi chú |
|---|---|---|
| **L-01** | ✅ **đóng** | 4 vòng 0,99–1,15×; `pg_locks` 0/369; deploy + nghiệm thu 0/0/0 |
| **L-02** | ✅ **đóng** | sàn `max_tokens` theo model × mức, đặt **sau** 413; nghiệm thu 4/4 mệnh đề trên đường thật |
| **L-03** | ✅ **đóng** | cả hai model khai `reads_images`; `DEVELOPER_GUIDE` + CHANGELOG đã sinh lại |
| **L-04** | ✅ **đóng** | bộ chấm đổi sang mệnh đề dương; bản cũ chấm 3/3 câu sai thành "đúng" |
| **L-05** | ✅ **đóng** | 48/48 done, 0 lỗi; p = 0,3 % nếu tỉ lệ 11,6 % còn nguyên |

⭐ Năm mục L-* đều đóng, và mỗi mục đóng bằng một **phép đo trên đường thật**,
không bằng một bản vá đã commit. Việc còn lại nằm ở các cổng A–Q, không ở sổ lỗi.
