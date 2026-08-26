# 15 — NGHIỆM THU MVP / CỔNG PHÁT HÀNH

**Ngày:** 2026-08-26 · **Nhánh:** `public-api-v2`

> Đây là **nghiệm thu**, không phải một vòng tối ưu mới.

---

## 1. Đã làm gì trong đợt này

Bảy commit, ba loại việc.

| Commit | Loại | Nội dung |
|---|---|---|
| `a5274bf` | đúng đắn | **M-01** máy dò giữ chỗ treo + **M-02** cắm cảnh báo biên âm + **B-01** dựng lại 3 bundle |
| `db6147e` | đúng đắn | **U-02** link 404 `/ltt-llm` + luật linter + bất biến test |
| `ede373a` | tài liệu | Báo cáo 01, 02, 03 |
| `3d804ee` | cấu trúc | **A-04** hợp đồng `apps → server` + `AGENTS.md` §8.2b/8.2c + báo cáo 04, 05 |
| `05a20ac` | tài liệu | Báo cáo 06–11 |
| `f625199` | cấu trúc | Hai bánh cóc mới + `test_308` |
| *(cuối)* | tài liệu | Báo cáo này |

**Bốn lỗi đóng bằng mã có test:** M-01, M-02, B-01, U-02.
**Ba bánh cóc mới:** biên `apps → server` · kích thước route `server/` · **chuông chưa treo**.
**Gate: 19 → 21 bước.**

---

## 2. Phát hiện có giá trị lâu nhất

Bốn lỗi tưởng như độc lập, đo ra thì **một** gốc:

| | Máy móc có sẵn? | Có ai gọi? |
|---|---|---|
| Giữ chỗ credit treo | `usage.reconcile` đếm được | ❌ chỉ test + CLI thủ công, **và vị ngữ bắt hụt 0/2** |
| Biên lợi nhuận âm | `costing.scan_for_alerts` đủ docstring, test, `__all__` | ❌ **không gì gọi** |
| Sao lưu | `backup.ps1` thiết kế đúng, tách bí mật | ❌ **chưa từng chạy** |
| Link 404 trong nav | `anhnoibo` đã biết cách tránh, **đã viết ra lý do** | ❌ chưa thành phép kiểm |

> **P-01 — một hàm cảnh báo không được cắm vào đâu trông y hệt một hàm cảnh báo
> đang chạy.** Nó có docstring, có test, có trong `__all__`. Mọi dấu hiệu bề
> ngoài của một thứ đang hoạt động, trừ chính việc hoạt động.

Ca đắt nhất: cảnh báo *"nền tảng đang bán dưới giá vốn"* nằm trong mã **suốt thời
gian nền tảng bán ảnh ở 45–57 % giá vốn trong 22 ngày**. Nó không im vì hỏng — im
vì không ai cắm dây.

**Đã luật hoá:** `tools/check_chuong_chua_treo.py`, trong gate. Đã chứng minh nó
bắt đúng ca gốc *(gỡ dòng cắm `costing.scan_for_alerts` trên một cây giả ⇒ báo
ngay)*. Và nó tìm ra **ca thứ ba** chưa ai biết: `upload_sessions.reconcile`.

---

## 3. Ba lần tôi tự sửa lại chính mình

Ghi ra vì một bản audit chỉ đáng tin bằng mức nó dám ghi chỗ nó sai.

