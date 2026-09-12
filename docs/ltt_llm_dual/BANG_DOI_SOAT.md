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
| **D** | C3 LTT-3.8 | ⚠️ | ngưỡng `≥100 tok/s` viết cho **4 luồng**; L-14 hạ xuống **3** ⇒ **phải tính lại**, chưa chốt |
| **E** | C4 LTT-3.5 | ⬜ | ngưỡng `2 × C1` chưa chốt số |
| **F** | Hai model đồng thời ≥ 85 % | 🔴 **CHẶN** | L-01: qua máy A đo 2,1–8,1×; thẳng máy B 0,85–1,05× |
| **G** | Ngữ cảnh hỗn hợp, `requests_deferred=0` | ⬜ | |
| **H** | 3.8 ngữ cảnh dài + cổng MTP | ⚠️ | đích **221.184 / `-np 3`** (L-14), không phải 262.144/`-np 4` |
| **I** | Residency: ảnh ↔ LLM xen kẽ | ⬜ | |
| **J** | 3.5 chạy khi 3090 vẽ ≥ 90 % | ⬜ | 3.5 không thuộc nhóm residency ⇒ kỳ vọng ~100 % |
| **K** | Kho ấm: nạp lạnh vs ấm | ⬜ | |
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
