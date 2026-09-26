# GĐ1 — plan dựng lại đường ống: đảo bậc thang, dọn chồng chéo, đối soát

> Chủ dự án chốt 26/09/2026 (bốn quyết định, §2). Tệp này là **plan**, ⛔ chưa
> phải mã. Số đo lấy từ hai lượt chạy production 26/09 và các phép đo đã ghi.

---

## §0 🔴 ĐỊNH CHÍNH — ba điều tôi nói chưa đúng ở buổi phân tích

1. ⛔ Tôi nói *"nới biên vào khoảng lặng là nấc CHƯA CÓ"*. **Sai.** Nó **đã có**, ở
   `thoi_gian.py:219` (`TY_LE_MUON_KHOANG_LANG = 0.7`, mượn từ SoniTranslate). Điều
   tôi nói **đúng** là thứ khác và quan trọng hơn: nó chạy ở **`timing_align`**,
   tức **SAU** nấc gọi LLM ở `voice_synthesis`.
2. ⛔ Tôi nói *"nới biên là nấc rẻ nhất chưa dùng"*. Phải kèm một cảnh báo:
   `nan_thoi_luong.py` đầu tệp khai rằng cần gạt *"PHÂN PHỐI LẠI thời gian"* đã bị
   **xoá 25/09** với lý do *"⛔ không còn khoảng lặng THẬT giữa hai khe để mượn"*.
   ⚠️ Đó là **một câu nói, chưa phải một phép đo** — và nó nói ngược với việc
   `thoi_gian.py` vẫn đang mượn 70%. ⇒ §3 phải **đo** dung lượng khoảng lặng thật
   trước khi plan dựa vào nó.
3. ⛔ Tôi nói *"`edit_plan` chỉ là kế hoạch cắt"*. **Sai.** Nó sản xuất **một
   artifact** `{ban: BanBienTap, chi_muc: ChiMucCanh}` mà **hai** giai đoạn đọc, và
   một trong hai **ném lỗi** nếu thiếu. Chi tiết ở §4.

---

## §1 Hiện trạng — bảy sự thật, mỗi cái một `tệp:dòng`

| # | sự thật | bằng chứng |
|---|---|---|
| 1 | Cửa **tiêu tiền** (gọi LLM nắn) so với khe **KHÔNG có pause** | `giai_doan_giong.py:211` `khe = nan_cho_vua.khe_cua(m)` → `:317` `nen_viet_lai(giay, khe)` |
| 2 | Cửa **thực thi** (`timing_align`) lại dùng ngân sách **CÓ pause** | `thoi_gian.py:219` `noi_thoai + int(khoang_lang * 0.7)` |
| 3 | Chính kho tự buộc tội cách làm ở (1) | `nan_thoi_luong.Khe.ngan_sach_s`: *"⛔ Lấy `ket - bat` là **vứt hết khoảng lặng**, tức vứt **phần lớn ngân sách**"* |
| 4 | Xấu nhất một đoạn: **3 lượt TTS + 2 lượt LLM** | `giai_doan_giong.py:292-337`, `nan_cho_vua.VONG_TOI_DA = 2` |
| 5 | Bộ ước lượng **đã có**: `âm tiết ÷ 3,35` | `nan_thoi_luong.py:190`, `ngon_ngu.NHIP = {VI: 3.35, EN: 3.63}` |
| 6 | `3.35` đo trên **6 đoạn, MỘT giọng** (`Minh Đức`), σ = **0,16** | `ngon_ngu.py:62-68` |
| 7 | Trần tăng tốc `1.15` là số **MƯỢN** (Subdub), tăng tốc áp ở `timing_align` bằng `ffmpeg atempo` | `nan_cho_vua.py:128`, `am_master.py:373` |

### 🔴 Và một phát hiện mới, giải thích con số 205,7 s

`edit_plan` khai `tai_nguyen="llm_remote"` **tĩnh** trong `pipeline.CHUOI`. Nhưng
docstring của chính nó nói: *"Giai đoạn này **không trả tiền** khi preset là
`localize_preserve_picture`: không có cảnh nào được cắt, nên không có gì để hỏi
VLM."*

⇒ Với preset mặc định, `edit_plan` **giữ suất LLM duy nhất của cả máy** rồi ⛔
**không gọi model nào**. Đo được trên hai lượt cùng preset:

