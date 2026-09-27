// UI-8a — Human approval. Kiem lop TRINH BAY tren LAYOUT THAT. Hop thu vite
// dev, cong 8206 (cong RIENG cua lan nay).
//
// ## Vi sao hop thu run GIA, ⛔ khong phai mot lan chay THAT qua worker
//
// Ly do GIONG HET UI-7 (doc `agent_ui_v2_ui7_nghiem_thu.js`): mot run that di
// qua `danh_thuc_dong_co` -> mot JOB hang doi -> can mot WORKER RIENG
// (`worker_main.py`, chay duoi mot tien trinh khac) de tien no toi `WAITING`.
// May chu co lap dung cho kiem GUI (`agent_ui_v2_ui0_may_chu.py`) KHONG khoi
// dong worker do — day la CHU DICH cua ho so ngu ay (kiem GUI, khong kiem
// dong co). Bo ho so cua lan nay (dau phien) da noi ro: cua HTTP thi do bang
// `TestClient` (`tests/test_6500_phe_duyet_v3.py`, 9 bai, da tiem loi do
// duoc), con lop TRINH BAY thi dung run GIA (`tests/runGia.ts`, DUNG LAI —
// khong dung lai `runDuHinhDang()` moi tao them mot ban sao).
//
// ⇒ Kich ban nay mo dung `ExecutionPanel` that (khong phai mot ban chep boi
//   tay) tren mot trang duoc trinh duyet THAT tinh layout, voi `n-video`
//   (WAITING + waiting_kind='HUMAN', co san trong `runDuHinhDang()`) la buoc
//   duoc do.
//
// ## Chay
//
//   cd frontend/agent-canvas && npx vite --port 8206 --strictPort --host 127.0.0.1
//   playwright-cli -s=ui8a run-code --filename=tests/browser/agent_ui_v2_ui8a_nghiem_thu.js
//
// ⚠️ Cong 8206 la cong RIENG cua lan UI-8a (giao dau phien). ⛔ KHONG 8100,
//    ⛔ khong 8196/8201-8205/8207 (cong cua lan khac).
async page => {
  const GOC = 'http://127.0.0.1:8206/static/agent-canvas/tests/harness/run-gia.html';
  const loi = [], soLieu = {};
  const check = (dk, m) => { if (!dk) loi.push(m); };

  const pageErrors = [], consoleErrors = [], failedRequests = [];
  page.on('pageerror', e => pageErrors.push(String(e.message)));
  page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  page.on('requestfailed', r => failedRequests.push({url: r.url(), err: r.failure()?.errorText}));

  await page.setViewportSize({width: 1440, height: 900});
  await page.goto(GOC + '?run=1');
  await page.locator('.run-timeline').waitFor({timeout: 15000});

  // ── 0. Đối chứng môi trường (cùng bài học UI-7: đọc thứ ĐẠI DIỆN) ────────
  soLieu.moiTruong = await page.evaluate(() => {
    const ngan = document.querySelector('.operation-drawer');
    return {nganRong: ngan ? ngan.clientWidth : 0,
           luoi: ngan ? getComputedStyle(ngan).display : ''};
  });
  check(soLieu.moiTruong.luoi === 'grid',
    '🔴 ngan keo khong phai `display:grid` — `canvas.css` chua duoc nap');

  // ── 1. Thẻ duyệt cho `n-video` (WAITING + HUMAN) CÓ mặt, TRÊN dòng thời gian ─
  await page.locator('[data-duyet-node="n-video"]').waitFor({timeout: 5000});
  soLieu.the = await page.evaluate(() => {
    const the = document.querySelector('[data-duyet-node="n-video"]');
    const timeline = document.querySelector('.run-timeline');
    const nutDuyet = the.querySelector('[data-duyet-hanh-dong="approve"]');
    const nutTuChoi = the.querySelector('[data-duyet-hanh-dong="reject"]');
    const a = the.getBoundingClientRect(), b = timeline ? timeline.getBoundingClientRect() : null;
    return {
      coHan: !!the.querySelector('[data-duyet-het-han]'),
      hanNoiGi: the.querySelector('[data-duyet-het-han]')?.textContent ?? '',
      nutDuyetText: nutDuyet?.textContent ?? '',
      nutTuChoiText: nutTuChoi?.textContent ?? '',
      // ⭐ "TRÊN dòng thời gian" là quyết định layout của `index.tsx` — đo
      //    bằng TOẠ ĐỘ THẬT, không suy từ thứ tự trong mã nguồn.
      truocTimeline: b ? a.bottom <= b.top + 1 : null,
      tranNgang: the.scrollWidth > the.parentElement.clientWidth + 1,
      hien: a.width > 0 && a.height > 0,
    };
  });
  check(soLieu.the.hien, 'the duyet khong hien tren man hinh');
  check(soLieu.the.coHan, 'the duyet thieu dong "Het han cho: ..."');
  check(soLieu.the.hanNoiGi.includes('TỪ CHỐI'),
    `mac dinh het_han phai la reject: ${JSON.stringify(soLieu.the.hanNoiGi)}`);
  check(soLieu.the.nutDuyetText === 'Duyệt', `nut Duyet sai chu: ${soLieu.the.nutDuyetText}`);
  check(soLieu.the.nutTuChoiText === 'Từ chối', `nut Tu choi sai chu: ${soLieu.the.nutTuChoiText}`);
  check(soLieu.the.truocTimeline === true, '🔴 the duyet KHONG nam TREN dong thoi gian');
  check(!soLieu.the.tranNgang, 'the duyet TRAN ngang khoi ngan keo');

  // ── 2. Bấm "Duyệt" trong TRÌNH DUYỆT THẬT: gọi đúng cửa, khoá nút, rồi báo lỗi
  //      gọn (không backend ở hộp thư ⇒ fetch thất bại là CA THẬT cần chống).
  const requests = [];
  page.on('request', r => { if (r.url().includes('/duyet')) requests.push({url: r.url(), method: r.method()}); });
  await page.getByRole('button', {name: 'Duyệt'}).click();
  // Khoá nút NGAY — kể cả khi request đã xong trước khi ta kịp đọc DOM, đây là
  // một cuộc đua vô hại (⛔ không phải flake): hoặc ta bắt được lúc khoá, hoặc
  // ta bắt được lúc đã báo lỗi — cả hai đều là bằng chứng hợp lệ cho luồng
  // "bấm rồi có phản hồi", nên bài dưới hỏi CẢ HAI khả năng.
  const [khiKhoaHoacLoi] = await Promise.all([
    Promise.race([
      page.getByRole('button', {name: 'Đang gửi…'}).waitFor({timeout: 2000}).then(() => 'khoa'),
      page.locator('.run-error[role="alert"]').waitFor({timeout: 4000}).then(() => 'loi'),
    ]).catch(() => 'khong_thay'),
  ]);
  soLieu.sauKhiBam = {trangThaiDauTien: khiKhoaHoacLoi};
  check(khiKhoaHoacLoi !== 'khong_thay',
    'bam "Duyet" khong lam gi quan sat duoc (khong khoa nut, khong bao loi)');

  await page.locator('.run-error[role="alert"]').waitFor({timeout: 5000});
  soLieu.sauLoi = await page.evaluate(() => {
    const nutDuyet = document.querySelector('[data-duyet-node="n-video"] [data-duyet-hanh-dong="approve"]');
    return {
      coLoi: !!document.querySelector('[data-duyet-node="n-video"] .run-error'),
      nutMoLaiKhoa: nutDuyet ? !nutDuyet.disabled : null,
    };
  });
  check(soLieu.sauLoi.coLoi, 'khong hien thong bao loi sau khi fetch that bai');
  check(soLieu.sauLoi.nutMoLaiKhoa === true,
    'nut "Duyet" van bi khoa sau khi da bao loi — nguoi dung khong thu lai duoc');
  check(requests.length === 1,
    `phai co DUNG MOT request /duyet, dem duoc ${requests.length}`);
  if (requests[0]) {
    check(requests[0].url.endsWith('/agent/api/v3/runs/r-gia/nodes/n-video/duyet'),
      `URL request sai: ${requests[0].url}`);
    check(requests[0].method === 'POST', `method sai: ${requests[0].method}`);
  }

  // ── 3. Khung hẹp (390px): thẻ duyệt KHÔNG tràn ────────────────────────────
  await page.goto(GOC + '?run=1');
  await page.locator('[data-duyet-node="n-video"]').waitFor({timeout: 15000});
  await page.setViewportSize({width: 390, height: 844});
  await page.waitForTimeout(300);
  soLieu.hep = await page.evaluate(() => ({
    tranTrang: document.documentElement.scrollWidth > window.innerWidth + 1,
    theTran: (() => {
      const the = document.querySelector('[data-duyet-node="n-video"]');
      return !!the && the.scrollWidth > the.parentElement.clientWidth + 1;
    })(),
  }));
  check(!soLieu.hep.tranTrang, 'khung 390px: trang TRAN ngang');
  check(!soLieu.hep.theTran, 'khung 390px: the duyet TRAN ngang');

  soLieu.pageErrors = pageErrors;
  soLieu.consoleErrors = consoleErrors;
  // ⚠️ `failedRequests` CHỦ Ý không chặn, và cùng lý do lọc bớt
  //    `consoleErrors`: request `/duyet` KHÔNG có backend ở hộp thử nên trả
  //    404 — trình duyệt tự log "Failed to load resource: … 404" cho MỌI
  //    resource non-2xx, đây là NHẬT KÝ MẠNG của Chrome, ⛔ không phải một
  //    `console.error()` do mã của TA gọi. Việc component không throw khi
  //    gặp đúng cái 404 này đã được đo riêng ở bước 2 (`.run-error` xuất
  //    hiện, nút mở khoá lại) — đó là phép kiểm ĐÚNG cho "không throw", không
  //    phải đếm dòng nhật ký mạng của trình duyệt.
  const consoleErrorsThatNgoaiMang = consoleErrors.filter(
    m => !/Failed to load resource/.test(m));
  check(pageErrors.length === 0, `pageerror: ${JSON.stringify(pageErrors)}`);
  check(consoleErrorsThatNgoaiMang.length === 0,
    `console error (ngoai nhat ky mang): ${JSON.stringify(consoleErrorsThatNgoaiMang)}`);
  soLieu.failedRequests = failedRequests;

  return loi.length ? {status: 'FAIL', loi, so_lieu: soLieu}
                    : {status: 'PASS', so_lieu: soLieu};
}
