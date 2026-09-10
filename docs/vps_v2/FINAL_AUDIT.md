# VPS V2 — KIỂM TOÁN CUỐI

> Prompt 11. Tài liệu này nói **cái gì đã sửa, bằng chứng ở đâu, và cái gì chưa**.
> Điểm số ở `RELEASE_SCORECARD.md`; vật cản ở `KNOWN_BLOCKERS.md`.

- Chương trình: `LTT_VPS_V2_ONE_SESSION_PROMPT_PACK` (12 pha, 00 → 11)
- Cây: `.claude/worktrees/ltt-vps-v2-deployment-plan-2cfc36`
- Nhánh: `claude/ltt-vps-v2-deployment-plan-2cfc36`
- Baseline: `05464239` · `master` lúc bắt đầu: `9e73bf1f` (đúng SHA pack quan sát)

---

## 1. Bảy phát hiện — trạng thái cuối

| ID | Mức | Phát hiện | Đã sửa ở | Bằng chứng |
|---|---|---|---|---|
| **V-01** | P0 | `khoi_dong_lai()` chỉ tắt, không bật lại | Pha 03 | `test_553::test_khoi_dong_lai_ket_thuc_o_RUNNING` + `::test_khoi_dong_lai_co_di_qua_pha_TAT` |
| **V-02** | P0 | Ghi trạng thái ổn định ngay sau khi Proxmox **nhận** lệnh | Pha 02–03 | `test_551::test_tac_vu_OK_ma_may_khong_toi_noi_van_la_that_bai`; `test_553::test_khong_gui_lenh_BAT_khi_may_van_con_dang_chay` |
| **V-03** | P0 | Chụp ảnh rồi dọn ngay; `sao_luu_luc` ghi cho ảnh chưa xác minh | Pha 04 | `test_554::test_tac_vu_bao_OK_ma_anh_khong_co_thi_van_la_that_bai`; `::test_bao_tri_KHONG_ghi_sao_luu_luc_khi_chup_hong` |
| **V-04** | P0 | Khôi phục nuốt lỗi `tat_cung` rồi rollback ngay | Pha 04 | `test_554::test_khoi_phuc_KHONG_rollback_khi_may_con_dang_chay`; `test_289::test_khoi_phuc_TAT_MAY_truoc` (viết lại) |
| **V-05** | P1 | Một cột `trang_thai` gánh năm khái niệm | Pha 01 | `test_550::test_bon_khai_niem_cung_dung_mot_luc` |
| **V-06** | — | `lifecycle="development"`, Proxmox lồng | **giữ** | đúng sự thật; B-07 |
| **V-07** | P0 | Bốn route điều khiển chạy thẳng, không có khoá | Pha 02–03 | `test_553::test_may_dang_ban_thi_lenh_khac_bi_tu_choi`; `test_552::test_khoa_idem_la_rang_buoc_CSDL_chu_khong_phai_mot_cau_if` |
| **V-08** | — | Pack đòi "mô tả ảnh chụp cho đúng" | **đã đạt từ trước** | `sao_luu.py` docstring + `proxmox.py` — *actual HEAD wins* |

---

## 2. Bốn lỗi CHƯA AI BIẾT, tìm ra trong lúc làm

Không có trong pack, không có trong baseline. Cả bốn đều **im lặng**.

### 2.1 · Trần chờ tác vụ dài hơn trần của chính job chứa nó

`jobs.CHO_TAC_VU_S = 20*60` dùng chung cho mọi job, nhưng
`manifest.max_runtime_s["vps.destroy"] = 600`. Bộ chờ **không bao giờ** tới lượt
bỏ cuộc: nền tảng cắt job trước, và cái chết đó trông giống hệt một job treo —
không dòng log nào nói tác vụ Proxmox mới là thứ không xong.

Sửa: `tac_vu.han_theo_job()` lấy 80% trần của **chính job đang chạy**.
Ghim: `test_551::test_han_cho_moi_job_deu_ngan_hon_tran_cua_chinh_job_do` —
duyệt **từng** job type, nên thêm một job trần ngắn cũng không tái tạo được.

### 2.2 · Khoá idempotency rỗng va vào nhau

`khoa_idem` là `String(64) NOT NULL DEFAULT ''` trong ràng buộc
`(instance_id, khoa_idem)`. Chuỗi rỗng **tham gia** vào UNIQUE ⇒ một máy chỉ có
được **một** thao tác không khoá trong cả đời nó.

Sửa: cột thành `NULL`-able — cùng khuôn `uq_vps_instance_vmid`.
Ghim: `test_552::test_thao_tac_da_ket_thuc_khong_con_chiem_may`.

### 2.3 · "Cài lại" là một nút gỡ cách ly mà khách tự bấm được

