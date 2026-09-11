# LTT Voice — RELEASE VERIFICATION (2026-09-10)

Hai tang bang chung, tach bac. **Khong tang nao thay cho tang kia.**

## Tang 1 — CI-tat-dinh (mock, KHONG GPU)

Chung minh **duong ong** chay: worker → cong giong → ffprobe → kho → so credit,
va cac ranh gioi tu choi dung. Tieng la **GIA LAP**.

```
python tools\check_voice_qa.py          # rao chong-xanh-gia (tinh, ~1s) — o trong GATE
python tools\check_voice_qa.py --e2e     # + golden+negative that (tu dung server)
```

`--e2e` (hay `voice_e2e_check.py` truc tiep) tu dung:
- `voice_mock_sidecar.py` (cong giong GIA LAP, 8131) — sin 220 Hz + dau van tay
  `ltt-voice-mock`, header `X-Voice-Mock: 1`;
- `voice_e2e_server.py` (may chu cach ly + worker trong tien trinh, 8129) — sqlite
  dung mot lan duoi `tmp/voice_e2e/`, `_vram_can` ep ve 0 nen KHONG cham GPU that.

Muon soi bang mat / chay flow trinh duyet:

```
python tools\voice_mock_sidecar.py --cong 8131 --token mock-token
python tools\voice_e2e_server.py   --cong 8129 --mock-cong 8131
playwright-cli open --browser=chrome
playwright-cli run-code --filename=tests/browser/ltt_voice_golden.js
playwright-cli run-code --filename=tests/browser/ltt_voice_negative.js
playwright-cli run-code --filename=tests/browser/ltt_voice_smoke.js
```

## Tang 2 — LIVE acceptance (VieNeu THAT + GPU THAT)

⛔ Cham **GPU + so credit that**. La ranh gioi cua nguoi dung — KHONG tu chay.
Can tai khoan thu co credit; `chay_thu_ltt_voice.py` **khong tu nap**.

```
powershell -File .\setup\tai_khoan_thu.ps1              # tao tai khoan thu
python tools\chay_thu_ltt_voice.py --tai-ve out.wav      # golden qua worker THAT
python tools\cong_chat_luong_voice.py                    # cong chat luong (baseline)
```

`chay_thu_ltt_voice.py` di dung duong khach: hang doi → admission lease → worker
that → cong giong that → ffprobe → quyet toan credit, va **doi chieu SO du truoc/
sau** voi `credit_cost`. `cong_chat_luong_voice.py` do CER/WER/on-dinh-giong/RTF/
… so voi baseline ghim theo phien ban (fail-closed).

Dieu kien coi la LIVE_GPU_VERIFIED:
- `chay_thu_ltt_voice.py` in `KET QUA: done`, `da_tru == credit_cost`, tep WAV > 0;
- `cong_chat_luong_voice.py` in `CONG XANH`.

## RAO CHONG-XANH-GIA (false-green guards) — vi sao moi cai ton tai

| rao | o dau | chan lop loi |
|---|---|---|
| tap hop test Voice chot theo TEN | `check_voice_qa.py` INVENTORY | suite tu rong ruot / doi ten mat |
| mock tu khai gia lap 3 kenh | `check_voice_qa.py` MOCK-LABEL + `voice_mock_sidecar.py` | tieng gia bi doc nham la that |
| tang LIVE khong dinh mock | `check_voice_qa.py` LIVE-PURITY | "mock dung trong suite ten live" |
| may chu E2E co 2 rao + VRAM=0 | `check_voice_qa.py` E2E-ISOLATION | E2E cham CSDL/GPU production |
| flow tro loopback + co `throw` | `check_voice_qa.py` BROWSER | flow khong the ĐO / tro production |
| job phai THAT SU `done` | `voice_e2e_check.py` G1 | coi moi trang thai cuoi la "xong" |
| WAV RIFF hop le + credit>0 | `voice_e2e_check.py` G2, golden.js | 200 rong doc nham la thanh cong |
| moi negative phai 400+ok:false | `voice_e2e_check.py` G3, negative.js | mot cua vo tinh mo |
| so phep kiem == khai bao | `voice_e2e_check.py` G4 | thu thap = 0 bat thuong |
| WAV mang dau van tay mock | `voice_e2e_check.py` G5, golden.js | da tro vao cong THAT (sai tang) |
| 0 loi console | golden.js, smoke.js | trang vo ma test khong thay |

⭐ Cac rao da duoc doi chung (10/09): `voice_e2e_check` **ĐO** khi cong giay lam
cong giong chet (job HET GIO); `check_voice_qa` **ĐO** khi thieu mock. Mot rao
chua tung ĐO la mot rao vo dung.
