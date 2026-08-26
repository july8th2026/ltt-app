# Sáu cái bẫy trong chính cổng chất lượng

**2026-08-25.** Không phải bẫy trong sản phẩm — bẫy trong **thứ dùng để chứng
minh sản phẩm đúng**. Tất cả đều cùng một hình dạng:

> Một phép kiểm **tồn tại**, nên không ai viết lại nó.
> Nó **không đo thứ nó có vẻ đang đo**, nên nó không cảnh gì cả.
> Và nó báo **PASS**, nên cái PASS đó đọc y hệt một cái PASS thật.

Sáu cái này lộ ra trong một ngày, vì trong ngày đó có **hai phiên làm việc song
song trên cùng một cây nguồn** — điều kiện làm mọi giả định "chỉ có một người"
gãy cùng lúc.

---

## Bẫy 1 — Bánh cóc đếm SỐ LƯỢNG thay vì chốt TẬP HỢP

`tools/check_so_test.py` chốt *"24 số tệp test bị trùng, không được nhiều hơn"*.

Ngày 25/08 hai phiên cùng tạo `test_303_*`. Bánh cóc báo **PASS** — vì trong
cùng lượt đó một va chạm **cũ** vừa được dọn. Tổng vẫn 24.

Nó không sai theo cách nó khai. Nó **đo nhầm đối tượng**: thứ cần chặn là *"một
số MỚI bị trùng"*, không phải *"tổng số tăng"*.

**Đã sửa.** `check_so_test.moc` nay là một tập hợp, dòng đầu `# tap-hop-so-bi-trung`.
Đọc được cả tệp mốc đời cũ và nói rõ đã chuyển đời — không nới lỏng im lặng.

> ⭐ **Luật rút ra, và nó áp cho cả ba bánh cóc thêm sau:** một bánh cóc đếm số
> lượng luôn có một cửa hoán đổi một-đổi-một đi lọt. Chốt tập hợp.

---

## Bẫy 2 — `--quick` báo PASS y hệt gate đầy đủ

`gate --quick` **đúng** khi bỏ `pytest` — đó là mục đích nó khai. Lỗi nằm ở dòng
kết quả: nó in `RESULT: PASS`, **không thêm một chữ nào**.

Cả hai phiên đều đọc dòng đó là "mọi thứ xanh". Và **mọi lỗi thật hôm đó đều nằm
ở đúng bước `pytest` mà chế độ này bỏ**:

| Lỗi | Vì sao `--quick` không thấy |
|---|---|
| Migration `pve_ve` dùng `ALTER COLUMN … TYPE` — vỡ trên SQLite | chỉ chạy trong pytest |
| Liên kết điều khoản VPS trỏ tới đường 404 | chỉ chạy trong pytest |
| Hai tệp `test_303_*` trùng số | bánh cóc bẫy 1 |

**Đã sửa.** `--quick` nay in:

```
RESULT: PASS  [--quick: KHONG chay bat bien da tien trinh, pytest]
        Chua phai bang chung day du - moi loi THAT ngay
        25/08 deu nam o buoc `pytest` ma che do nay bo qua.
```

---

## Bẫy 3 — Chuỗi đã vào `.po` rồi mà `msgstr` vẫn rỗng

`tools/check_i18n.py` canh chuỗi **chưa được bọc `_()`** — chuỗi không bao giờ
vào được tệp dịch. Không có gì canh bước **sau** đó.

Đo 25/08 trên `locale/en/LC_MESSAGES/messages.po`: 2.352 mục, trong đó **203 mục
`msgstr` rỗng** và **76 mục `#, fuzzy`**.

⛔ **Fuzzy đếm như rỗng.** `msgfmt` **bỏ qua** mọi mục `#, fuzzy` khi sinh `.mo`.
Một bản dịch fuzzy không bao giờ tới mắt người dùng — nó giống hệt một `msgstr`
rỗng khi chạy, chỉ khác là nó **trông như đã làm xong** khi đọc tệp `.po`.

**Đã sửa.** `tools/check_dich_thieu.py` + mốc 279 mục. Chốt tập hợp, nên ca hoán
đổi (dịch một mục cũ + thêm một mục mới, tổng không đổi) vẫn đỏ — có test chốt
đúng ca đó.