`_cap_ip_cong_khai` gọi `gateway.mo_duong()` mỗi lần dựng máy. Một máy đang bị
cách ly mà khách bấm "Cài lại" sẽ được **mở lại đường NAT** — im lặng, không ghi
sổ, và người vận hành vẫn thấy `cach_ly_luc` khác NULL nên tưởng máy còn bị cắt.

Sửa: kiểm `dang_bi_cach_ly` **trước** `mo_duong`.
Ghim: `test_557::test_cai_lai_KHONG_tro_thanh_nut_go_cach_ly`.

### 2.4 · Bộ test async xanh mà tốn 301 giây

Bản đầu của `nhip` chỉ tiêm `ngu`, không tiêm đồng hồ. Hàm thôi ngủ nhưng hạn
chót vẫn tính theo `time.monotonic()` ⇒ mọi ca quá hạn **quay tít một lõi CPU**
cho đủ 300 giây thật. Bộ test vẫn **xanh** — nó chỉ chậm.

Sửa: `tac_vu.Nhip` gói đồng hồ + giấc ngủ vào **một** đối tượng, nên không ai
tiêm được nửa này mà quên nửa kia. Sau khi sửa: **3,86 giây**.

---

## 3. Ba phép kiểm CŨ được viết lại vì chúng không đo thứ chúng khai

Không phải "sửa test cho xanh" — cả ba đều **khó xanh hơn** sau khi viết lại.

| Phép kiểm | Bản cũ đo gì | Bản mới đo gì |
|---|---|---|
| `test_289::test_khoi_phuc_TAT_MAY_truoc` | `nguon.index("tat_cung") < nguon.index("khoi_phuc_anh")` — **thứ tự văn bản** | trạng thái điện thật **tại khoảnh khắc** `khoi_phuc_anh` được gọi |
| `test_289::_Client` | Proxmox đồng bộ (ảnh hiện ngay trong `chup_anh`) | ảnh chỉ hiện khi tác vụ nền **kết thúc tốt** |
| `test_251::test_manifest_khong_thu_theo_luot_job` | liệt kê cứng ba job type | mọi job type khai ra đều có trần **và** có handler |

Và một phép kiểm được sửa vì nó đo **thứ tự nạp module** chứ không đo sản phẩm:
`test_252::test_app_TAT_khong_lot_vao_trang_chu` — xanh khi chạy riêng, đỏ trong
một lượt rộng hơn, cùng một mã sản phẩm. `MANIFEST.enabled` tính một lần lúc nạp,
nên nó phụ thuộc test nào chạy trước trong cùng worker.

---

## 4. Kiến trúc sau chương trình

```
route (web, < 100s)                worker (job, có trần riêng)
  xin()  ─────────────────┐
   ├ kết nạp              │        thi_hanh()
   ├ mở thao tác (sổ)     └──────►  ├ hỏi thế giới thật
   ├ đặt ý định                     ├ gửi lệnh → ghi UPID
   └ nộp job                        ├ cho_xong()      ← tác vụ kết thúc TỐT?
                                    ├ cho_dien()      ← máy TỚI NƠI chưa?
                                    └ ghi_quan_sat()  ← đo được rồi mới ghi
```

Năm khái niệm tách rời trên `vps_instance`: `vong_doi` · `dien_mong_muon` ·
`dien_quan_sat` · `tac_vu` · `suc_khoe` + `quan_sat_luc`. Cột `trang_thai` cũ ở
lại làm **hình chiếu**, tính ở đúng một chỗ (`trang_thai_may.chieu`) — nhờ vậy
18 tệp test và 7 template không phải viết lại.

Bốn hàng rào cơ học, không phải quy ước:

1. `VpsInstance.__init__` chuẩn hoá ngay lúc dựng — không chờ ai nhớ gọi thêm;
2. ràng buộc `uq_vps_thao_tac_idem` là trọng tài chống bấm hai lần (không phải một câu `if`);
3. lease `vps-may:{id}` serialize ở worker; `thao_tac.mo` từ chối sớm ở route;
4. `test_560` đọc **AST** để canh: không ghi thẳng `trang_thai`, không `sleep`, không `except:` trần, không nuốt lỗi im lặng.

---

## 5. Cái KHÔNG làm, và vì sao

| Không làm | Vì sao | Ở đâu |
|---|---|---|
| Ảnh an toàn trước khi khôi phục | cùng pool ⇒ bảo đảm giả; đĩa là nút thắt | ADR-04 |
| Tự động cách ly theo heuristic | cắt mạng của một khách đang làm việc hợp lệ | `cach_ly.py`, `test_557` |
| Mở `/api/v1` cho VPS | hợp đồng API là *một lượt chạy*; VPS là *thuê có thời hạn* | ADR-06 |
| Chặn SMTP/25 mặc định | quyết định kinh doanh trên sản phẩm đang chạy | B-05 |
| Đổi `lifecycle` sang `released` | chưa có bằng chứng live | B-07 |
| Sửa lại V-08 theo snapshot của pack | HEAD đã đúng — *actual HEAD wins* | §1 |


