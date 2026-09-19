# Pha 13 — sổ tay thi hành (soạn trong lúc gate chạy)

> ⚠️ **Ảnh chụp 09/09/2026** (tệp này) — không phải hiện trạng. Số đồng thời LLM ở đây
> (`DONG_THOI_MAY_B=1`, `parallel=1`, một suất máy B…) **đã cũ** → `apps/ltt_llm/ngan_sach.HO_SO`
> (L-23, L-28 trong `docs/ltt_llm_dual/DECISION_LOG.md`).

**Chỉ bắt đầu khi:** gate lượt xác nhận xong, và 9 lỗi rút còn **7** (đúng nợ
`test_448` của trunk, không thêm gì).

---

## Bước 0 — đo lại trunk, vì số cũ đã hết hạn

Số đo 17:47 nói trunk `05464239` **FAIL (3/32)**. Số ấy của phiên khác, và trunk
đi rất nhanh. Đo lại **ngay trước khi hoà**, không dùng lại số cũ.

```
git -C D:\LTTSTUDIOSAPP-aiclean rev-parse --short admin-mvp-v3
git -C D:\LTTSTUDIOSAPP-aiclean rev-list --count 0d1ffe5a..admin-mvp-v3
```

Nếu SHA khác `05464239` ⇒ đo lại cả bề mặt hoà (`merge-tree`, và hai phép
đối chứng ở dưới), vì kết quả 18:4x chỉ đúng cho `05464239`.

### Bề mặt hoà đã đo lúc 18:4x (cho `05464239`, **24 commit** trước tôi)

| Câu hỏi | Kết quả | Đối chứng |
|---|---|---|
| Xung đột văn bản | **0** (`merge-tree --write-tree` rc=0) | — |
| Trunk có THÊM tham chiếu tới thứ đã gỡ | **0** | cùng đường ống, `voice` cho **273** |
| Trunk có sửa tệp nào trong 36 tệp tôi xoá | **0** | hai danh sách 36 / 120, không rỗng |

⚠️ **Sạch văn bản ≠ sạch nghĩa.** Ba số 0 trên trả lời "có va nhau không", chúng
**không** trả lời "hoà xong có chạy đúng không". Câu ấy chỉ gate sau hoà trả lời.

---

## Bước 1 — hoà và đẩy

```
worktree/branch → changes → tests → commit → push branch
                → merge → push master → deploy → verify → dọn nhánh remote
```

⛔ Không xoá repo, không tạo lại repo, không xoá master, không force-push master.
⛔ Dọn nhánh remote là **pha 14**, không làm sớm.

---

## Bước 2 — deploy

⚠️ **Deploy xuất HEAD cây chính** (`git archive` + `$VAN_CHUYEN`, `setup/2-cai-dat.ps1`; tệp chưa commit không lên). Vẫn hỏi các phiên khác trước (`ListAgents`), và
kiểm `git status` — một dòng `??` lạ là một phiên khác đang làm việc.

⚠️ Cửa sổ cấm ghi **kéo dài tới hết nghiệm thu**, không dừng ở lúc chép xong.

---

## Bước 3 — đóng nốt pha 11: **5 đường sinh thật**

Đây là thứ duy nhất nâng được trục E2E khỏi **6/10**. Không suy PASS từ test
xanh — bộ test dùng điều phối giả.

| # | Đường | Cách chạy |
|---|---|---|
| 1 | LTT_LLM Text | `tools\api_prod_canary.py`, một lượt thật |
| 2 | LTT_LLM VLM | như trên, có ảnh |
| 3 | LTT_IMAGE vẽ thật | một lượt qua `anhnoibo`/`taoanh` |
| 4 | Voice | cần sidecar VOICE + GPU |
| 5 | Seedance/BytePlus | **tốn tiền thật** — chốt với chủ dự án trước |

⚠️ Máy B chỉ có **MỘT suất đồng thời** (`DONG_THOI_MAY_B=1`) ⇒ ba đường đầu
**loại trừ nhau**, chạy nối tiếp. Và `/health` + CPU máy A đều **không** trả lời
được câu "B có rảnh không".

---

## Bước 4 — dọn bí mật và dịch vụ chết (nâng trục Secrets 8/10)

### 4a. `LTT_CODEX_SIDECAR_TOKEN` trong `app.env`

⛔ **Sửa `app.env` rồi `Restart-Service` là KHÔNG ĐỦ** — `nssm` nướng ENV vào
cấu hình dịch vụ **lúc CÀI**. Đã dính **ba lần**.

```
sửa app.env  →  setup\nap_lai_env.ps1  →  restart
```

⚠️ Và **cấu hình dịch vụ LÀ nơi chứa bí mật**: một `nssm get` in sạch khoá
production ra log. Đừng dump nó ra đâu cả.

### 4b. Gỡ dịch vụ Windows `LTTStudioCodex`

Mã đã xoá ở pha 07, `setup\2-cai-dat.ps1` đã đổi khối CÀI thành khối GỠ — nhưng
dịch vụ **vẫn đang chạy trên máy chủ**. Xoá mã không xoá một dịch vụ đã đăng ký.

Cần UAC ⇒ khuôn hai lớp `Start-Process -Verb RunAs` (AGENTS §9.3).

---

## Bước 5 — nghiệm thu deploy, hỏi **BA** chiều

So với **COMMIT**, không so với cây. Chiều `thừa` là chiều **duy nhất** bắt được
deploy từ một cây bẩn.

```
/health/version  →  commit + asset_ver + hợp đồng app
điểm xuất phát   →  app.previous\dau_van_tay.json
migration        →  hỏi alembic_version, KHÔNG git diff
```

⛔ Hỏi `/health/version` **sau** deploy thì vô dụng cho câu "đã đổi gì" — phải có
điểm xuất phát.

---

## Sau pha 13

- **Pha 14** — dọn 22 nhánh remote
- **Pha 15** — báo cáo nén kho
- Chấm lại điểm: E2E 6/10 và Secrets 8/10 là hai trục pha 13 nâng được; App
  surface 9/10 thì không (`brand_directive` chưa đo).