**Không dịch hết 279 mục ngay**, vì chúng nằm ở khu socialbot đóng băng, các app
cũ và trang admin — những chỗ bản tiếng Anh chưa ai xem — và dịch hết là một
buổi làm không ai kiểm lại được, mà vẫn không sửa nguyên nhân. Khu `/api/v1` và
khu VPS đã về **0% tiếng Việt** trong bản EN (`test_299`, `test_304`, `test_305`);
mốc này giữ cho phần còn lại không xấu đi trong lúc đó.

---

## Bẫy 4 — Test frontend đỏ vì hạn chờ viết cứng, và tôi chẩn đoán sai

Ba test vitest đỏ rải rác. Tôi suy ra *"quá hạn khi máy tải nặng"* từ con số
3.288ms so với hạn mặc định 5.000ms — một suy luận nghe hợp lý và **sai**.

Dòng lỗi thật đã bắt được:

```
2381ms … Unable to find role="button" and name "Tải bản mới"
```

Không phải 5.000ms. Là một `{timeout: 1900}` **viết cứng trong chính test đó**.

**Đã sửa.** Ba chỗ trong `CanvasShell.test.tsx` và một chỗ trong
`StudioShell.test.tsx` nâng lên `10_000`; cả ba `vite.config.ts` đặt
`testTimeout: 20_000, hookTimeout: 20_000`.

> ⭐ Bài học không phải "đặt hạn dài hơn" mà: **đừng suy ra nguyên nhân từ một
> con số khi dòng lỗi thật vẫn còn đọc được.**

---

## Bẫy 5 — Kết quả gate nói về một cây nguồn đã không còn tồn tại

Một lượt gate đầy đủ mất **2,9–4,4 giờ**. Trên kho này — hai phiên song song —
cây đổi vài phút một lần.

Ngày 25/08 có ba lượt đầy đủ. Lượt 4,4 giờ báo lỗi ở **một tệp đã đổi tên từ
nhiều giờ trước**. Kết quả ấy không sai lúc nó đo; nó **trả lời về quá khứ**. Đọc
nó như bằng chứng cho hiện tại là cách sinh ra ba vòng sửa những thứ không còn hỏng.

**Đã sửa.** Gate lấy dấu vân tay cây nguồn ở **cả hai đầu** và nói ra khi lệch:

```
CAY DA DOI TRONG LUC CHAY (a1b2… -> c3d4…).
Ket qua duoi day noi ve cay luc BAT DAU, khong phai cay hien tai.
```

---

## Bẫy 6 — Test bị bỏ qua là test không canh gì cả

`pytest -q` in **một chữ `s`** cho mỗi test bị bỏ qua. Một chữ `s` giữa ba nghìn
dấu chấm là vô hình, và gate chỉ giữ **4 dòng cuối** của đầu ra — nên ngay cả
`-rs` cũng không tới mắt ai.

Cụm VPS chạy sạch **503 passed, 2 skipped**. Hai cái `s` đó là
`test_293_vps_dung_lai_cong_vao.py`, và chúng không phải hai phép kiểm phụ:
chúng là **hai phép kiểm duy nhất** chốt rằng kịch bản dựng lại cổng vào còn
khớp bộ luật nftables đang chạy thật. Chúng bỏ qua vì `secrets/cong_vao/` không
bao giờ được commit — nghĩa là trên **mọi** máy làm việc chúng chưa từng chạy,
và bộ luật có thể trôi bao lâu cũng được.

**Đã sửa — nhưng không bằng cách ép chúng chạy.** Phần lớn chỗ bỏ qua ở đây là
đúng: không có PostgreSQL, không có ffmpeg, không có bucket R2 vứt đi, không
phải Windows. Ép chúng chạy trên máy không có điều kiện là đổi một phép kiểm im
lặng lấy một phép kiểm báo động giả.

`tools/check_bo_qua.py` **bắt mọi chỗ bỏ qua phải được KHAI BÁO**: in hết danh
sách 12 chỗ ở mỗi lượt gate (nên `test_293` được **gọi tên** mỗi lần), và báo đỏ
khi xuất hiện một chỗ **mới** chưa có trong mốc.

---

## Cái gì canh cái gì, sau ngày 25/08

