# 11 — KẾ HOẠCH TỔNG HỢP + CỔNG QUYẾT ĐỊNH

**Ngày:** 2026-08-26 · **Đầu vào:** 00–10 · **Cây:** `3d804ee`+

---

## A. Hợp đồng MVP — bản chốt đề cử

> **Cho người sáng tạo nội dung tiếng Việt: biến một ý tưởng thành ảnh hoặc video
> dùng được, trả theo lượt bằng credit, không cần cài gì.**

**Lõi:** ảnh (`taoanh`+`thumbnail`+`anhnoibo`) · video (`taovideo`, `upscalevideo`) ·
prompt (`prompt_ai_ommi`) · chat/LLM (`chataistudio`+`ltt_llm`) · nạp credit ·
`/api/v1`
**Hỗ trợ:** đăng ký/đăng nhập · admin tối thiểu · `nexus`
**Beta:** `autosubvideo` · `taoclipngan`
**Hoãn:** `agent` (đường đưa tệp vào đã đứt) · `vps` (còn G7b/G9b)
**Nội bộ:** `qualitylab`

**9 bất biến** (INV-1…INV-9) ở `03_...md` §4. Hai cái mới — INV-5 (mọi giữ chỗ
đều kết sổ) và INV-9 (app sinh nav phải có trang) — **sinh từ lỗi thật đo được**,
không từ suy luận.

---

## B. Hiện tại → đích

**Hiện tại đã đúng và giữ nguyên** *(danh sách này dài hơn danh sách sửa)*:

```
platform_core → apps         0 cạnh, xác minh AST 732 tệp
19/19 job_type có handler     không mồ côi hai chiều
313 route, 0 route hở         40 route không Depends đều có chốt riêng
106 biến cấu hình, 0 chết
1 alembic head
gia_von.json + test_261       miễn trừ bán-dưới-giá-vốn có chữ ký + hạn
leases + gpu_lease            đập nhịp, thu hồi mồ côi, một-lần-trên-cụm
_khoa_so_du_user              check-then-write nguyên tử ở tầng CSDL
visible_on_surface()          một nguồn chân lý cho catalog/header
trung vị 4 tệp/commit         định vị thay đổi lành mạnh
```

**Đích = tiến hoá, không phải viết lại.** Ba việc cấu trúc, tất cả là *khai báo
một biên đã tồn tại*, không phải *dựng biên mới*:

| | Việc | Trạng thái |
|---|---|---|
| A-04 | Khai hợp đồng `apps → server` (4 module) + linter thi hành | ✅ `3d804ee` |
| A-02 | `server/api` thôi biết tên `apps.ltt_llm` | ⏳ |
| A-01 | Khai bề mặt công khai của `upscalevideo` | ⏳ |

---

## C. Gộp nguyên nhân gốc

⭐ **Bốn phát hiện, một gốc.** Đây là kết luận quan trọng nhất của Prompt 11:

| Phát hiện | Máy móc có sẵn? | Có ai gọi không? |
|---|---|---|
| **M-01** giữ chỗ treo | `usage.reconcile` đếm được | ❌ chỉ test + CLI thủ công, **và vị ngữ bắt hụt 0/2** |
| **M-02** biên lợi nhuận âm | `costing.scan_for_alerts` đủ mọi thứ | ❌ **không gì gọi** ngoài test của nó |
| **O-01** sao lưu | `backup.ps1` + `5-lich-backup.ps1` thiết kế đúng | ❌ **chưa từng chạy** |
| **U-02** link 404 | `anhnoibo` đã biết cách tránh và **đã viết ra lý do** | ❌ chưa thành phép kiểm |

> ## 🔴 P-01 — gốc chung
>
> **Khoảng cách giữa "đã biết" và "đã xếp lịch" không có ai canh.**
>
> Bốn lần, cùng một hình dạng: thứ cần thiết **đã được nghĩ ra, đã được viết,
> thậm chí đã được ghi lý do** — và không bao giờ được cắm điện. Một cảnh báo
> không được gọi trông **y hệt** một cảnh báo đang chạy, cho tới ngày cần nó.
>
> Sửa từng cái chỉ chữa hôm nay. **P-01 là thứ chữa ngày mai.**

**Đề xuất (P-01):** mục *"Còn tồn đọng"* trong `NHAT_KY.md` là ngõ cụt — nhật ký
đọc **theo thời gian**, kế hoạch đọc **theo việc**. Một bánh cóc đòi mỗi gạch đầu
dòng "Còn tồn đọng" có mã ứng với một dòng trong `KE_HOACH_TRIEN_KHAI.md`, cùng
họ `check_bo_qua`/`check_dich_thieu` — chặn tương lai, không dọn quá khứ.

---

## D. Ba lane

### Lane 12 — Đúng đắn *(phần lớn đã xong)*