| | Tôi đã viết | Sự thật | Hệ quả nếu không sửa |
|---|---|---|---|
| **F-06** | 105 mục `.po` "nên dọn" (P2) | Trích lại sinh thêm **25 bản dịch SAI** (fuzzy 76→101) | Lane 12 sẽ **làm nợ dịch tăng** trong khi tưởng đang giảm |
| **O-03** | `deploy-self.ps1` thiếu `LTTNexus` | `LTTNexus` là **nhị phân riêng** ở `Program Files`, không chạy mã trong `app\` | Sửa một đường deploy **đang chạy đúng** — chính đường đã làm production ngừng 20 phút ngày 05/08 |
| **M-01** | "bốn đường chỉ dựa vào `try/finally`" | `streaming.py:257` **đã có** `except BaseException` từ 25/08 | Mô tả sai hiện trạng; cách gọi đúng mạnh hơn: *lưới có, nhưng chỉ căng trong tiến trình — và deploy là hành động giết tiến trình* |

Và một lỗi kỹ thuật bắt được bằng `git diff`: khi dựng lại trạng thái cũ để thử
nghiệm, tôi ghi `job_runner.py` không đặt `newline="\n"` ⇒ Windows đổi **toàn bộ
1.335 dòng** sang CRLF. `git diff --stat` báo 1335/1335. Đã sửa về LF. Không kiểm
diff thì một commit "không đổi gì" đã mang theo cả tệp.

---

## 4. Bằng chứng E3 — trên URL công khai

Đo qua Cloudflare, **không** qua loopback:

| | Desktop 1280 | Mobile 375 |
|---|---|---|
| Lỗi console | **0** | — |
| Tràn ngang | không (1265/1280) | không (375/375) |
| Phần tử vượt biên | — | **0** |
| Cache-bust | ✅ `ltt.css?v=828a9c98` | |

9 thẻ sản phẩm, **khớp chính xác** với phép đo nguồn.

⭐ Và một phân biệt chỉ E3 mới cho được: **bốn app đã gỡ KHÔNG hiện trong catalog**
dù mã vẫn nằm trên production. Residue Q108/Q109 nằm ở tầng **route**, không ở
mặt tiền khách hàng. Suy từ mã sẽ nói *"19 app còn đó"*; suy từ khách sẽ nói
*"9 sản phẩm"*. Cả hai đúng, và câu thứ hai mới là câu khách sống trong đó.

---

## 5. Bảng nghiệm thu

```text
MVP_SCOPE            : 8 app khach an danh thay; loi hua + non-goals o 03_...md
GOLDEN_JOURNEYS      : MOT PHAN — GJ-1 co E3; GJ-2..GJ-6 chi co E2
ARCHITECTURE_GATE    : PASS   platform_core -> apps = 0 canh; 1 chu trinh muc goi
SECURITY_TENANT_GATE : PASS (E1/E2)  313 route, 0 route ho; 65 tep test co lap chu
RUNTIME_GATE         : PASS   19/19 job_type co handler; claim/lease/thu hoi day du
MONEY_GATE           : PASS voi mot ngoai le co ten — xem duoi
DATA_RECOVERY_GATE   : FAIL   sao luu chua chay theo lich (O-01)
UI_UX_GATE           : PASS (trang vao)  con 4 trang GJ chua co E3
ACCESSIBILITY_GATE   : CHUA DO
OPERABILITY_GATE     : MOT PHAN  quan sat tot; sao luu la lo con lai
PERFORMANCE_COST_GATE: CHUA DO — khong bia nguong phut cuoi
FULL_REPO_GATE       : FAIL (1/23)  — 22/23 buoc PASS, buoc `pytest` do
                       36 failed / 4054 passed / 26 skipped  (2:00:25)

