# 06 — RUNTIME / JOB / CREDIT / TÁC DỤNG PHỤ

**Ngày:** 2026-08-26 · **Cây:** `3d804ee` · **Đầu vào:** 00–05 + hợp đồng nghiệm thu

---

## 1. Máy trạng thái job — lành

```
submit → queued → claimed → running → done|error|cancelled
                     ↑           │
                     └── reclaim_orphans (quá hạn đập nhịp)
```

| Tính chất | Trạng thái | Bằng chứng |
|---|---|---|
| Claim nguyên tử | ✅ | `SKIP LOCKED`, claim commit riêng một transaction ngắn |
| Lease + đập nhịp | ✅ | `gpu_lease` nhịp ngắn hơn nhiều `ORPHAN_TIMEOUT` 10 phút |
| Thu hồi mồ côi | ✅ | `jobs.reclaim_orphans` — **đếm lượt đã tiêu**, job làm treo worker không quay lại vô hạn |
| Quyết toán idempotent | ✅ | `_khoa_ket_so_job` + `_ket_qua_da_chot` |
| Việc nền chạy một lần/cụm | ✅ | `leases.MAINTENANCE` |
| 19 job_type ↔ handler | ✅ | không mồ côi hai chiều |

⇒ **Đường tiền qua worker an toàn**: job luôn tới trạng thái cuối, nên tiền luôn
được kết sổ.

---

## 2. 🔴 M-01 — đường tiền **trong request** không có đường về

### 2.1 Sự thật, mức E4

Đo trên CSDL production 26/08 *(phiên `lttstudiosapp-3a` thực hiện; phiên này
chưa được cấp quyền đọc production)*:

```
Tổng bút toán 'hold'              : 123 bút toán, 1.105 credit
Giữ chỗ CHƯA settle CHƯA refund   : 2   (cả hai KHÔNG có hàng Job)
    ms:de4cc565…   1 credit   2026-08-24 22:28:06
    ms:84e9b141…   1 credit   2026-08-24 23:58:10
Máy dò cũ (`job_id = ''`) bắt được: 0 / 2
```

⭐ **Con số đáng sợ không phải "2 credit".** Dòng `23:58:10` có người tình cờ thấy
và ghi vào `docs/PUBLIC_API/KE_HOACH_MVP_CONG_LAP_TRINH_VIEN.md` §P2-4. Dòng
`22:28:06` **không ai ghi ở đâu cả**. ⇒ Tỉ lệ phát hiện thủ công **1/2**, nghĩa
là con số thật **≥** con số biết, không bao giờ nhỏ hơn.

### 2.2 Cách gọi tên đúng

> **Lưới hoàn tiền CÓ, nhưng chỉ căng bên trong tiến trình — và deploy là hành
> động giết tiến trình.**

`setup/2-cai-dat.ps1:107-111` `Stop-Service -Force` cả ba dịch vụ trước khi chép
đè. `except BaseException` là mã Python; nó không chạy khi Windows kết liễu tiến
trình.

⇒ Đây không phải một lỗ hổng chung chung. Đây là **một quy trình vận hành tự mở
lỗ của chính nó**, đều đặn, rộng bằng đúng độ dài một luồng LLM (đã đo 119 giây).

### 2.3 Bốn đường, bốn mức bảo vệ, **không đường nào sống sót**

| Đường | Lưới trong tiến trình | Sống sót khi bị giết |
|---|---|---|
| `server/api/streaming.py` (`/messages`, `/responses`) | ✅ `except BaseException` (vá 25/08) | ❌ |
| `apps/chataistudio/routes.py:228` | ⚠️ một phần — `finally` xử `GeneratorExit` | ❌ |
| `apps/chataistudio/routes.py:464` | ❌ giữ/quyết toán/hoàn ở **ba hàm rời** | ❌ |
| `platform_core/agent/budget.py:86` | ❌ `settle()` hoàn phần thừa, **không ai quét run treo** | ❌ |

`agent/budget` để lại hàng `AgentRun` **bền vững** ở `AGENT_RUNNING` — về nguyên
tắc thu hồi được. Nhưng grep `AGENT_RUNNING`/`AgentRun` + `sweep|stale|orphan|reclaim`
⇒ **trống**. "Về nguyên tắc thu hồi được" chỉ thành "thu hồi được" khi có ai viết
vòng quét.

⚠️ Số production cho đường này: `agent_runs` **n=4**, 0 rò. Đọc cho đúng: nó chưa
rò **vì mẫu quá nhỏ**, không phải vì nó an toàn.