---

## 6. Cổng chất lượng — hai lượt, và vì sao lượt đầu bị vứt

### Lượt 1 (pid 4404) — **KHÔNG dùng làm bằng chứng**

Tôi sửa tệp **trong lúc** nó chạy. Chính gate phát hiện và tự khai:

```
CAY DA DOI TRONG LUC CHAY:
    M apps/vps/jobs.py  (45642 -> 45895 byte)
    M apps/vps/services/proxmox.py  (23485 -> 23913 byte)
    M tools/do_token_may_b.py  (5336 -> 5624 byte)
Ket qua duoi day noi ve cay luc BAT DAU, khong phai cay hien tai.
```

Đó là lỗi quy trình của tôi, không phải của công cụ. Ghi lại vì nó đúng là loại
sai mà `docs/QUY_TAC_CHAY_LENH_NANG.md` cảnh báo: một phép đo trên một cây đang
động không nói về cây nào cả.

Lượt đó vẫn có ích ở một việc: nó **liệt kê** ra 16 lỗi để phân loại.

### Phân loại 16 lỗi của lượt 1

| Nhóm | Số | Của ai | Xử lý |
|---|---:|---|---|
| bảng mới chưa xếp loại lưu trữ + chưa vào drill khôi phục | 3 | **tôi** | thêm `Store(...)` **và** hàm dọn thật `thao_tac.don_cu`; thêm `uq_vps_thao_tac_idem` vào `restore_drill_schema.py` |
| thiếu tệp gitignored trong worktree | 3 | **môi trường** | chép `apps/upscalevideo/vendor` (48 MB) + `yolov8n.pt` sang cây này |
| `mypy` | 6 | 1 của tôi, 5 của phiên trước | sửa cả sáu |
| `nuot loi lang le` | 2 | 1 của tôi, 1 của `3eae396d` | thu hẹp ngoại lệ |
| `test_448` (ASV) | 7 | **phiên khác, đang dở** | ⛔ không đụng |
| đọc trúng lúc tệp đang ghi | 1 | lượt gate hỏng | chạy lại: xanh |

### Lượt 2 (pid 22868) — cây đứng yên, **là bằng chứng**

`RESULT: FAIL (2/32)` · 12,3 phút · **không** có dòng "cây đã đổi".

Còn lại: 7 × `test_448` + 3 lỗi dịch. Ba lỗi dịch là của tôi (một chuỗi `N_()`
mới trong `governance.py` chưa dịch) — đã sửa và kiểm lại xanh.

### `test_448` — vì sao KHÔNG sửa

Bảy lỗi này thuộc `auto_scan_video`, và hai commit cuối trước baseline của tôi
(`3eae396d`, `05464239`) đều là của một phiên khác đang điều tra đúng nó.

Bằng chứng cấu trúc — không phải suy đoán:

```
git diff --name-only HEAD | grep -c auto_scan_video   →  0
```

Chương trình này **không chạm một tệp nào** trong `apps/auto_scan_video`. Sửa
chúng là đi vào việc đang dở của phiên khác, và `CLAUDE.md` luật 12 cấm đúng điều đó.

---

## 7. Ba lần sửa NGOÀI phạm vi VPS — nói ra thay vì giấu

`START_HERE.md` §6 khoá phạm vi vào `apps/vps/**`. Ba chỗ dưới đây nằm ngoài, và
mỗi chỗ có một lý do cụ thể:

| Tệp | Vì sao buộc phải sửa |
|---|---|
| `platform_core/public_api/governance.py` | Nền tảng **bắt buộc** mọi bảng mới phải có xếp loại lưu trữ (`test_211`). Không khai thì gate đỏ, và khai suông không có hàm dọn thì cũng đỏ — đúng như nó nên thế |
| `tools/restore_drill_schema.py` | Ràng buộc duy nhất mới phải nằm trong drill khôi phục (`test_155`), nếu không lần khôi phục sau không ai kiểm nó |
| `tools/do_token_may_b.py`, `do_on_dinh_*`, `do_ngan_sach_*` | Ba **script đo** của phiên trước làm đỏ hai bánh cóc chung cho **mọi** phiên trên nhánh này. Sửa: một đổi tên biến + hai chú thích kiểu. Không đổi hành vi một chút nào |

⛔ Không dùng `--accept` để né bất kỳ lỗi nào trong số đó. Lần hạ mốc duy nhất là
`mypy`, và nó hạ vì số phát hiện **giảm thật** (123 thay vì 124).