| Bước gate | Chặn | Mốc |
|---|---|---|
| `trung so test` | thêm số tệp test bị trùng | `check_so_test.moc` (tập hợp) |
| `bo qua im lang` | thêm chỗ bỏ qua không khai báo | `check_bo_qua.moc` (12) |
| `chuoi chua dich` | thêm chuỗi chưa bọc `_()` | `check_i18n` |
| `dich thieu ban EN` | thêm `msgstr` rỗng / `fuzzy` | `check_dich_thieu.moc` (279) |

Cả bốn chạy **cả ở `--quick`** — chúng chỉ đọc tệp, tốn dưới 5 giây. Ba lỗi thật
lọt lên tàu ngày 25/08 đều lọt vì phép kiểm **có** mà chỉ sống trong `pytest`,
thứ `--quick` bỏ qua.

Bằng chứng rằng cả bốn **chặn thật**, không chỉ tồn tại:
`tests/test_306_banh_coc_bo_qua_va_dich.py` (10 phép kiểm, gồm ca hoán đổi của
bẫy 1) và hai phép kiểm mới trong `tests/test_145_gate_covers_everything.py`.

---

## Bẫy 7 — Một phép kiểm bảo mật đỏ **vì lý do khác** vẫn là một phép kiểm bảo mật không chạy

`tools/build_release.py` có đường chặn: phát hiện bí mật trong gói phát hành thì
`SystemExit`. Phép kiểm canh nó là
`test_44_release_build::test_secret_abort_path_reports_location_and_exits`.

Phép kiểm đó **đỏ nhiều ngày** — và không phải vì đường chặn hỏng:

```
AssertionError: assert '1 secret finding' in
  'frontend/agent-canvas bundle is stale or built with the wrong Node'
```

Chốt "bundle cũ" bắn **trước**, ném `SystemExit` của chính nó, và **nuốt mất**
`SystemExit` mà phép kiểm định bắt.

⛔ Một gốc (ba bundle lệch hash nguồn), **hai** triệu chứng — và triệu chứng thứ
hai đáng lo hơn hẳn: suốt thời gian đó **không ai kiểm đường chặn rò rỉ bí mật**,
trong khi bảng kết quả chỉ hiện *"2 failed"* trông như một lỗi build tầm thường.

⭐ **Bài học:** khi một phép kiểm đỏ, đọc **thông điệp**, không đọc **số**. Hai
test đỏ cùng một tệp có thể là hai vấn đề, và cái thứ hai có thể đang bị cái thứ
nhất che.

*(Đóng 2026-08-26 ở `a5274bf`: dựng lại ba bundle ⇒ 35 passed, phép kiểm bí mật
chạy lại.)*

---

## Bẫy 8 — Con số PASS nói về một tập hợp khác với tập hợp bạn tưởng

`tools/check_bien_dich.py` báo **"2.101 tệp .py đã kiểm | hỏng: 0"**. Nghe như
toàn bộ kho đã biên dịch được.

Ngày 26/08, sau khi gỡ một git worktree bỏ quên trong `.claude/worktrees/`, con
số tụt xuống **1.357**. Chênh **744 tệp** chính là một **bản sao cũ của cả kho**
— có `core/`, có `apps/socialbot`, có `test_152` đã xoá.

⇒ Suốt thời gian đó cổng biên dịch **thổi phồng độ phủ ~35 %**. Kết quả PASS
không sai, nhưng nó nói về một tập hợp **rộng hơn và cũ hơn** tập hợp người đọc
tưởng. Và `tmp/h26-canary-*/` (1,8 GB, 695 tệp `.py`) vẫn còn đó, vẫn được đếm.

⚠️ Cùng bản sao bóng đó suýt tạo một kết luận sai khác: lần quét
`LTT_SOCIALBOT_ROUTES` đầu tiên trả **13 kết quả từ worktree** trước khi tới kết
quả thật — đủ để báo *"còn residue socialbot"* trong khi nguồn đã sạch.

⭐ **Bài học:** mọi lệnh quét toàn kho phải mang `| grep -v '\.claude/worktrees/'`,
và khi một cổng in ra một con số lớn, hỏi *"con số đó đếm những gì"* trước khi
thấy yên tâm.