```
phim 1  edit_plan =   2,8 s
phim 2  edit_plan = 205,7 s      <- 203 giây chênh lệch là XẾP HÀNG, không phải tính
```

⭐ Đây là loại lỗi rẻ nhất để sửa và đắt nhất khi để lại: một giai đoạn **không
dùng** tài nguyên vẫn **chiếm** nó, trong khi `llm_remote` chỉ có **MỘT** suất
(`platform_core/llm/canonical.py:171`).

---

## §2 Bốn quyết định của chủ dự án (26/09) — và hệ quả kỹ thuật

| quyết định | hệ quả phải thi hành |
|---|---|
| **H2 không cần khoá.** Gốc 3 từ → Việt 4 từ đọc lệch là bình thường ⇒ ⛔ không khoá nới biên khi giữ giọng gốc | ⛔ Bỏ ý tưởng khoá chéo hai tính năng. Nới biên **luôn** được phép |
| **Vượt trần tăng tốc: chấp nhận thoải mái.** Thứ tự cứu: **(b) nới biên lần hai → (c) chấp nhận + ghi báo cáo** | `TRAN_TANG_TOC` đổi từ **cổng CHẶN** thành **ngưỡng CẢNH BÁO**; hệ số đã áp phải **ghi vào hồ sơ** từng đoạn |
| **`edit_plan` dọn sạch khỏi GĐ1** | Là một **phase**, ⛔ không phải một patch — xem §4 |
| **Giữ giọng gốc ⇒ phương án C**: hạ gain giọng gốc xuống rất thấp, nói rõ trên trang | Một hằng số trần gain cho lớp `giong` khi bật, + một câu trên giao diện |

---

## §3 Logic vận hành MỚI của GĐ1

```
transcribe  ->  ban ghi 74 doan, moc tung tu
   |
   v
[A] DICH theo lo (20 doan)  +  HO SO DICH ca video  +  SO GIAY cua tung khe
   |        (C1/C2/C3 cua B2_PLAN_NGU_CANH_DICH.md)
   v
[B] UOC LUONG giay doc — ⛔ khong chay TTS
   |    am tiet ÷ NHIP  +  thoi gian cho DAU CAU va KHOANG TRANG
   v
[C] CHIA NGAN SACH KHOANG LANG — MOT phep TOAN CUC cho ca chuoi
   |    moi doan: ngan_sach = khe + phan pause duoc chia (<= 70%)
   |    bat bien: moi doan sau khi noi bien ⛔ KHONG giao nhau
   v
[D] PHAN LOAI ba nhom, ⛔ khong goi model nao
   |    N1  uoc luong <= ngan sach                 -> PASS
   |    N2  vua duoc bang co gian nhe              -> ghi he_so, PASS
   |    N3  van tran                                -> vao lo can nan
   v
[E] NAN theo LO — MOT loi goi cho nhieu doan, kem tag truoc/sau
   |    chi nhom N3. 1-3 loi goi cho ca video (nay: hang chuc)
   v
[F] TTS MOT luot cho toan bo danh sach da chot
   |    GPU chay lien mach
   v
[G] DO THAT + CUU CUOI
        voice <= ngan sach            -> PASS
        voice >  ngan sach            -> tang speed (khong tran chan)
        van tran sau tang speed       -> (b) noi bien lan hai
        het pause de muon             -> (c) chap nhan + GHI vao bao cao
```

### Ba chỗ khác hẳn hiện tại

1. **[C] đứng TRƯỚC [E]** — nấc miễn phí trước nấc 16 giây. Đây là toàn bộ nội dung
   của phát hiện §1(1)+(2).
2. **[E] theo LÔ** thay vì một-đoạn-một-lời-gọi.
3. **[F] chỉ chạy MỘT lượt** vì text đã chốt ở [E]. Bỏ vòng `while` 3-TTS.

### ⚠️ Nấc [G] là nấc KHÔNG được bỏ

Bộ ước lượng có sai số ⇒ luôn còn đoạn lệch sau [F]. [G] là lưới cuối, và theo
quyết định của chủ dự án nó ⛔ **không chặn** — nó **sửa rồi ghi lại**.

---

## §4 Dọn dẹp — cái gì chết, ai thay, và chỗ nào ⛔ KHÔNG được xoá

