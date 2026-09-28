// Luu tru 6 workflow RAC do chinh phep do cua toi tao ra (28/09/2026).
//
// ## ⛔ Vi sao LUU TRU chu khong XOA
//
// Kho ⛔ KHONG co cua `DELETE` cho workflow, va do la mot QUYET DINH co ghi ly
// do (`apps/agent/routes/drafts_v3.py:166`):
//
//   "Day KHONG phai xoa... Ban ghi, ban nhap va moi `workflow_version` o lai
//    nguyen ven; `/mo-lai` dua tat ca tro lai."
//
// ⇒ Mot cu xoa cung se phai la ta tu tay `DELETE` hang trong CSDL production,
//   di quanh chinh co che san pham. ⛔ Khong lam.
//
// ⭐ `/luu-tru` LUY DANG: bam lan hai ⛔ KHONG lam moc troi. Nen kich ban nay
//    chay lai duoc, va mot id da luu tru tu truoc ⛔ khong thanh loi.
//
//   python tools\chay_web_that.py tests\browser\agent_luu_tru_workflow_rac.js --phien luutru
async page => {
  const COOKIE = '__LTT_COOKIE__';
  if (!COOKIE || COOKIE.startsWith('__LTT_'))
    throw new Error('chua dien cookie - chay qua `python tools/chay_web_that.py`');

  const GOC = 'https://app.lttstudios.com';
  // Sau tien to id do CHINH cac phep do cua toi sinh ra trong phien 28/09.
  const TIEN_TO = ['fe0ca55e', '9bfb7148', '7777f173', '4671af58', '6a687639',
                   'abfc2396'];
  const so = {};
  const loi = [];

  await page.context().addCookies([{
    name: 'session', value: COOKIE, domain: 'app.lttstudios.com',
    path: '/', httpOnly: true, secure: true, sameSite: 'Lax',
  }]);
  await page.goto(GOC + '/agent/workflows', { waitUntil: 'domcontentloaded',
                                              timeout: 60000 });
  const csrf = await page.evaluate(() => {
    const m = document.querySelector('meta[name="csrf-token"]');
    if (m) return m.getAttribute('content') || '';
    const i = document.querySelector('input[name="csrf_token"]');
    return i ? i.value : '';
  });
  if (!csrf) { loi.push('khong lay duoc CSRF'); return { status: 'FAIL', loi, so } }

  const goi = async (duong, body, phuong = 'POST') => {
    const r = await page.request.fetch(GOC + duong, {
      method: phuong,
      headers: { 'content-type': 'application/json', 'x-csrf-token': csrf },
      data: body === undefined ? undefined : { ...body, csrf_token: csrf },
    });
    let than = null;
    try { than = await r.json() } catch { than = await r.text() }
    return { status: r.status(), than };
  };

  // ⭐ Lay id DAY DU tu danh sach that thay vi ghep tu tien to: `/luu-tru` nhan
  //    mot `workflow_id` du, va mot tien to 8 ky tu ⛔ khong phai mot id.
  const ds = await goi('/agent/api/v3/workflows', undefined, 'GET');
  so.danh_sach = ds.status;
  const tatCa = (ds.than?.items || ds.than?.workflows || ds.than || []);
  const hang = Array.isArray(tatCa) ? tatCa : (tatCa.items || []);
  so.tong_dang_mo = hang.length;

  const canLuu = hang.filter(w => TIEN_TO.some(t => String(w.id).startsWith(t)));
  so.khop = canLuu.map(w => `${String(w.id).slice(0, 8)}:${w.ten || w.name || '?'}`);

  // 🔴 Doi chieu SO: neu khop < so tien to thi mot so id KHONG con trong danh
  //    sach dang mo — hoac da luu tru, hoac khong ton tai. Hai thu KHAC NHAU,
  //    va im lang o day se thanh "da don xong" trong bao cao.
  const thieu = TIEN_TO.filter(t => !hang.some(w => String(w.id).startsWith(t)));
  so.khong_thay_trong_danh_sach_dang_mo = thieu;

  so.da_luu_tru = [];
  for (const w of canLuu) {
    const r = await goi(`/agent/api/v3/workflows/${w.id}/luu-tru`, {});
    if (r.status === 200) so.da_luu_tru.push(String(w.id).slice(0, 8));
    else loi.push(`luu-tru ${String(w.id).slice(0, 8)} -> ${r.status} `
                  + JSON.stringify(r.than).slice(0, 150));
  }

  // Doi chung: dem lai danh sach dang mo sau khi luu tru.
  const sau = await goi('/agent/api/v3/workflows', undefined, 'GET');
  const hangSau = (() => { const x = sau.than?.items || sau.than || [];
                           return Array.isArray(x) ? x : (x.items || []) })();
  so.tong_dang_mo_sau = hangSau.length;
  so.con_sot = hangSau.filter(w => TIEN_TO.some(t => String(w.id).startsWith(t)))
                      .map(w => String(w.id).slice(0, 8));
  if (so.con_sot.length)
    loi.push(`con ${so.con_sot.length} workflow RAC trong danh sach dang mo `
             + `sau khi luu tru: ${so.con_sot.join(',')}`);

  return { status: loi.length ? 'FAIL' : 'PASS', loi, so };
}
