# RUNBOOK — khôi phục dữ liệu VPS

> Tài liệu này viết cho **người vận hành lúc 3 giờ sáng**, không phải cho người
> đang đọc để học. Nên nó bắt đầu bằng câu hỏi thay vì bằng kiến trúc.

---

## 0. Trước hết: mất cái gì?

| Triệu chứng | Còn cứu được không | Đi tới |
|---|---|---|
| Khách xoá nhầm thư mục, cài nhầm phần mềm, bản vá làm hỏng Windows | ✅ **có** | [§1](#1) |
| Một VM biến mất khỏi Proxmox nhưng pool `vmdata` còn nguyên | ⚠️ **không** — ảnh chụp đi theo VM | [§3](#3) |
| Pool `vmdata` hỏng, hoặc đĩa vật lý chết | ❌ **KHÔNG** | [§4](#4) |
| Cả node `pve` chết | ❌ **KHÔNG** | [§4](#4) |

⚠️ Hai dòng cuối là sự thật hôm nay, không phải một cảnh báo lý thuyết. Ảnh chụp
LVM-thin nằm **cùng pool** với đĩa gốc. Chưa có lớp sao lưu độc lập —
`apps/vps/sao_luu_doc_lap.nang_luc()` trả `sao_luu_doc_lap=False`, và trang máy
phải nói đúng như vậy.

---

## 1. Khôi phục về ảnh chụp hằng tuần {#1}

### Đường của khách (tự làm được)

Trang máy → khối **Nguy hiểm** → *Khôi phục về ảnh chụp* → gõ đúng tên máy.

Việc chạy nền: tắt cứng → chờ máy **thật sự** STOPPED → hỏi lại xem ảnh còn đó
không → rollback → chờ tác vụ → bật lại nếu máy đang chạy trước đó.

Theo dõi tiến độ: cột `buoc` của `vps_thao_tac` (`tat_truoc_khoi_phuc` →
`dang_khoi_phuc_anh` → `bat_lai_sau_khoi_phuc`).

### Nó KHÔNG làm gì

* Không chụp "ảnh an toàn" trước khi rollback — cố ý, xem `ADR_INDEX.md` ADR-04.
* Không giữ nhiều bản: đúng **một** bản, khoảng bảy ngày tuổi.

### Khi khách bấm mà không có gì xảy ra

```sql
SELECT id, loai, trang_thai, buoc, ma_loi, chi_tiet_loi, han_luc
FROM vps_thao_tac WHERE instance_id = '<id>' ORDER BY tao_luc DESC LIMIT 5;
```

* `trang_thai='dang_chay'` và `han_luc` còn ở tương lai ⇒ **đang chạy**, chờ.
* `trang_thai='qua_han'` ⇒ worker chết giữa chừng. Vòng bảo trì đã mở khoá máy.
  **Hỏi Proxmox trước khi bấm lại** (xem §2) — việc đó có thể đã xong.
* `trang_thai='hong'` ⇒ đọc `ma_loi`:
  * `dien_khong_dat` — máy không tắt được. Thử *Tắt cứng* rồi khôi phục lại.
  * `anh_khong_dung` — ảnh đã bị vòng bảo trì dọn. Không cứu được bản đó.
  * `proxmox_tu_choi` — đọc `chi_tiet_loi`.

---

## 2. Hỏi thế giới thật {#2}

⛔ **Đừng bấm lại một thao tác phá huỷ trước khi làm bước này.** Một lần khôi
phục "quá hạn" có thể đã chạy xong; bấm lại là rollback **lần thứ hai**, và nó
xoá mọi thứ khách làm sau lần khôi phục đầu.

```bash
python tools/api_prod_canary.py trang-thai
```

Trên máy chủ, hỏi thẳng Proxmox:

```bash
pvesh get /nodes/pve/qemu/<vmid>/status/current
pvesh get /nodes/pve/qemu/<vmid>/snapshot
```

---

## 3. VM biến mất khỏi Proxmox {#3}

Vòng đối chiếu sẽ báo mức `vo_bat_bien` với nhãn *"May trong CSDL khong co VM"* —
tức khách **đang trả tiền cho một máy không tồn tại**.

Bốn việc, theo thứ tự:

1. **Dừng thu tiền** cho máy đó trước khi làm gì khác.
2. Kiểm log Proxmox xem VM bị xoá lúc nào và bởi ai (`/var/log/pve/tasks/`).
3. Ảnh chụp **đã mất theo VM** — không có đường khôi phục dữ liệu.
4. Quyết định thương mại: hoàn credit chu kỳ đang chạy.

---

## 4. Hỏng pool hoặc hỏng node {#4}

**Không có đường khôi phục dữ liệu khách.** Nói thẳng, sớm.

Đây không phải một khiếm khuyết của mã — nó là hệ quả của việc chưa dựng lớp B.
Điều kiện để câu này đổi:

* một đích sao lưu có **failure domain độc lập** (PBS, hoặc tương đương);
* khai vào `LTT_VPS_PBS_URL` / `_DATASTORE` / `_USER`;
* một job sao lưu chạy theo lịch, **và** một job xác minh chạy sau nó;
* một lần **diễn tập khôi phục** thật, có ghi lại kết quả.

Thiếu bất kỳ mục nào ⇒ `nang_luc().chong_hong_phan_cung` vẫn phải trả `False`.
Điền biến môi trường mà không chạy job là dựng đúng cái nhãn xanh giả mà cả
chương trình này sinh ra để dọn.

---

## 5. Diễn tập khôi phục — khi đã có lớp B

Chưa chạy được hôm nay. Ghi ra đây để lần đầu có hạ tầng thì không phải nghĩ lại:

1. chọn một máy **thử của chương trình**, không phải máy khách;
2. ghi lại một dấu vết kiểm chứng được vào trong máy (một tệp có nội dung + giờ);
3. chạy một lượt sao lưu, chờ **và** xác minh;
4. khôi phục vào một **định danh cô lập** — VMID khác, MAC khác, không NAT;
5. bật, vào console, kiểm dấu vết ở bước 2;
6. ghi kết quả + thời gian vào `docs/vps_v2/KNOWN_BLOCKERS.md`;
7. xoá máy thử, kiểm cả VM lẫn IP đã được trả về.

⚠️ Bước 4 không phải hình thức: khôi phục vào **đúng** định danh cũ giữa lúc máy
gốc còn sống là hai máy cùng MAC và cùng IP trong một mạng — mất kết nối của cả
hai, và triệu chứng không chỉ về đâu cả.