### 4a. `edit_plan` — ⛔ KHÔNG xoá được bằng một lệnh xoá

Nó sản xuất **một** artifact `{ban: BanBienTap, chi_muc: ChiMucCanh}`, và có **hai**
người đọc:

| người đọc | đọc thế nào | nếu thiếu artifact |
|---|---|---|
| `content_process` (GĐ1) | `giai_doan_noi_dung._doc_ban_bien_tap()` | 🔴 **NÉM** `ThieuBanBienTap` — *"Chưa có bản biên tập nên chưa biết giữ phần nào"* |
| `image_finish` (GĐ2) | `giai_doan_hinh_anh.py:179`, `if khoa_ep:` | ✅ bỏ qua êm, `ban = chi_muc = None` |

Và `giai_doan_hinh_anh.py:33` khai một luật: *"⛔ **Không gọi model.** Quyết định
'cảnh nào kém' đã chốt ở `EDIT_PLAN`."*

⇒ **Ba việc, theo đúng thứ tự này:**

1. **`content_process` phải coi "không có bản biên tập" là trạng thái HỢP LỆ** =
   *giữ tất cả*, thay vì ném. Đây là điều kiện tiên quyết; ⛔ không làm bước này
   trước thì mọi bước sau làm chết lượt chạy.
2. **Bỏ `edit_plan` khỏi `pipeline.CHUOI`**, nối `content_process.sau = (TRANSCRIBE,)`.
   ⚠️ Chạm **sổ đăng ký dùng chung**: hàng `asv_stage`, chuỗi vân tay, `loi.phan_loai`,
   bảng `khoa phân loại job`, và các bài kiểm đếm giai đoạn. Đây là phần nặng nhất.
3. **Việc phán quyết cảnh kém chuyển sang GĐ2**, chạy **chỉ khi** khách bật preset
   cắt. ⇒ Luật *"`image_finish` không gọi model"* **phải được sửa tường minh** và
   ghi lại vì sao — ⛔ không sửa lặng lẽ.

⛔ **KHÔNG được xoá** `ban_bien_tap.py` / `canh.py` / `hieu_canh.py`: GĐ2 vẫn cần
`ChiMucCanh` để cắt. Chỉ **giai đoạn** biến mất, ⛔ không phải các module.

### 4b. Bảng chồng chéo — cái gì trùng với cái gì

| đang có | tình trạng | phán quyết trong plan này |
|---|---|---|
| `nan_cho_vua` (bậc thang 4 nấc) | ĐANG CHẠY | **Giữ** làm chủ bậc thang, nhưng đổi đầu vào: nhận **ngân sách** thay vì `khe_cua` |
| `nan_thoi_luong.gop_khe` | ĐANG CHẠY, ⭐ không trùng ai | **Giữ**. Nó đổi **ranh giới khe**, khác hẳn việc sửa một câu cho vừa khe |
| `nan_thoi_luong` 3 cần gạt cũ | ĐÃ XOÁ 25/09 vì trùng | ⛔ **Không thêm lại**. Plan này ⛔ không dựng module thứ hai cho bậc thang |
| `nan_cho_vua.khe_cua()` | là **nguồn của lỗi §1(1)** | **Giữ tên, đổi NGƯỜI GỌI**: `giai_doan_giong` phải hỏi ngân sách. ⚠️ ⛔ Đừng sửa `khe_cua` để nó tự cộng pause — nó đang trả lời đúng câu hỏi của nó (*"khe của đoạn này rộng bao nhiêu"*); sai là **câu được hỏi** |
| `VONG_TOI_DA = 2` | vòng 2 hiếm khi cần (chú thích của chính ta), VideoLingo đã **bỏ** vòng 2 | **Về 1**, đo lại số đoạn còn tràn |
| `TRAN_TANG_TOC = 1.15` (chặn) | chủ dự án chốt: ⛔ không chặn | Thành **ngưỡng cảnh báo** + ghi hệ số đã áp |
| `edit_plan` khai `llm_remote` tĩnh | chiếm suất mà ⛔ không dùng | Sửa **ngay ở phase 1** — rẻ nhất, lợi nhất |
| `_duong_doc_duoc` tên tệp cố định `nguon.bin` | **N-58 + N-59** | Phase 0 |

---

## §5 Cơ chế đối soát — mỗi lượt chạy tự kiểm chính nó