| ID | Việc | Trạng thái |
|---|---|---|
| M-01 | Máy dò giữ chỗ treo + cắm vào bảo trì + cảnh báo | ✅ `a5274bf` |
| M-02 | Cắm cảnh báo biên lợi nhuận âm | ✅ `a5274bf` |
| B-01 | Dựng lại 3 bundle ⇒ gói phát hành + phép kiểm bí mật chạy lại | ✅ `a5274bf` |
| U-02 | Link 404 `/ltt-llm` + luật linter + bất biến test | ✅ `db6147e` |
| F-07 | Gỡ worktree bóng | ✅ (hệ quả: gate biên dịch thôi thổi phồng 35 %) |
| D-01 | Sửa mâu thuẫn `CLAUDE.md` về `LTT_PUBLIC_API_TOOLS` | ✅ |
| **O-01** | **Bật lịch sao lưu** | ⏳ **cần Administrator** |
| M-01b | Test tái hiện giết tiến trình giữa luồng | ⏳ |
| M-03 | Test đa tiến trình cho `credit.tru()` | ⏳ |
| M-04 | Vòng quét `AgentRun` treo *(khuôn: `reclaim_orphans`)* | ⏳ |

### Lane 13 — Cấu trúc

| ID | Việc | Trạng thái |
|---|---|---|
| A-04 | Hợp đồng `apps → server` + linter + `AGENTS.md` §8.2b | ✅ `3d804ee` |
| A-02 | Cắt `server/api` khỏi tên `apps.ltt_llm` (5 chỗ) | ⏳ |
| A-01 | Khai bề mặt công khai `upscalevideo` | ⏳ |
| G-01 | Mở lint sang `server/routes/`, bánh cóc baseline | ⏳ |
| 05.2 | Chẻ `server/routes/developer.py` theo use case | ⏳ (P2) |
| P-01 | Bánh cóc "Còn tồn đọng" ↔ kế hoạch | ⏳ |

### Lane 14 — Giao diện

| ID | Việc |
|---|---|
| U-01 | Xoá `.page--catalog` mồ côi *(kèm cache-bust)*; dọn style nội tuyến **sau khi** có bản thay thế |
| R-01 | Quyết ngõ cụt kéo-thả của Canvas — cần quyết định sản phẩm |
| 09.5 | E3 cho 4 trang Golden Journey còn lại, **sau deploy** |

---

## E. Cổng quyết định

⚠️ Chủ sản phẩm **đã bỏ cổng duyệt** ngày 26/08 và yêu cầu chạy thẳng chuỗi. Bảng
dưới ghi những gì **đã tự quyết** và **vì sao**, cùng ba thứ **không tự quyết được**.

### Đã tự quyết

| ID | Quyết | Căn cứ |
|---|---|---|
| D-04 | M-01 làm **phương án A** (máy dò + báo), **không** tự hoàn | Tự hoàn là quyết định tiền. A không đụng đường tiền, đảo được bằng `git revert` |
| D-03 | **Hoãn** tắt 43 route legacy trên production | Nó cần khởi động lại `LTTStudioWeb` — **chính là cửa sổ M-01**, mà bản vá chưa lên production |
| — | `ltt_llm` → `catalog_parent="chataistudio"` | Khuôn `anhnoibo` đã có; đổi `surface` sẽ đóng đường bán API |
| — | A-04 chọn **khai báo**, không dời chỗ | 72 lần sửa để đổi một cái tên; rủi ro thật đã được luật chặn |

### Không tự quyết được — vẫn cần chủ sản phẩm

| ID | Câu hỏi | Vì sao |
|---|---|---|
| ~~D-07~~ ✅ | Bù 2 credit đã kẹt? | **ĐÓNG** — chủ sản phẩm xác nhận chưa có khách thật ⇒ đó là tài khoản nội bộ, không cần bù |
| ~~D-02~~ ✅ | Đếm CSDL production? | **ĐÓNG bằng câu trả lời trực tiếp**: chưa có khách thật. Phép đo kỹ thuật không còn cần thiết |
| **D-06** | Khi nào deploy? | Không nằm trong bộ pack — Prompt 15 cấm tự deploy |
| **S-A/B/C** | Bề mặt MVP: 5 app `development` có ở lại catalog công khai? | Lời hứa với khách, và cần D-02 |
| **O-01** | Bật lịch sao lưu | Cần Administrator (UAC) |

---

## F. Trạng thái

```text
READY_FOR_CORRECTNESS_LANE: YES  (phần lớn đã thi hành)
READY_FOR_STRUCTURAL_LANE:  YES
READY_FOR_UI_LANE:          MỘT PHẦN  (R-01 chờ quyết định sản phẩm)
OPEN_OWNER_DECISIONS:       3   (D-06 deploy, S-A/B/C be mat MVP, O-01 sao luu — de cuoi)
```

⭐ **Câu quan trọng nhất của bản kế hoạch này không nằm ở ba lane.** Nó ở mục C:
bốn phát hiện độc lập hoá ra là **một** gốc. Sửa bốn cái mà không sửa gốc thì lần
sau vẫn thế, chỉ khác chỗ.