OPEN_P0 : 0
OPEN_P1 : 2   (O-01 sao luu — chu san pham de cuoi;  O-02 khoang trong bang chung)
```

### `MONEY_GATE` — ngoại lệ có tên

**INV-5** (*mọi giữ chỗ cuối cùng đều kết sổ*) hiện được **QUAN SÁT**, chưa được
**BẢO ĐẢM**.

Máy dò đã chạy dưới lease bảo trì và có cảnh báo gửi người trực. Nhưng nó **chỉ
báo, không tự hoàn** — tự hoàn là quyết định tiền (D-04, phương án B). Cửa sổ khi
tiến trình bị giết **vẫn mở**.

⚠️ Chủ sản phẩm xác nhận **chưa có khách thật**, nên hai khoản kẹt là tài khoản
nội bộ và không cần bù (D-07 đóng). Điều đó làm **giảm mức khẩn**, không làm giảm
mức nghiêm trọng: cửa sổ sẽ mở đúng lúc có khách đầu tiên, và mỗi lần deploy là
một lần mở nó.

---

## 5-bis. 🔴 Lượt gate đầy đủ — và nó tìm ra hai thứ

Chạy `python tools/gate.py` đầy đủ, **2 giờ 25 giây**:

```
22/23 buoc PASS  (gom ca `bat bien da tien trinh` 136.8s — buoc chi co o gate day du)
pytest           36 failed · 4054 passed · 26 skipped
```

### (a) Một test **làm bẩn cây nguồn**, và nó tự vô hiệu hoá lượt gate

Cuối lượt chạy, gate in:

```
CAY DA DOI TRONG LUC CHAY (a654577ceaeab401 -> 41743d3758f86da8).
Ket qua duoi day noi ve cay luc BAT DAU, khong phai cay hien tai.
```

Thủ phạm: **`tests/test_306_banh_coc_bo_qua_va_dich.py`**. Ba test trong đó ghi
đè `locale/en/LC_MESSAGES/messages.po` **thật** rồi khôi phục trong `finally`
bằng `write_text(goc, encoding="utf-8")`. Trên Windows, `Path.write_text` dịch
LF thành CRLF ⇒ bản "khôi phục" khác bản gốc **10.465 dòng** — nguyên tệp, chỉ
đổi kiểu xuống dòng.

⛔ Hai hậu quả, cả hai âm thầm:
1. `git status` của **bất kỳ ai chạy pytest** bỗng có một tệp `.po` sửa đổi
   không hiểu từ đâu ra;
2. gate lấy dấu vân tay ở cả hai đầu ⇒ **một lượt gate 2 giờ tự vô hiệu hoá
   chính nó**.

⭐ Và điều đáng nói nhất: **chính tệp đó đã làm ĐÚNG cho tệp `.moc`**
(`read_bytes`/`write_bytes`) ở test ngay bên dưới. Bài học: khi một tệp cần
byte-exact thì **mọi** tệp trong cùng hàm đều cần — không chỉ tệp mình nhớ tới.

**Đã sửa.** Sau khi sửa: `test_306` 10 passed, và `git status` sạch sau khi chạy.

⚠️ Đây cũng là lần thứ **hai** trong một buổi cùng một lớp lỗi CRLF cắn — lần
đầu là chính tôi khi dựng lại một trạng thái để thử nghiệm. Cả hai lần đều chỉ
lộ ra vì có người nhìn `git diff`.

### (b) Bốn lượt gate, và con đường 36 → 8 → 4 → 2

| Lượt | pytest | Cây có đổi? | Đã sửa gì sau đó |
|---|---|---|---|
| 1 | **36 failed** / 4054 passed | ⚠️ có | residue Agent + `test_69` + BEL trong `.ps1` + `test_37` |
| 2 | **8 failed** / 4082 passed | ⚠️ có | `test_272` mâu thuẫn · placeholder `ltt_sk_` · `test_298` · `test_126` |
| 3 | **4 failed** / 4085 passed | ✅ không | link chết `/settings` · plugin thiếu 2 chuyển hướng · `uq_vps_instance_ip` · cấu hình hồ sơ |
| 4 | **2 failed** / 4088 passed | ✅ không | hạn mức nhịp phụ thuộc tốc độ máy |

⭐ **Từ lượt 3 trở đi không còn cảnh báo `CÂY ĐÃ ĐỔI`** — sau khi `test_306` trả
lại cả **dấu thời gian** (`os.utime`), không chỉ nội dung. Trước đó hai lượt gate
(≈4 giờ) tự vô hiệu hoá chính chúng.

⛔ **Không lỗi nào trong 36 là do đợt tối ưu này gây ra.** Tất cả đã có sẵn, và
chúng chưa từng lộ ra vì lượt `pytest` đầy đủ chưa bao giờ chạy xong (H40.7).

### (c) Ba lỗ THẬT mà lượt chạy đầy đủ tìm ra

Đây là phần trả lời cho câu hỏi *"chạy `pytest` đầy đủ có đáng hai giờ không"*:

1. **`/settings` trả 404 cho mọi admin** kể từ Q108 — ba template vẫn trỏ vào
   nó. Cùng lớp với `/ltt-llm`, khác một điểm: `/ltt-llm` sinh **tự động** từ
   manifest nên luật linter bắt được; `/settings` **viết tay** trong template
   nên luật đó không với tới. Đã thêm phép kiểm đóng đúng khoảng trống ấy.
2. **Hai alias chuyển hướng thiếu trong plugin WordPress** — link cũ tới điều
   khoản VPS trả 404 trên website thật.
3. **`uq_vps_instance_ip` rơi khỏi lưới diễn tập khôi phục** — đúng cái bẫy mà
   chú thích ngay trên danh sách đó đã cảnh. Nó chặn một địa chỉ nội bộ bị cấp
   cho **hai** máy trong cùng gateway; mất nó thì mạng không báo lỗi, chỉ im
   lặng hỏng.

### (d) Và một phép kiểm **chưa bao giờ xanh** trên máy này

`test_193::test_one_abusive_key_does_not_degrade_a_well_behaved_one`.

Hạn mức tính theo **phút** (`RPM=120`); kịch bản chạy **3 giây**; máy đẩy được
~22 req/s ⇒ 65 request. 65 < 120 nên bộ hạn mức không có lý do gì để bắn.

⭐ Chú thích cũ ghi đúng ý định — *"real limits, so the thing being measured is
isolation"* — nhưng ngưỡng 120 làm phép đo phụ thuộc **máy chạy nhanh bao
nhiêu**, tức đo đúng cái nó nói là không đo.

Hạ xuống 15, và **đo trước khi chọn**: với 30 thì biên chỉ 3–11 request và đỏ
1/3 lần (đã đo đúng vậy); với 15 thì biên hai phía đều rộng. 5/5 lượt xanh.

⇒ *Một phép kiểm không bao giờ chạy và một phép kiểm không bao giờ xanh trông
giống hệt nhau từ bên ngoài.* Đây là bằng chứng cụ thể cho **O-02**.

### (e) residue Q108/Q109 trong bộ test — lớp thứ 16

Chẩn đoán từ mẫu đã soi (`test_97`, `test_98`, 9 lỗi):

```
AssertionError: (ValidationIssue(code='tool',
  message='Tool khong ton tai/khong co quyen: text.script', ...))