---

## Bẫy 9 — Cái chuông đã đúc mà chưa ai treo

Bốn ca trong một đợt audit, cùng một hình dạng:

| | Máy móc có sẵn? | Có ai gọi? |
|---|---|---|
| Giữ chỗ credit treo | `usage.reconcile` đếm được | ❌ chỉ test + CLI thủ công, **và vị ngữ bắt hụt 0/2** |
| Biên lợi nhuận âm | `costing.scan_for_alerts` đủ docstring, test, `__all__` | ❌ **không gì gọi** |
| Sao lưu | `backup.ps1` thiết kế đúng | ❌ **chưa từng chạy** |
| Link 404 trong nav | bài học đã viết trong chú thích `anhnoibo` | ❌ chưa thành phép kiểm |

⛔ **Một hàm cảnh báo không được cắm vào đâu trông Y HỆT một hàm cảnh báo đang
chạy.** Nó có docstring, có test, có trong `__all__` — mọi dấu hiệu bề ngoài của
một thứ đang hoạt động, trừ chính việc hoạt động.

Ca đắt nhất: cảnh báo *"đang bán dưới giá vốn"* nằm trong mã **suốt 22 ngày nền
tảng bán ảnh ở 45–57 % giá vốn**. Nó không im vì hỏng — im vì không ai cắm dây.

⭐ Vì vậy `test_307` và `test_308` chốt bằng `inspect.getsource` rằng các hàm quét
**ĐƯỢC GỌI**, không chỉ **tồn tại**. Và `tools/check_chuong_chua_treo.py` (trong
gate) luật hoá điều đó: mọi hàm quét/cảnh báo trong `platform_core/` phải có ít
nhất một người gọi ngoài `tests/`.

⚠️ Giới hạn nói thẳng: nó không bắt được ca sao lưu (PowerShell) và ca link-404
(một chú thích). Nó bắt hai ca nguy hiểm nhất, và bắt chắc chắn.

---

## Bẫy 10 — Công cụ chạy đúng khi bạn gọi tay, vỡ khi có thứ khác hứng đầu ra

Ngày 26/08, `gate.py` đỏ ở bước `bo test (song song)` sau **0,1 giây** — tức
**trước khi** bộ test kịp chạy lấy một phép kiểm nào:

```text
UnicodeEncodeError: 'charmap' codec can't encode characters in position 2-71
```

Nguyên nhân: `tools/test_nhanh.py` in một đường kẻ khung `─` làm nhãn bước. Gọi
tay thì console là UTF-8 nên nó luôn xanh. Nhưng gate **hứng** đầu ra, stdout
không còn là console, Python rơi về `cp1252`, và một dấu gạch trang trí làm hỏng
cả bước.

⭐ **Điều đáng học không phải chuyện mã hoá.** Là chuyện một công cụ có thể **xanh
100% khi người viết nó thử** và **luôn đỏ ở nơi nó thật sự chạy** — vì môi trường
khác nhau ở một chỗ không ai nghĩ tới. Nó vỡ ở đúng nơi ít người nhìn nhất.

⛔ Và nó **không nằm trong bộ test**. Không phép kiểm nào chạy `test_nhanh.py`
dưới stdout bị hứng, nên bộ test xanh trong khi công cụ chạy bộ test thì hỏng.
*Thứ chạy phép kiểm không tự nó được kiểm.*

**Đã bịt bằng hai lớp, và lớp thứ hai là lớp không được vắng:**

1. `_ep_utf8()` ép `stdout`/`stderr` về UTF-8 — nhưng `reconfigure` chỉ có trên
   `io.TextIOWrapper`, và dưới một trình hứng khác nó có thể **biến mất không báo
   gì**;
2. chuỗi in ra là **ASCII thuần**, nên không phụ thuộc lớp (1) nữa.

`test_309` chốt cả hai: một phép kiểm dựng lại đúng `cp1252` bị hứng, một phép
kiểm đọc mã và từ chối ký tự ngoài ASCII trong dòng `print` của `_chay`.

⇒ **Luật rút ra:** công cụ trong `tools/` phải được thử **dưới đúng cách gate gọi
nó** (đầu ra bị hứng), không chỉ dưới cách bạn gọi nó.
