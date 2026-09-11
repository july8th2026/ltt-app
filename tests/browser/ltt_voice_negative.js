// ltt_voice_negative.js — cac RANH GIOI cua LTT Voice trong trinh duyet.
//
//   playwright-cli run-code --filename=tests/browser/ltt_voice_negative.js
//
// ⭐ VE "VI + EN mismatch": san pham CANH BAO, KHONG chan (co chu y — xem
//    apps/ltt_voice/lan_ngon_ngu.py: tieng Viet khong dau khong phan biet duoc
//    voi tieng Anh bang bang ma, nen mot cong CHAN se tu choi viec hop le).
//    Nen o day "xu ly dung" nghia la: van tao duoc, chi hien mot loi nhac.
//
//    Cac chan CUNG that su trong san pham la: vuot tran ky tu, va van ban rong.
//    Hai cai do duoc khang dinh o day.
async page => {
  const BASE = 'http://127.0.0.1:8129';   // may chu E2E CACH LY (voice_e2e_server.py)

  await page.goto(BASE + '/ltt-voice');
  if (/\/login/.test(page.url())) {
    await page.getByRole('textbox', { name: 'Username' }).fill('voice-e2e@test.local');
    await page.getByRole('textbox', { name: 'Password' }).fill('khong-phai-mat-khau-that-12');
    await page.getByRole('button', { name: 'Sign in' }).click();
    await page.waitForLoadState('networkidle');
    await page.goto(BASE + '/ltt-voice');
  }

  const script = page.getByRole('textbox', { name: 'Script' });
  const nut = page.getByRole('button', { name: 'Generate speech' });

  const csrf = await page.getAttribute('#lv-form input[name="csrf_token"]', 'value');
  if (!csrf) throw new Error('khong lay duoc csrf tu form Studio');
  const tao = (form) => page.request.post(BASE + '/ltt-voice/tao',
    { form: Object.assign({ csrf_token: csrf }, form) });

  // 1. VUOT TRAN (100.001 > 100.000) — CHAN o CLIENT: nut tat + co canh bao.
  //    (Do that 10/09: nut Generate `disabled`, va dong dem hien "100.000".)
  await script.fill('a'.repeat(100001));
  await page.waitForTimeout(300);
  if (await nut.isEnabled())
    throw new Error('vuot tran ma nut Generate VAN bat — cua client mo');
  if (!(await page.getByText(/100\.00|vượt|thừa/i).first().isVisible().catch(() => false)))
    throw new Error('vuot tran ma KHONG co dong bao nao cho khach');

  // 2. Cac RANH GIOI o SERVER (Public API di thang xuong day, khong qua client):
  //    moi ca phai 400 + ok:false.
  const cas = [
    ['rong',                 { text: '   ', preset: 'Adam' },       /văn bản/],
    ['vuot-tran',            { text: 'a'.repeat(100001), preset: 'Adam' }, /vượt giới hạn/],
    ['vua-preset-vua-voice', { text: 'hi', preset: 'Adam', voice_id: 'vce_e2e_natural_vi' }, /Chỉ chọn một/],
    ['preset-bia',           { text: 'hi', preset: 'KHONG-CO-THAT' }, /dựng sẵn/],
    ['csrf-sai',             { text: 'hi', preset: 'Adam', csrf_token: '__SAI__' }, /hết hạn/],
  ];
  for (const [nhan, form, mong] of cas) {
    const r = await tao(form);
    if (r.status() !== 400)
      throw new Error(`negative[${nhan}]: mong 400, nhan ${r.status()} — CUA MO`);
    const body = await r.text();
    if (!/"ok"\s*:\s*false/.test(body) || !mong.test(body))
      throw new Error(`negative[${nhan}]: body khong dung: ${body.slice(0, 100)}`);
  }

  console.log('NEGATIVE OK — vuot tran chan o client; 5 ranh gioi server deu 400');
}