### 2.4 ⭐ Mã tự tố cáo chính nó

Chú thích tại `streaming.py:257`, viết bởi người vá lỗi 25/08:

> *"⚠️ Và KHÔNG AI QUÉT NÓ. Đường đồng bộ này không tạo `Job`, nên `_hoan_credit`
> của worker không bao giờ nhìn thấy. Khách mất tiền lặng lẽ, và không có báo cáo
> nào chỉ ra điều đó."*

Người viết **đã biết**, **đã ghi ra**, và việc treo chuông vẫn không vào lịch.

⇒ **M-01 không phải một khám phá. Nó là một việc đã biết mà chưa ai xếp lịch.**
Đó là **P-01**, và nó quan trọng hơn M-01.

### 2.5 Đã sửa — `a5274bf`

| Việc | Trạng thái |
|---|---|
| `credit.giu_cho_treo()` — phép đo thật, đặt ở **chủ sở hữu cuốn sổ** | ✅ |
| `usage.reconcile` bỏ vị ngữ mù | ✅ |
| Loại cảnh báo `HOLD_STRANDED` gửi người vận hành, **có email** | ✅ |
| Cắm vào `_mot_luot_bao_tri` dưới lease ⇒ một lần/cụm | ✅ |
| 14 test, gồm cả **"chuông IM khi phải im"** | ✅ |

⛔ **CHỈ BÁO, KHÔNG TỰ HOÀN.** Ghi bút toán bù là quyết định tiền ⇒ **D-07**.

⇒ INV-5 hiện được **quan sát**, chưa được **bảo đảm**. Bảo đảm cần `hold_expires_at`
+ tự hoàn (phương án B), và đó là thay đổi schema + đường tiền.

---

## 3. Kiểm kê 24 điểm đổi tiền

```
giu_cho  8      quyet_toan  4      hoan  8
tru      2      hoan_phi    1      nap   1
```

`credit.tru()` — **trừ thẳng, không giữ chỗ** — dùng ở 2 chỗ, đều là mô hình thuê
bao: `apps/vps/services/billing.py:106`, `platform_core/nexus/billing.py:103`.

⚠️ **Rủi ro riêng của chúng:** chạy hai lần trong một chu kỳ thì trừ hai lần. Cả
hai chạy dưới `AppManifest.bao_tri` ⇒ dưới lease `bao_tri` ⇒ **về lý thuyết** một
lần/cụm. `CLAUDE.md` ghi rõ *"app tự dựng vòng lặp sẽ trừ tiền khách N lần mỗi
chu kỳ"* — nghĩa là bài học này đã trả giá một lần.

**Còn nợ bằng chứng:** một test đa tiến trình chứng minh `tru()` chỉ chạy một
lần/chu kỳ trên **hai** tiến trình worker. `test_214` có hạ tầng đó — chưa phủ ca
này.

---

## 4. Ma trận cửa sổ hỏng

| Cửa sổ | Job qua worker | Trong request |
|---|---|---|
| state chưa commit / side effect chưa xảy ra | an toàn (cùng transaction) | an toàn |
| state commit / side effect chưa xảy ra | `reclaim_orphans` | ⚠️ **M-01** |
| side effect xảy ra / state rollback | `quyet_toan_hoac_hoan` xử | ⚠️ hoàn đủ nếu bắt được |
| **tiến trình chết trước ACK** | `reclaim_orphans` | 🔴 **M-01 — tiền kẹt** |
| timeout không rõ kết quả | `KhongDoDuocError` ⇒ hoàn đủ | ⇒ hoàn đủ |
| retry trùng | idempotent theo `job_id` | idempotent theo `request_id` |

Chỉ **một** ô đỏ, và nó đã có máy dò.

---

## 5. Việc còn nợ

| ID | Việc | Mức |
|---|---|---|
| **M-01b** | Test tái hiện giết tiến trình giữa luồng (CSDL test) | P1 |
| **M-03** | Test đa tiến trình cho `credit.tru()` của vps/nexus | P2 |
| **M-04** | Vòng quét `AgentRun` treo — khuôn có sẵn: `reclaim_orphans` | P2 |
| **D-07** | Bù 2 credit đã kẹt cho khách | quyết định chủ sản phẩm |

---

```text
NO_RUNTIME_CHANGE: NO   (a5274bf — P0 tiền khách, §I cho phép)
```
