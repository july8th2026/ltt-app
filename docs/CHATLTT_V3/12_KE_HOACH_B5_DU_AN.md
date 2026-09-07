# B5 — Dự án (projects): gom hội thoại và tệp

> Đo ngày 06/09/2026. §0 lấy từ GitHub API + mã tải về (`scratchpad/b5/`); §1 từ
> chính mã kho này.

---

## §0 — Đối chiếu cộng đồng

### §0.1 Đo kho, kèm cột "mục ở cây gốc" (luật rút ra ở B4)

| Kho | Sao | Đẩy | Giấy phép | Mục cây gốc |
|---|---:|---|---|---:|
| `open-webui/open-webui` | 151.110 | 2026-09-05 | **NOASSERTION** | 54 |
| `danny-avila/LibreChat` | 42.864 | 2026-09-06 | MIT | 47 |

Cả hai có mã thật. Chỉ đọc hành vi ở Open WebUI (giấy phép).

### §0.2 `LibreChat/packages/data-schemas/src/schema/chatProject.ts` — 50 dòng

```ts
name (<=100) · description (<=1000) · user · tenantId
conversationCount        // dem, PHI CHUAN HOA
lastConversationAt       // moc, PHI CHUAN HOA
lastConversationId
index: (user,name,_id) · (user,createdAt desc) · (user,lastConversationAt desc)
```

🔴 **Thứ đáng ghi nhất là thứ KHÔNG có: không một trường chỉ dẫn / prompt nào.**
Project của LibreChat là một **thư mục**, không phải một ngữ cảnh. Đó là một dữ
kiện, không phải một thiếu sót — và nó thu hẹp phạm vi B5 đáng kể.

⭐ Thứ đáng mượn: **danh sách project sắp theo LẦN DÙNG GẦN NHẤT**, không theo
ngày tạo. Ba chỉ số của họ đều bắt đầu bằng `user`, và một cái sắp theo
`lastConversationAt desc` — họ đẻ ra cột ấy **chỉ để** phép sắp xếp đó đánh chỉ
số được.

⛔ Thứ **không** mượn: `conversationCount` phi chuẩn hoá. Đó là một nguồn chân
lý **thứ hai** cho thứ bảng nội dung đã biết, và `CLAUDE.md` của kho này viết
thẳng: *"một giá trị chép lại là một giá trị sẽ trôi"* — bảng 280 dòng chép tay
đã nói sai **năm lần**, và cả năm đều về phía nguy hiểm.

---

## §1 — Đo kho: B5 là LẮP, không phải XÂY

`platform_core/app_projects.py` **đã có đủ vòng đời**, và đã được ba app dùng
(`agent`, `autosubvideo`, `prompt_ai_ommi`):

```
get_owned · create · save (khoa lac quan qua `revision`) · archive
validate_container_payload: <=1 MiB · sau <=32 · chan khoa bi mat
```

Bảng `app_projects`: `id · user_id · app_slug · name(160) · schema_version ·
revision · status · payload(JSON) · created_at · updated_at`, với

```
ix_app_projects_owner_app_updated  (user_id, app_slug, updated_at)
```

⭐ **Chỉ số ấy CHÍNH LÀ thứ `lastConversationAt` của LibreChat sinh ra để phục
vụ.** Nếu ChatLTT chạm `updated_at` mỗi lần một hội thoại vào/ra dự án thì phép
sắp "gần nhất trước" đã có chỉ số, **không thêm cột nào, không có bộ đếm nào để
trôi**.

⚠️ Và một cái bẫy đã ghi ở `07_KE_HOACH_P07.md` §2: `git grep AppProject` trúng
`apps/chatltt/services/hoi_thoai.py` — nhưng đó là một **chú thích** mượn con số
30 ngày, không phải một chỗ dùng. ChatLTT **chưa** dùng `app_projects` lần nào.

---

## §2 — Bốn quyết định

### D1. Liên kết ở CỘT, cấu hình ở `payload` (giữ nguyên P07 D1)

`payload` là JSON do app sở hữu — hợp cho *cấu hình*. Nhưng *"dự án gom hội
thoại"* nghĩa là `chatltt_conversation` phải **thuộc về** một dự án, và một danh
sách id trong JSON không có ràng buộc, không có chỉ số, không xoá theo tầng.

⇒ **Cột `project_id` NULLABLE trên `chatltt_conversation`.** Nullable vì 220 hội
thoại đang sống không thuộc dự án nào và sẽ tiếp tục không thuộc dự án nào. Dự
án là **tuỳ chọn**, không phải một tầng bắt buộc mọc thêm trên đầu mọi người.

### D2. 🔴 Dự án KHÔNG mang trường chỉ dẫn riêng — B4 đã có `du_an`

Phản xạ là thêm `payload.chi_dan` rồi tiêm nó vào system prompt. **Không.**
`chatltt_ghi_nho.pham_vi` đã khai sẵn giá trị `du_an` từ B4 bước 1, và
`ghi_nho.ap_dung(du_an_id=…)` đã tiêm đúng tầng ấy — mã đã viết, đã có phép
kiểm, chỉ chưa có ai truyền `du_an_id` vào.

⛔ Hai cơ chế cùng tiêm chữ vào system prompt là hai cơ chế sẽ lệch nhau, và
   người dùng sẽ có **hai** chỗ để sửa cùng một điều — rồi sửa nhầm chỗ.

