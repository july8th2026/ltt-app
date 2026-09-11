# LTT Voice — TEST MATRIX (2026-09-10)

Ma tran phu tung tinh nang qua **nam tang**. Hai tang cuoi tach bac co chu y:

| tang | chay o dau | tieng that? | chay trong gate? |
|---|---|---|---|
| unit / integration | `pytest` (qua `test_nhanh.py`) | khong (mock/khong goi cong) | ✅ |
| browser (E2E) | `playwright-cli` + `voice_e2e_server.py` | **GIA LAP** (`voice_mock_sidecar.py`) | ⛔ nghiem thu phat hanh |
| CI-mock E2E | `voice_e2e_check.py` (tu dung server) | **GIA LAP** | ⛔ nghiem thu phat hanh |
| rao chong-xanh-gia | `check_voice_qa.py` | — (rao tinh) | ✅ |
| LIVE acceptance | `chay_thu_ltt_voice.py`, `cong_chat_luong_voice.py` | **THAT** (VieNeu + GPU) | ⛔ tren dich vu that |

⛔ **CI-mock KHONG thay cho LIVE.** Tieng o hai tang browser/CI-mock do
`voice_mock_sidecar.py` sinh — mot sin 220 Hz mang dau van tay `ltt-voice-mock`.
No chung minh **duong ong** (worker → cong → ffprobe → kho → credit) chay, khong
chung minh **chat luong nghe duoc**. Chat luong la viec cua `cong_chat_luong_voice.py`.

## Ma tran tinh nang → tang

| Tinh nang | unit / integration (pytest) | browser | CI-mock E2E | LIVE GPU |
|---|---|---|---|---|
| Create Voice (synthesize) | `test_347_ltt_voice_studio`, `test_338_ltt_voice_hop_dong` | `ltt_voice_golden.js` | golden | `chay_thu_ltt_voice.py` |
| Preset preview (xem-truoc / nghe-thu) | `test_347` (`xem_truoc`), `test_500_ltt_voice_nghe_thu` | golden (Studio) | — | — |
| Language compatibility (lan vi/en) | `test_384_lan_ngon_ngu`, `test_355_hop_dong_lan_giong` | `ltt_voice_negative.js` (mo ho, khong chan); `ltt_voice_rc1.js` LUONG 5 (doan CHAC, CHAN — D002) | — | — |
| My Voices | `test_345_ltt_voice_giong_mau`, `test_382_kho_tham_chieu` | `ltt_voice_smoke.js` | — | — |
| Enrollment (ghi danh) | `test_367_chon_doan_tham_chieu`, `test_382_kho_tham_chieu` | — | — | `chay_thu_ghi_danh.py` |
| Projects (du an) | `test_350_ltt_voice_du_an` | `ltt_voice_smoke.js` | — | — |
| Long-form (noi dai) | `test_342_ltt_voice_noi_dai`, `test_396_ban_doc_dai` | — | (endpoint `/v1/speech-dai` co o mock) | `chay_thu_ltt_voice.py --text <dai>` |
| History (lich su) | `test_348_ltt_voice_lich_su` | `ltt_voice_smoke.js` | — | — |
| Download (audio serving) | `test_346_ltt_voice_cua_audio` | golden (tai WAV + kiem RIFF) | golden (G2) | — |
| Public API / man API | `test_364_ltt_voice_man_api`, `test_338` (ToolSpec) | — | — | `bench_public_api_key.py` |
| Jobs (hang doi/worker/lease) | `test_67…` (nen tang) + `test_347::_tao_job` | golden (queued→done) | golden (G1) | `chay_thu_ltt_voice.py` |
| Credit (giu + quyet toan) | `test_337_ltt_voice_gia` | golden (hien "Holding … credits") | golden (G2: credit>0) | `chay_thu_ltt_voice.py` (doi chieu SO tien) |
| Storage | `test_346` (doc tu kho) | golden (206 Partial Content) | golden | — |
| User isolation | `test_347::test_ket_qua_cua_nguoi_khac_tra_404` | — | — | — |
| Pronunciation dict | `test_391_tu_dien_rieng` | — | — | — |
| Char boundary / Unicode | `test_397_ltt_voice_bien_ky_tu` (32) | negative (vuot tran) | negative (G3) | — |
| Failure taxonomy | `test_501_ltt_voice_hong_hoc` | — | — | — |
| Idempotent resubmit | `test_375_ltt_voice_nop_lai_khong_trung` | — | — | — |
| Waveform (song am) | `test_902_voice_song_khong_ve_cho_khong` | — | — | (can tep tieng that dai) |
| A11y | `test_352_ltt_voice_tiep_can` | — | — | — |

## Tang browser — DA CHAY 2026-09-10

Chay tren `voice_e2e_server.py` (cach ly, cong 8129) + `voice_mock_sidecar.py`
(8131), qua `playwright-cli` (Chromium). Ket qua:

- **golden**: login → Studio (20 preset + 1 giong nhan ban seed hien du) → chon
  preset Adam → nhap text → Generate → **done, 3.5s, 1 credit** → trinh phat +
  tai WAV/MP3; tep tai la RIFF hop le; **0 loi console**, khong request that bai.
- **negative**: vuot tran (100.001) → nut Generate **tat** + canh bao "100.000";
  nam ranh gioi server (rong · vuot tran · vua-preset-vua-voice · preset bia ·
  CSRF sai) deu **400 + ok:false**.
- **smoke**: My voices / Projects / History deu render du lieu seed, **0 loi console**.

⭐ Ve "VI + EN mismatch": **hai truong hop khac nhau, KHONG con cung mot hanh vi**
tu Q121/D002 (`apps/ltt_voice/lan_ngon_ngu.py::quyet_dinh`):

- Van ban **mo ho** (tieng Viet khong dau, khong co dau hieu chac chan) — VAN
  cho tao, khong chan. Ly do khong doi: tieng Viet khong dau khong phan biet
  duoc voi tieng Anh bang bang ma, nen chan o day la tu choi mot viec hop le.
  Day la ca `ltt_voice_negative.js` chay.
- Van ban **doan CHAC** (du dau hieu — vi du du tieng Anh chuc nang, hoac co
  dau tieng Viet) ma lech lan voi giong dang chon — **CHAN**, tra
  `ma_loi=voice_language_mismatch` (D002/INV-LAN-1). Dung cho ca truong hop
  khach da khai lan: loi khai KHONG mien tru mot van ban ma may biet chac la
  lan kia. Luong nay chay o `tests/browser/ltt_voice_rc1.js` (LUONG 5): khai
  `vi` + giong `vi` (Adam) + van ban `en` chac -> 400, `voice_language_mismatch`.

Cac chan KHONG-lien-quan-ngon-ngu (vuot tran, van ban rong) van giu nguyen.

## Tang LIVE — CHUA CHAY trong luot nay

Xem `01_RELEASE_VERIFICATION.md`. Cong giong that (`LTTStudioVoice`, 127.0.0.1:8120)
**dang song** (do 10/09: tra 401 khi thieu token = dich vu chay). Nhung tang LIVE
cham **GPU + so credit that** nen no la ranh gioi cua nguoi dung, khong tu chay.