⭐ **Nguyên tắc: bộ ước lượng phải bị đối chiếu với sự thật ở MỌI lượt chạy thật, ⛔
không phải trong một lượt hiệu chuẩn riêng.** [F] đo giây thật của từng đoạn, [B] đã
đoán giây cho từng đoạn ⇒ mỗi lượt chạy cho **N cặp (đoán, thật)** miễn phí.

| mã | đối soát | đạt khi | vì sao cần |
|---|---|---|---|
| **Đ1** | `sai_so_uoc_luong` = phân vị 50/90/max của `|thật − đoán| / thật`, **theo từng giọng** | p90 ≤ 10% | Nếu trôi, mọi ngưỡng ở [D] sai theo. Bài học: *lệch nhỏ ở nhịp thành lệch lớn ở ngưỡng* |
| **Đ2** | `chieu_lech`: bao nhiêu % đoán **ngắn** hơn thật | 40–60% | Lệch **một chiều** là lỗi hệ thống (ví dụ: chưa tính thời gian dấu câu), khác hẳn nhiễu |
| **Đ3** | `pause_kha_dung_s`: tổng khoảng lặng mượn được / tổng thời lượng | — (đo để biết) | **Trả lời câu §0(2)**: lời khai *"không còn khoảng lặng thật"* là đo hay là nói |
| **Đ4** | `so_doan_nan_oan` = số đoạn `thật > khe_cua` **nhưng** `thật ≤ ngân sách` | = **0** sau phase 2 | Đây là **con số đo trực tiếp lỗi §1(1)**: mỗi đoạn như vậy là một lượt LLM tiêu oan |
| **Đ5** | `he_so_toc_da_ap`: phân bố, và số đoạn vượt 1,15 | — (ghi lại) | Chủ dự án cho vượt trần ⇒ phải **thấy** mình đang vượt bao nhiêu |
| **Đ6** | `so_doan_lech_cuoi` + tổng giây lệch | ghi vào báo cáo | Nấc (c): chấp nhận thì phải **nói ra**, ⛔ không im |
| **G1** | nhất quán đại từ (1 bộ cho một cặp vai) | = 1 | `B2_PLAN_NGU_CANH_DICH.md` §2 |
| **G2** | nhất quán tên riêng (1 tên gốc → 1 dạng Việt) | vi phạm = 0 | idem |

⭐ Đ1–Đ6 **⛔ không cần bản tham chiếu và ⛔ không cần ai chấm** — chúng là phép
**đếm** trên chính lượt chạy. Nên chúng là **cổng**, ⛔ không phải một nghiên cứu, và
chúng đi vòng qua vòng tròn LLM đang khoá bộ đo dịch.

⚠️ **Đ4 là cổng quyết định của cả plan.** Trước phase 2 nó **phải > 0** (chứng minh
lỗi tồn tại); sau phase 2 nó **phải = 0**. Một phép đo mà ⛔ không đỏ được trước khi
sửa thì ⛔ không chứng minh được gì.

---

## §6 Lộ trình — điều kiện VÀO và RA của từng phase

### Phase 0 · Bỏ chặn (N-58, N-59) — ⛔ không có nó thì ⛔ không đo được gì

* Sửa `_duong_doc_duoc`: `mkdir(parents=True, exist_ok=True)` + tên tệp **dẫn xuất
  từ khoá**.
* Bất biến ở biên: kho giả R2 (`local_path → None`) · thư mục **chưa tồn tại** · **hai
  khoá khác nhau vào cùng một thư mục phải ra hai đường khác nhau**.
* **RA:** một lượt chạy thật đi hết tới `render` và ra MP4.

### Phase 1 · Ba việc rẻ, ⛔ không chạm sổ đăng ký

1. `edit_plan` ⛔ không giữ `llm_remote` khi preset là giữ hình.
2. `VONG_TOI_DA: 2 → 1`.
3. Bộ ước lượng **cộng thời gian dấu câu + khoảng trắng** (mượn VideoLingo, Apache 2.0).
* **RA:** Đ1/Đ2/Đ3/Đ4 có số **lần đầu**, trên hai phim thật.

### Phase 2 · Đảo bậc thang — phần lõi

