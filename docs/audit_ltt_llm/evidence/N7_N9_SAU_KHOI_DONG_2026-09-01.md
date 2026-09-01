# N7/N9 — SO DO THAT, may A khoi dong lai 2026-09-01

Do trong khoang boot+7min (luot 1, quyen user) va boot+15min (luot 2, LocalSystem
qua NexusAgent). Nguon: `tmp/sau_khoi_dong.json`, `tmp/sau_khoi_dong_system.json`,
+ cac phep do bo sung duoi day.

## Moc thoi gian (tat ca lay tu runtime that, khong suy luan)

| Moc | Gio may (local) | UTC | Tu luc boot | Nguon |
|---|---|---|---|---|
| Windows boot | 15:51:28.500 | 08:51:28.5 | +0 | `Win32_OperatingSystem.LastBootUpTime` |
| Driver `dam` khong nap duoc | 15:51:48 | — | +19.5s | System log id=7026 |
| 5 vo boc NSSM sinh ra (ca 5 cung luc) | 15:51:44.187 | — | **+15.7s** | `Win32_Process.CreationDate` cua PID cua tung service |
| Worker pool bao "da nang x2" | — | 08:51:48.181 | **+19.7s** | `logs/ltt-job-worker.jsonl` |
| cloudflared: precheck PASS toan bo | — | 08:51:48 | +19.5s | `logs/cloudflared-nssm-err.log` |
| cloudflared: 4 tunnel connection registered | — | 08:51:49 | **+20.5s** | cung tren (connIndex 0..3) |

## N7 — dien tap reboot: DAT

- Ca **5** dich vu `StartMode=Auto` va `Status=Running` sau reboot khong nguoi cham:
  `cloudflared`, `LTTStudioWeb`, `LTTStudioWorker`, `LTTStudioVoice`, `LTTStudioCodex`.
- **Khong** dich vu nao phai nho `FAILURE_ACTIONS` dung day: toan bo System log
  tu luc boot chi co **3** su kien Service Control Manager, va **khong su kien nao**
  lien quan toi LTTStudio/cloudflared (kiem ca theo ProviderName lan quet ca log).
- Cong tu khai khong mo coi: `vo_boc_pid=4616` sinh 15:51:44, `mo_coi=false`.
- `LTT_WORKER_POOLS` **KHONG DAT** -> giu hanh vi mac dinh. (Luot chay bang quyen
  user KHONG doc duoc app.env va bao "KHONG DOC DUOC"; chi luot LocalSystem moi
  ket luan duoc. Day la mot chot that su can quyen.)
- LTT VOICE: dich vu Running, sidecar 8120 tra 401 (song, co xac thuc), `voice_sidecar_song=true`.
- May B khong bi anh huong (cong 8299 song) -- dung nhu du kien, no la may khac.

## N9 — nhat ky khoi dong: DAT, nhung KHONG bang duong da du dinh

⚠️ Duong da du dinh (doc `Service Control Manager` 7036 trong System log) **khong
bao gio hoat dong duoc tren may nay** -- khong phai vi thieu quyen.

Bang chung: chay lai chinh cau truy van do bang **LocalSystem** (`whoami` =
`nt authority\system`):

    TONG SU KIEN SCM tu luc boot: 3
    KHOP 'LTTStudio|cloudflared'  : 0

Ba su kien do la: 7026 (driver `dam` khong nap), 7000 + 7009 (dich vu Coc Coc
Update timeout). Windows tren may nay **khong ghi** 7036 "entered the running
state". => Thu tu len phai do bang `Win32_Process.CreationDate` + timestamp trong
log ung dung, nhu bang o tren.

## KHUYET TAT TIM DUOC TRONG CHINH CONG CU DO

**D-1 (`tools/do_sau_khoi_dong.py` §3): mot cau tra loi SAI mac mot loi giai
thich nghe hop ly.** Khi truy van tra ve rong, cong cu ket luan
`"KHONG DOC DUOC (can Administrator)"` va in 6 dong huong dan chay lai bang
LocalSystem. Da lam dung y do -- ket qua **y het**. Nguyen nhan that la
"khong co su kien nao", tuc chinh cai ma comment trong code dan do
("dung tra danh sach rong, rong doc len y het 'khong co su kien nao'").
Cong cu tranh duoc bay do bang cach... noi mot cau sai khac.
Day la **cung lop loi** voi `tools/api_prod_canary.py` (doc sai truong roi in
"rong -- dung y muon"), da ghi o `CLAUDE.md`.

**D-2 (`tools/do_sau_khoi_dong.py` §4): nhan sai ten phep do.** Muc ghi
"Bao lau toi khi /health/ready xanh" nhung `t0 = time.monotonic()` dat o **luc
goi cong cu**, khong phai luc boot. Chay o boot+7min no in `0.5s`; chay lai o
boot+15min no in `0.6s`. Ca hai deu la "do tre cua mot request /health/ready
luc nay", KHONG phai "boot -> ready". So that cua boot->ready **chua tung duoc
do** va khong con do duoc nua o luot boot nay; chan tren la +19.7s (luc worker
bao san sang).