```

`text.script` là tool của **`kichban`**, đã gỡ ở Q109. Các test này dựng workflow
Agent dùng bảy tool và khẳng định chúng chạy được — bảy tool đó nay không còn đủ.

⇒ **Không phải lỗi do đợt tối ưu này gây ra.** Nhưng nó là một phát hiện mà
`01_...md` **đã bỏ sót**: tôi kiểm residue theo *import, route, CSDL, tài liệu,
docstring* — và kết luận `REMOVED_APPS_ACTIVE_REACHABILITY_SOURCE: 0`. Con số đó
đúng cho **khả năng với tới**, nhưng sai cho **hợp đồng hành vi**: bộ test vẫn
phụ thuộc vào sự **tồn tại** của các tool đã gỡ.

⭐ **Lớp thứ 16 cho danh sách quét của pack:** *test khẳng định một năng lực đã
bị gỡ vẫn tồn tại*. Nó không lộ ra bằng `grep` tên app — `text.script` không mang
chữ "kichban" ở đâu cả. Nó chỉ lộ khi **chạy**.

Đó cũng là lý do `H40` đóng mà thiếu lượt `pytest` đầy đủ là một khoảng trống
thật, không phải thủ tục: **đây chính là thứ lượt đó lẽ ra phải tìm ra.**

---

## 6. Còn nợ

| ID | Mức | Việc | Vì sao chưa làm |
|---|---|---|---|
| **O-01** | P1 | Bật lịch sao lưu + sao lưu bí mật + diễn tập khôi phục | Cần Administrator; **chủ sản phẩm để cuối** |
| **O-02** | P1 | E3 cho 4 trang Golden Journey còn lại | Phải lấy **sau deploy** — production đang chạy `ec6a00c` |
| **M-01B** | P2 | `hold_expires_at` + tự hoàn ⇒ INV-5 từ *quan sát* thành *bảo đảm* | Đụng schema + đường tiền; cần D-04 phương án B |
| **A-02** | P2 | `server/api` thôi biết tên `apps.ltt_llm` | Cần khái niệm *executor đồng bộ* trong hợp đồng app — xem 04 |
| **A-01** | P2 | Khai bề mặt công khai `upscalevideo` | |
| **05.2** | P2 | Chẻ `server/routes/developer.py` theo use case | Bánh cóc đã chặn việc nó phình thêm |
| **S-A/B/C** | — | Bề mặt MVP: 5 app `development` có ở lại catalog công khai? | **Quyết định sản phẩm** |
| **D-06** | — | Khi nào deploy | Prompt 15 cấm tự deploy |

---

## 7. Kết luận

```text
MVP_OPTIMIZED: KHONG — va day la cau tra loi dung
```

Không phải vì chất lượng kém. Ba lý do, mỗi lý do là một điều kiện của chính hợp
đồng nghiệm thu (`03_...md` §5):

1. **`DATA_RECOVERY_GATE` FAIL** — sao lưu chưa chạy theo lịch. Một MVP có khách
   trả tiền mà không có bản sao lưu tươi thì không phải một MVP đã sẵn sàng, bất
   kể mã tốt đến đâu.
2. **Golden Journeys chỉ mới một phần có E3.** Bốn hành trình còn lại mới ở E2, và
   hợp đồng đòi E3 trên URL công khai.
3. **INV-5 mới được quan sát, chưa được bảo đảm.**

⭐ Nhưng khoảng cách còn lại **nhỏ và đã có tên**, và điều đó khác hẳn tình trạng
đầu buổi. Đầu buổi có: ba trạng thái hệ thống chưa ai chốt · gói phát hành không
dựng được · một phép kiểm chặn rò rỉ bí mật không chạy · một link 404 trong header
mọi khách · hai khoản tiền kẹt không ai đếm · và bốn cái chuông chưa treo.

Nay còn: **một việc cần bấm UAC**, **một việc cần deploy rồi đo lại**, và **một
quyết định sản phẩm**.

**Đề xuất** *(không tự làm)*: sau khi O-01 xong và deploy, gắn thẻ
`MVP_OPTIMIZED_V2`.