* `giai_doan_giong` hỏi **ngân sách** (đã chia pause toàn cục) thay vì `khe_cua`.
* Phép chia pause là **một hàm thuần**, có bất biến *"⛔ không đoạn nào giao nhau"*.
* **VÀO:** Đ4 > 0 đã đo được ở phase 1. **RA:** Đ4 = 0.

### Phase 3 · Nắn theo LÔ + hồ sơ dịch

* Gộp với C1/C2/C3 của `B2_PLAN_NGU_CANH_DICH.md` — **cùng một lời nhắc, cùng một
  lần tăng `PHIEN_BAN_LOI_NHAC_DICH`**. ⛔ Đừng tách hai lần đổi lời nhắc.
* Chống lẫn id: khoá JSON theo số thứ tự, kiểm `set(cần) − set(nhận)` **và** so số
  dòng, retry ≤ 3 lần **thêm khoảng trắng cuối prompt** để phá cache.
* **RA:** G1 = 1 · G2 = 0 · số lời gọi LLM mỗi video giảm ít nhất **5×**.

### Phase 4 · Một lượt TTS + nấc cứu cuối

* Bỏ vòng `while` 3-TTS. Trần tăng tốc thành **cảnh báo**. Nấc (b) rồi (c).
* **RA:** Đ5, Đ6 có số; ⛔ không đoạn nào bị bỏ im lặng.

### Phase 5 · Dọn `edit_plan` khỏi GĐ1 — phase NẶNG nhất, làm SAU CÙNG

Theo đúng ba bước ở §4a. Làm sau cùng vì nó chạm sổ đăng ký dùng chung, và vì mọi
phase trên **⛔ không phụ thuộc** nó.

⚠️ **Tách `edit_plan` khỏi việc đo:** phase 0–4 phải đo được **trước khi** chuỗi giai
đoạn đổi hình dạng. Đổi cả hai cùng lúc thì một con số đỏ ⛔ không nói được là do đảo
bậc thang hay do bỏ một giai đoạn.

---

## §7 Rủi ro, và cách chặn từng cái

| rủi ro | chặn bằng |
|---|---|
| Bộ ước lượng lệch **một chiều** ⇒ hàng loạt đoạn lọt/oan | **Đ2** (chiều lệch 40–60%) là cổng, ⛔ không phải báo cáo |
| `NHIP = 3.35` chỉ đo **1/49 giọng** | Đ1 **theo từng giọng**; giọng nào chưa đủ mẫu thì dùng **biên an toàn rộng hơn**, ⛔ không dùng số của giọng khác |
| Chia pause làm hai đoạn **giao nhau** — lỗi IM LẶNG | Bất biến ở biên trong hàm chia, ném khi giao |
| Nắn theo lô ⇒ model **lẫn/thiếu id** | 3 lớp kiểm của VideoLingo (số thứ tự · hiệu tập hợp · so số dòng) + retry nhiễu |
| Đổi lời nhắc mà **quên tăng phiên bản** ⇒ dùng lại bản dịch cũ, tưởng bản sửa vô dụng | Một bài kiểm chốt: lời nhắc đổi ⇒ `PHIEN_BAN_LOI_NHAC_DICH` phải đổi |
| Bỏ `edit_plan` làm `content_process` **ném** | §4a bước 1 **đi trước** bước 2, ⛔ không đảo |
| Vượt trần speed tự do ⇒ giọng méo mà ⛔ không ai biết | Đ5 ghi phân bố hệ số; Đ6 ghi đoạn còn lệch |

---

## §8 Hai câu vẫn cần chủ dự án

1. **Phán quyết cảnh kém (VLM) chuyển sang GĐ2 thì `image_finish` được phép gọi
   model.** Luật hiện tại của nó là *"⛔ không gọi model"*. Anh đồng ý sửa luật đó
   không? Nếu **không**, thì việc phán quyết cảnh **phải ở lại GĐ1** và "dọn sạch
   `edit_plan`" chỉ còn nghĩa *"⛔ không chạy khi preset là giữ hình"* — nhẹ hơn
   nhiều, và ⛔ không chạm sổ đăng ký.
2. **Trần gain của lớp "giọng nói gốc" khi khách bật** (phương án C): bao nhiêu phần
   trăm là "chỉ còn hơi thở nền"? Tôi đề nghị **≤ 20%**, ⛔ chưa đo — nó là một
   phán quyết **nghe**, không phải một con số suy ra được.