⇒ B5 chỉ phải **nối dây**: `luot.khoi_ghi_nho_neu_bat` truyền `du_an_id` của hội
  thoại. Giao diện quản lý ghi nhớ (B4 bước 6) đã bày sẵn nhóm *"Trong một dự
  án"*, hiện luôn rỗng vì chưa ai ghi vào được.

⭐ Và nó khớp phép đo §0.2: LibreChat cũng **không** cho project một trường chỉ
   dẫn. Ta không thiếu tính năng của họ; ta đặt nó ở một chỗ đã có.

### D3. `updated_at` chạm khi HỘI THOẠI vào/ra, không phải khi đổi tên

Nếu chỉ đổi tên mới chạm `updated_at` thì danh sách sắp theo "lần sửa tên gần
nhất" — một thứ không ai quan tâm. Mượn ý §0.2: mốc phải theo **lần dùng**.

### D4. Xoá một dự án KHÔNG xoá hội thoại trong nó

`project_id` về `NULL`, hội thoại ở lại. Một cái thư mục bị xoá không được mang
theo thứ nó đựng — người dùng nghĩ mình đang dọn nhãn, không phải đốt nội dung.

⛔ Đây cũng là lý do liên kết nằm ở **cột nullable** chứ không ở khoá ngoại có
   `ON DELETE CASCADE`.

---

## §3 — Sáu bước

| # | Việc | Cửa | Trạng thái |
|---|---|---|---|
| 1 | migration `f2c48b71e903`: `project_id` nullable + chỉ số | không đổi hành vi | ✅ |
| 2 | `services/du_an.py` — bọc `platform_core.app_projects` | không | ✅ `test_836` (19) |
| 3 | gán/gỡ, chạm `updated_at` (D3) | không | ✅ |
| 4 | nối `du_an_id` vào đường tiêm ghi nhớ (D2) | sau cờ `_MEMORY` | ✅ |
| 5 | 6 route `/api/du-an` + `cong_du_an` | cờ **mới** `_PROJECTS` | ✅ `test_837` (13) |
| 6 | `BangDuAn.tsx` + ô chọn dự án ở đầu trang | vẽ thật | ✅ `BangDuAn.test.tsx` (12) |

Dải test: **836–837**. **44 phép kiểm** (32 Python + 12 frontend).

### Kiểm bằng trình duyệt thật — lời hứa lõi đã chứng minh đầu-cuối

Tiến trình riêng cổng 8198, CSDL vứt đi. Tạo dự án → gán hội thoại → xoá dự án,
rồi **hỏi thẳng CSDL**:

```
hoi thoai: ('cv_ce9479...', 'Bon trang thai khoi tool', None)   <- CON NGUYEN
du an    : ('Quyet toan thue 2026', 'archived')
so tin   : 10                                                   <- khong mat gi
```

🔴 **Và trình duyệt bắt được một quyết định thiết kế SAI mà phép kiểm đơn vị đã
xanh sạch.** Bản đầu gắn cảnh báo *"N cuộc trò chuyện sẽ ở lại"* vào
`onMouseEnter`/`onFocus` của nút Xoá — 12 phép kiểm jsdom đều xanh. Thử trong
trình duyệt thật thì hai điều lộ ra: cử chỉ ấy khó kích hoạt, và quan trọng hơn,
**người dùng cảm ứng không bao giờ hover**. Câu cảnh báo quan trọng nhất của màn
hình nằm sau một cử chỉ mà một nửa số người không có.

⇒ Đổi sang **hai nhịp bấm**: nhịp một hỏi số và đổi nút thành *"Xoá thật"*, nhịp
  hai mới xoá. Ai cũng đi qua được, và nó nói **điều gì sẽ xảy ra** — khác hẳn
  một hộp thoại *"bạn có chắc không"*, thứ không nói được gì và người ta bấm Yes
  theo phản xạ.

⚠️ Bản đầu của phép kiểm cho quyết định ấy quét `BangDuAn.toString()` tìm chữ
   `onMouseEnter` — và nó **đỏ vì chính đoạn chú thích giải thích nó**. Đúng bẫy
   đã có tài liệu. Bản thay thế đo **hành vi**: hover/focus thì không có gì hiện
   ra và không request nào đi.

---

## §4 — Phép đo nghiệm thu (viết TRƯỚC)

1. **220 hội thoại cũ không đổi một byte**: migration add-only, `project_id`
   `NULL` cho mọi hàng có sẵn.
2. **Xoá dự án ⇒ hội thoại còn nguyên**, `project_id` về `NULL`.
   *(Đối chứng: bản dùng `CASCADE` phải ĐỎ.)*
3. **Không rò chéo người dùng**: gán hội thoại của mình vào dự án người khác bị
   chặn — kiểm **cả hai chiều** như `kho_tep`.
4. **`updated_at` chạm khi gán/gỡ**, không chỉ khi đổi tên.
5. **Ghi nhớ phạm vi `du_an` vào được ngữ cảnh** khi hội thoại thuộc dự án, và
   **không** vào khi nó thuộc dự án khác.
6. **Không có bộ đếm nào**: bánh cóc AST chốt rằng `services/du_an.py` không
   khai một cột/trường đếm hội thoại — §0.2 nói rõ vì sao.
