// ltt_voice_smoke.js — smoke bon man con lai cua LTT Voice: My voices, Projects,
// History. Moi man phai render dung va KHONG co loi console.
//
//   playwright-cli run-code --filename=tests/browser/ltt_voice_smoke.js
//
// ⛔ Dung tren du lieu CO SAN (voice_e2e_server.py seed mot giong + mot du an):
//    so mot trang RONG voi mot anh mau CO du lieu thi moi khac biet doc len nhu
//    mot loi bo cuc (bay §27 / studio_dev.py). Nen smoke nay khang dinh du lieu
//    seed HIEN RA, khong chi "trang tra 200".
async page => {
  const BASE = 'http://127.0.0.1:8129';   // may chu E2E CACH LY (voice_e2e_server.py)

  const loiConsole = [];
  page.on('console', m => { if (m.type() === 'error') loiConsole.push(m.text()); });
  page.on('pageerror', e => loiConsole.push('pageerror: ' + e.message));

  // My voices: dang nhap NEU CAN, roi mo man.
  await page.goto(BASE + '/ltt-voice/giong');
  if (/\/login/.test(page.url())) {
    await page.getByRole('textbox', { name: 'Username' }).fill('voice-e2e@test.local');
    await page.getByRole('textbox', { name: 'Password' }).fill('khong-phai-mat-khau-that-12');
    await page.getByRole('button', { name: 'Sign in' }).click();
    await page.waitForLoadState('networkidle');
    await page.goto(BASE + '/ltt-voice/giong');
  }
  // giong da nhan ban seed phai hien.
  if (!(await page.getByText('Giong E2E - Natural VI').first().isVisible()))
    throw new Error('My voices: khong thay giong da seed "Giong E2E - Natural VI"');

  // Projects: du an seed phai hien.
  await page.goto(BASE + '/ltt-voice/du-an');
  if (!(await page.getByText('Kich ban E2E').first().isVisible()))
    throw new Error('Projects: khong thay du an da seed "Kich ban E2E"');

  // History: man phai dung (tieu de), khong nem.
  await page.goto(BASE + '/ltt-voice/lich-su');
  await page.waitForLoadState('networkidle');

  if (loiConsole.length)
    throw new Error('co ' + loiConsole.length + ' loi console qua 3 man: '
      + loiConsole.join(' | '));

  console.log('SMOKE OK — My voices, Projects, History; 0 loi console');
}
