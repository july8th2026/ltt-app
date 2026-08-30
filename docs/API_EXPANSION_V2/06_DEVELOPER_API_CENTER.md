# Phase 06 — Developer API Center

**Kết luận: phần lớn đã xong, và khuyến nghị lớn nhất của tôi ở Phase 01 là
SAI.** Mục này ghi lại cả hai.

---

## 1. 🔴 Khuyến nghị sai, và vì sao nó sai

Ở `02_OPTIONS_AND_RECOMMENDATION.md` §5 bản đầu tôi viết:

> *"Cả cụm `/developers/*` trả 303 về `/login`… nên làm một trang danh mục
> **công khai** sinh từ cùng builder."*

kèm tiền lệ `/vps` hồi 25/08 (*"trang bán phải phục vụ cả khách chưa đăng
nhập"*).

**Quan sát đúng. Kết luận sai.** Đó là một quyết định của chủ sản phẩm, đã chốt
**hai nhịp**, và tôi đã suy diễn ngược lại nó.

`docs/PUBLIC_API/QUY_CHUAN_TRANG_TAI_LIEU_API.md` §1:

> **TOÀN BỘ `/developers/*` đứng sau đăng nhập.** Hệ thống API của LTT phải
> đăng nhập mới kích hoạt được, nên cả khu đó là khu **của tài khoản**, không
> phải khu bán hàng.
>
> ⚠️ Chốt này đã đi qua hai nhịp […] nhịp đầu chủ sản phẩm bác riêng `tools`;
> nhịp sau chốt **cả khu**.

Và mã đã lường trước đúng sai lầm tôi mắc — `server/routes/developer/_chung.py`:

> *"`quickstart` không nằm trong chốt đó, và nó **KHÔNG** được mở theo suy diễn:
> mở một trang ra rồi đóng lại tệ hơn là mở chậm."*

Có cả bánh cóc hai chiều: `TRANG_CONG_KHAI = frozenset()`, và
`test_300::test_danh_sach_cong_khai_dung_bang_chot_cua_chu_san_pham` tồn tại
**chỉ để** một danh sách rỗng không làm hai phép kiểm khác im lặng biến mất.

### Bài học, vì nó lặp lại được

Tiền lệ `/vps` **có thật**, và tôi đã áp nó cho một trường hợp mà chủ sản phẩm
đã cân nhắc rồi quyết ngược. Sự khác nhau:

| | `/vps` | `/developers/*` |
|---|---|---|
| Trả lời câu gì | *"có đáng mua không"* | *"tôi đang dùng cái gì"* |
| Đọc dữ liệu tài khoản | không | có, và **đó là điểm của nó** |

⇒ **Một tiền lệ không phải một luật.** Trước khi áp nó, kiểm xem trường hợp này
đã có quyết định riêng chưa.

---

## 2. Ranh giới thi hành — đã đầy đủ

| Công khai | Sau đăng nhập |
|---|---|
| `/gia-api` — giá | **toàn bộ `/developers/*`** |
| `/huong-dan` — cách cắm vào công cụ | tools · quickstart · keys · usage |
| `/huong-dan/cong-cu` — tải công cụ | logs · webhooks · playground · docs · cli |
| `/status/api` · `/tai/…` · `/api/v1/openapi.json` | |

---

## 3. Việc thật của phase này — **đã làm 30/08**

Không phải *mở thêm trang*, mà là **làm đủ nội dung ở khu đã công khai**:

| Việc | Trước | Sau |
|---|---|---|
| Con số cửa sổ ngữ cảnh | **6 chỗ** nói **3 giá trị** mâu thuẫn (`131K`, `65000`, `64K`) | sinh từ `apps/ltt_llm/ngan_sach.py`, có test đối chiếu |
| Ba cửa + streaming | chỉ ở `/developers/quickstart` (sau đăng nhập); tài liệu còn ghi *"No streaming yet"* — sai từ 24/08 | `examples.BA_CUA` ra `/huong-dan` **công khai** |
| Hướng dẫn cắm | thiếu `model_catalog_json`, thiếu `CLAUDE_CODE_MAX_*` | có cả hai, kèm số đo A/B |
| **Gỡ ra** | **không có mục nào** | `HUONG_DAN_CAM_CLI.md` §2.6 — 5 nơi phải dọn |

⭐ Thứ đáng kể nhất: *"có ba cửa, hai trong đó stream"* là câu trả lời cho **"tôi
cắm được Codex/Claude Code vào đây không?"** — tức đúng loại câu *"có đáng mua
không"*, nên nó **thuộc khu công khai** theo chính chốt trên. Nó nằm nhầm chỗ,
và giờ đã đúng chỗ.

---

## 4. Nguồn chân lý — một, và có bánh cóc

| Thứ | Nguồn | Bánh cóc |
|---|---|---|
| routes | `server/api/inventory.py` | 27 route đóng băng, so hai chiều |
| tools · models · constraints | `AppManifest` → `build_catalog` | golden snapshot + `check_api_compat` |
| examples | `platform_core/public_api/examples.py` | `test_334` cấm số ngữ cảnh gõ tay |
| limits | `apps/ltt_llm/ngan_sach.py` | `test_334` đối chiếu 3 tầng |
| trang công khai | `TRANG_CONG_KHAI` | `test_300` chốt **cả hai chiều** |

---

## 5. Deviations

**`DEVIATION_WITH_EVIDENCE`** — khuyến nghị Phase 01 §5 đã **rút**. Ghi lại thay
vì xoá, vì lý do rút (một tiền lệ không phải một luật) có giá trị hơn khuyến
nghị ban đầu.

**Không có việc nào bị chặn.** Phần còn lại thuộc quyền chủ sản phẩm nếu họ muốn
đổi chốt.
