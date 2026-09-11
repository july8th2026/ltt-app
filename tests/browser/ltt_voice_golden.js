// ltt_voice_golden.js — GOLDEN PATH cua LTT Voice trong trinh duyet that.
//
//   playwright-cli run-code --filename=tests/browser/ltt_voice_golden.js
//
// Doi may chu E2E CACH LY dang chay (mac dinh 127.0.0.1:8129), tuc:
//   python tools\voice_mock_sidecar.py --cong 8131 --token mock-token
//   python tools\voice_e2e_server.py   --cong 8129 --mock-cong 8131
//
// ⛔ SIMULATED INFERENCE: tieng do cong GIA LAP sinh. Day la tang CI, KHONG
//    thay cho LIVE. Xem tools/voice_e2e_check.py va docs/LTT_VOICE/QA/.
//
// Luong: login -> Studio -> chon preset -> nhap text -> Generate -> done ->
//        phat + tai. Nem (throw) neu bat ky buoc nao sai — `run-code` bao ĐO.
async page => {
  const BASE = 'http://127.0.0.1:8129';   // may chu E2E CACH LY (voice_e2e_server.py)

  // RAO chong-xanh-gia: thu loi console. 0 loi la mot phan cua phan quyet.
  const loiConsole = [];
  page.on('console', m => { if (m.type() === 'error') loiConsole.push(m.text()); });
  page.on('pageerror', e => loiConsole.push('pageerror: ' + e.message));

  // 1. Mo Studio; dang nhap NEU CAN (tai khoan E2E dung mot lan, khong o mat
  //    khau that nao). Robust ca khi phien da dang nhap san.
  await page.goto(BASE + '/ltt-voice');
  if (/\/login/.test(page.url())) {
    await page.getByRole('textbox', { name: 'Username' }).fill('voice-e2e@test.local');
    await page.getByRole('textbox', { name: 'Password' }).fill('khong-phai-mat-khau-that-12');
    await page.getByRole('button', { name: 'Sign in' }).click();
    await page.waitForLoadState('networkidle');
    await page.goto(BASE + '/ltt-voice');
  }
  if (!(await page.getByRole('heading', { name: 'Generate speech' }).isVisible()))
    throw new Error('Studio khong render tieu de "Generate speech"');

  // 3. Chon giong dung san (preset Adam) + nhap kich ban.
  await page.getByRole('radio', { name: /Adam/ }).first().check();
  await page.getByRole('textbox', { name: 'Script' })
    .fill('Đây là lượt kiểm golden path trong trình duyệt thật của LTT Voice.');

  // 4. Tao — va CHO ket qua done (nut tai WAV hien khi xong).
  await page.getByRole('button', { name: 'Generate speech' }).click();
  const taiWav = page.getByRole('link', { name: /Download WAV/i });
  await taiWav.waitFor({ state: 'visible', timeout: 45000 });

  // 5. RAO: link tai phai tro dung cua /audio/ cua app, khong lo khoa kho tho.
  const href = await taiWav.getAttribute('href');
  if (!href || !href.includes('/ltt-voice/audio/'))
    throw new Error('link tai khong di qua /ltt-voice/audio/: ' + href);

  // 6. RAO: WAV that su tai duoc va la RIFF hop le (khong phai 200 rong).
  const res = await page.request.get(BASE + href);
  if (![200, 206].includes(res.status()))
    throw new Error('tai WAV -> HTTP ' + res.status());
  const buf = await res.body();
  if (!(buf[0] === 0x52 && buf[1] === 0x49 && buf[2] === 0x46 && buf[3] === 0x46))
    throw new Error('tep tai ve KHONG phai WAV (thieu RIFF)');

  // 7. RAO chong-xanh-gia: khong duoc co loi console/page.
  if (loiConsole.length)
    throw new Error('co ' + loiConsole.length + ' loi console: ' + loiConsole.join(' | '));

  console.log('GOLDEN OK — done, WAV ' + buf.length + ' byte, 0 loi console');
}
