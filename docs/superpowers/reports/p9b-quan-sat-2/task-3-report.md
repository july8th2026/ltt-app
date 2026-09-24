# P9b Task 3 - Frontend doc run bang SSE thay vong poll (XONG)

**Cham:** `frontend/agent-canvas/src/workflowApi.ts` (`theoDoiRunV3`),
`src/CanvasShell.tsx` (effect doc run), `tests/setup.ts` (bo doi `EventSource`
cho jsdom), `tests/CanvasShell.test.tsx`.

## Nguon
- `apps/agent/routes/runs_v3.py::v3_su_kien_sse` (lan p9 da dung): `GET` thuan,
  quet CSDL 1 s, dong o 90 s (duoi tran 100 s cua Cloudflare), `Last-Event-ID`
  thang `?sau=`.
- MDN `EventSource`: co san co che noi lai, **co dinh ~3 s, khong lui dan,
  khong noi gi**. Do chinh la ly do ⛔ KHONG dung no.

## 🔴 Cho de MAT chong-ngap - da mac, da do duoc, da sua
Ban dau toi mo luong ngay trong than effect: `soHong` doi -> effect chay lai ->
mo lai **tuc thi**. Lui dan bien mat ma moi bai cu van xanh. Bai
`hong lien tiep thi LUI DAN` bat duoc: khoang cach giua hai lan mo la **21 ms**.
Sua: `setTimeout(mo, soHong > 0 ? nhipCho(soHong - 1) : 0)` - giu nguyen ba con
so cu (1,5s -> 3s -> 6s -> 12s) va dong loi nhin thay duoc.

**Doi chung (tiem lai loi):** dat lai giãn cach ve `0` roi chay dung bai ay:
```
AssertionError: expected 21 to be greater than 900
```
Banh coc can that.

## Hai loai "luong dong", khong duoc lan
- **DA nhan goi roi moi dong** = moc 90 s cua may chu ⇒ noi lai NGAY, khong
  lui, ⛔ khong hien dong loi. (Co `lanNoiLai` rieng, khong dung `soHong`.)
- **Dong ma chua nhan gi** = hong that ⇒ `soHong + 1`, lui dan, hien loi.
`theoDoiRunV3` dong luong ngay trong `onerror` truoc khi bao len, de
`EventSource` khong kip tu noi lai ngoai tam kiem soat.

## Dong do / dong xanh
```
Tests  8 failed | 21 passed (29)    (EventSource is not defined - jsdom khong co)
Tests  32 passed (32)               (sau khi them bo doi + 3 bai SSE moi)
npm run typecheck                   sach
```

## 🔴 BANG CHUNG TRINH DUYET (Chromium that, Playwright, cong 8177 CO LAP)
CSDL sqlite vut di, ⛔ khong dung cong 8100 (production). Dang nhap bang cookie
cua mot tai khoan test tu tao; ⛔ khong go mat khau nao trong trinh duyet.
```
TIEU DE: Canvas - LTT Agent AI
TRANG THAI RUN TREN GIAO DIEN: QUEUED
HUY TU NGOAI TRANG: 200
TRANG THAI SAU KHI HUY (chi SSE dua ve duoc): CANCELLED
--- LOI CONSOLE (0) ---
--- MANG HONG (0) ---
--- GOI DOC RUN (1) ---
  200 .../agent/api/v3/runs/9685a2ce-.../su-kien?sau=1 :: text/event-stream; charset=utf-8
```
Ba dieu doc duoc tu do:
1. **Dung MOT goi doc run**, va no la SSE. ⛔ Khong con `GET /runs/{id}?sau=`.
2. Man hinh doi **QUEUED -> CANCELLED** sau mot POST huy phat ra TU NGOAI trang
   (JavaScript cua trang khong he goi no) - duong duy nhat tin ay ve toi DOM la
   luong SSE.
3. 0 loi console, 0 request hong.

Cache-bust: bundle vite mang ten co bam (`main-<hash>.js`, doc tu manifest qua
`bundle_assets`), nen khong can `?v=`; chinh phep kiem tren chung minh trinh
duyet da nap ban MOI.

## Chua lam duoc
- Bo doi `EventSource` trong `tests/setup.ts` thay cho API cua trinh duyet, nen
  vitest **khong** doc khung SSE that; phan do la viec cua phep kiem trinh
  duyet o tren.
- Nut "Thu lai node" va man hinh diff hai run (task 1, 2) chua co tren giao
  dien - cua may da xong.
