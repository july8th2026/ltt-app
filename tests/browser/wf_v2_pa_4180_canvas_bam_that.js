// P-A (spec `docs/superpowers/plans/2026-09-25-wf-v2-VAN-HANH.md` §5) —
// CHUNG MINH BAM THAT tren Canvas that, khong doc source/curl roi tuyen bo
// GUI hoat dong (CLAUDE.md toan cuc, muc "Global browser testing policy").
//
// Ba nut + inspector phai TON TAI, BAM DUOC, va bam thi CO GOI MANG DI:
//   - "Chay lai tu day"   (RunV3Panel.tsx, workflowApi.chayLaiTuNodeV3)
//   - "So sanh voi luot goc" (CanvasShell.tsx, workflowApi.soSanhRunV3)
//   - "Soan bang AI"      (CanvasShell.tsx, workflowApi.soanWorkflowV3)
//   - RunInspector (input/output tho qua @uiw/react-json-view)
//
// KHONG chay tren cong 8100 (production that) — luon mot may chu thu rieng.
// Dang nhap KHONG go mat khau: chay `setup/ve_dang_nhap_thu.ps1` roi mo
// URL ve SSO truoc khi goi script nay bang `playwright-cli goto` (xem
// `tests/browser/wf_v2_pa_4180_run.ps1`). Script nay gia dinh trang da co
// phien dang nhap (cookie) va bat dau tu `page.goto(base + '/agent/canvas')`.
//
// ⭐ 25/09 (lan wfk): lo hong "Agent Designer ghi node core.* thieu
// `data.tool`, lam Canvas trang trong" DA VA (`platform_core/agent/
// ke_hoach_v3.py::chuan_hoa`/`_data_canvas`, `tests/test_4250_wf_v3_soan_
// data_tool_shape.py`) — buoc "Soan bang AI" o cuoi nay KHONG con loc rieng
// thong diep loi do nua, xem canh bao cuoi tep truoc day (da go).
async page => {
  const base = 'http://127.0.0.1:8199';
  const pageErrors = [], consoleErrors = [], failedRequests = [], serverErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text()); });
  page.on('requestfailed', request => failedRequests.push({url: request.url(), error: request.failure()?.errorText}));
  page.on('response', response => { if (response.status() >= 500) serverErrors.push({url: response.url(), status: response.status()}); });
  const check = (condition, message) => { if (!condition) throw new Error(message); };

  await page.goto(base + '/agent/canvas');
  check(page.url().startsWith(base + '/'), 'khong o may chu thu (co the ticket SSO da het han/da dung)');
  check(!page.url().includes('/login'), 'chua dang nhap — mo ticket SSO truoc khi chay script nay');
  const root = page.locator('#agent-canvas-root');
  await root.waitFor();
  const csrf = await root.getAttribute('data-csrf-token');
  check(!!csrf, 'thieu CSRF token tren #agent-canvas-root');

  // ── Buoc 0: ep workflow dau tien cua tai khoan ve mot trang RONG. Idempotent
  //    — moi lan chay lai script deu bat dau tu cung mot trang thai, du lan
  //    truoc da tao node/run/goal gi. ─────────────────────────────────────
  const resetWorkflow = async () => {
    const listRes = await page.evaluate(async () => {
      const r = await fetch('/agent/api/v3/workflows', {credentials: 'same-origin'});
      return r.json();
    });
    check(Array.isArray(listRes.items) && listRes.items.length > 0, 'tai khoan thu chua co workflow nao');
    const id = listRes.items[0].id;
    const before = await page.evaluate(async (wfId) => {
      const r = await fetch(`/agent/api/v3/workflows/${wfId}`, {credentials: 'same-origin'});
      return r.json();
    }, id);
    // ⚠️ Dung DUY NHAT mot trang co id co dinh 'page-1' va luon dat
    //    `active_page_id` khop no — `updateActive()` (editorState.ts) so
    //    KHOP TUYET DOI `page.id === document.active_page_id`, KHONG co loi
    //    lui nao ca (khac `activePage()` dung cho DOC, co `?? pages[0]`).
    //    Mot tai lieu thieu/lech `active_page_id` (vd tai lieu rong may chu
    //    tao — `drafts_v3.py::_tai_lieu_rong` — hoac mot ban ghi cu de lai)
    //    lam moi thao tac THEM/SUA node qua UI IM LANG khong lam gi ca,
    //    khong loi console, khong request hong — chi "Hoan tac" bat sang vi
    //    reducer van day lich su du update la no-op. Da tu tay va phai lo
    //    nay hai lan khi debug thu cong; ep co dinh o day de test KHONG con
    //    phu thuoc trang thai document truoc do.
    const first = before.document.pages[0] ?? {name: 'Page 1', viewport: {x: 0, y: 0, zoom: 1},
      frames: [], notes: [], comments: []};
    const emptied = {
      ...before.document,
      goal: '',
      active_page_id: 'page-1',
      pages: [{...first, id: 'page-1', nodes: [], edges: []}],
    };
    const putRes = await page.evaluate(async ({wfId, doc, rev, csrfToken}) => {
      const r = await fetch(`/agent/api/v3/workflows/${wfId}`, {
        method: 'PUT', credentials: 'same-origin',
        headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken, 'If-Match': `"${rev}"`},
        body: JSON.stringify({document: doc, csrf_token: csrfToken}),
      });
      return {status: r.status, body: await r.json()};
    }, {wfId: id, doc: emptied, rev: before.revision, csrfToken: csrf});
    check(putRes.status === 200, `khong reset duoc workflow: HTTP ${putRes.status}`);
    return id;
  };

  const workflowId = await resetWorkflow();
  // Palette chi tai MOT LAN luc mount (`Promise.all([taiPalette(), ...])`,
  // CanvasShell.tsx) — doi phan hoi cua no O DAY, khong doi sau khi bam "Mo
  // cong cu" (do chi doi trang thai/CSS, khong fetch lai — doi sau click se
  // cho mai mot response da xay ra TRUOC do va khong bao gio toi).
  const paletteLoaded = page.waitForResponse(r => r.url().endsWith('/agent/api/v3/palette') && r.request().method() === 'GET');
  await page.reload();
  await root.waitFor();
  await paletteLoaded;
  check((await page.locator('.canvas-stage').getAttribute('data-edge-count')) === '0', 'workflow chua ve trang sau reset');

  // ── Them mot node that qua palette (bam, KHONG keo-tha — spec §13.3: cua
  //    duy nhat cua no la onClick={()=>themNode(nd)}, xem PaletteV2.tsx). ──
  await page.getByRole('button', {name: 'Mở công cụ'}).click();
  const addBtn = page.locator('button').filter({hasText: 'app.text.chat@1'}).first();
  await addBtn.waitFor();
  await addBtn.click();
  // `click()` tra ve khi su kien DOM da phat, KHONG doi React commit lai —
  // doi bang waitForFunction (co poll) thay vi doc DOM mot lan ngay sau do,
  // neu khong phep kiem tu no flaky theo do tre render (da thay that).
  await page.waitForFunction(() => /1 node/.test(document.body.innerText));
  check((await page.locator('.canvas-stage').getAttribute('data-edge-count')) === '0', 'chua co canh nao (dung, 1 node don le)');

  await page.getByRole('textbox', {name: /messages/}).fill('[{"role":"user","content":"Tra loi dung mot chu: OK"}]');
  const runNutHeader = page.getByRole('button', {name: 'Chạy', exact: true});
  check(await runNutHeader.isEnabled(), 'nut "Chay" (mo khay chay) van khoa sau khi dien tham so bat buoc');
  await runNutHeader.click();

  // ── "Chay ngay": save -> publish -> tao run that (createRunV3). ─────────
  const runCreated = page.waitForResponse(r => /\/agent\/api\/v3\/workflows\/.+\/runs$/.test(r.url()) && r.request().method() === 'POST');
  await page.getByRole('button', {name: 'Chạy ngay'}).click();
  const runRes = await runCreated;
  check(runRes.status() === 201, `POST .../runs khong tao duoc run: HTTP ${runRes.status()}`);

  const choDenKhiXong = async (timeoutMs = 60000) => page.waitForFunction(
    () => {
      const el = document.querySelector('.run-v3 strong[data-run-status]');
      const trangThai = el?.getAttribute('data-run-status');
      return trangThai && ['SUCCEEDED', 'FAILED', 'CANCELLED', 'ABANDONED'].includes(trangThai);
    }, {timeout: timeoutMs});
  await choDenKhiXong();

  // ── Task A5 — Inspector: input/output tho phai HIEN duoc thuc su. ───────
  const inspector = page.locator('.run-v3-inspector');
  check(await inspector.isVisible(), 'RunInspector khong hien — Task A5 chua noi day');
  check((await inspector.innerText()).includes('nodes'), 'RunInspector khong co du lieu node cua run that');

  // ── Task A1 — "Chay lai tu day": bam that tren MOT hang node cua bang. ──
  const chayLaiBtn = page.getByRole('button', {name: 'Chạy lại từ đây'});
  check(await chayLaiBtn.isVisible(), 'nut "Chay lai tu day" khong xuat hien du run da xong');
  const chayLaiCall = page.waitForResponse(r => /\/agent\/api\/v3\/runs\/.+\/chay-lai-tu\/.+/.test(r.url()) && r.request().method() === 'POST');
  await chayLaiBtn.click();
  const chayLaiRes = await chayLaiCall;
  check(chayLaiRes.status() === 201, `POST .../chay-lai-tu khong tao duoc run: HTTP ${chayLaiRes.status()}`);
  await choDenKhiXong();

  // ── Task A2 — "So sanh voi luot goc": bam that, doc diff that. ──────────
  const soSanhBtn = page.getByRole('button', {name: 'So sánh với lượt gốc'});
  check(await soSanhBtn.isVisible(), 'nut "So sanh voi luot goc" khong xuat hien sau chay lai');
  const soSanhCall = page.waitForResponse(r => /\/agent\/api\/v3\/runs\/.+\/so-sanh\?voi=.+/.test(r.url()) && r.request().method() === 'GET');
  await soSanhBtn.click();
  const soSanhRes = await soSanhCall;
  check(soSanhRes.status() === 200, `GET .../so-sanh khong tra duoc diff: HTTP ${soSanhRes.status()}`);
  const diff = page.locator('.run-diff');
  check(await diff.isVisible(), 'RunDiff khong hien sau khi so sanh');

  // ── Task A3 — "Soan bang AI": chi doi hoi bam duoc + goi mang that. ─────
  //    (xem canh bao o dau tep ve lo hong da biet ngoai pham vi lan nay)
  await page.getByRole('button', {name: 'Mở mẫu và thiết lập'}).click();
  await page.getByRole('textbox', {name: 'Mục tiêu workflow'})
    .fill('Sinh mot cau tra loi ngan bang model chat noi bo, khong dung node du lieu rieng.');
  const soanBtn = page.getByRole('button', {name: 'Soạn bằng AI'});
  check(await soanBtn.isEnabled(), 'nut "Soan bang AI" khoa du da co muc tieu');
  const soanCall = page.waitForResponse(r => /\/agent\/api\/v3\/workflows\/.+\/soan$/.test(r.url()) && r.request().method() === 'POST',
    {timeout: 45000});
  await soanBtn.click();
  const soanRes = await soanCall;
  // Cai can chung minh la NUT GOI DUOC MANG, khong phai AI luon soan ra mot
  // do thi hop le (phu thuoc LLM, khong tat dinh) — 200 (soan xong, co the
  // hop_le:false kem loi) va 422 (draft khong bien dich duoc, `agent_v3.py`
  // tra ve loi co cau truc) deu la SERVER DA XU LY YEU CAU that. Chi 5xx/mat
  // ket noi moi la nut/day khong hoat dong.
  check([200, 422].includes(soanRes.status()), `POST .../soan: HTTP bat thuong ${soanRes.status()}`);
  await resetWorkflow(); // don sach cho lan chay ke tiep, bat ke /soan sinh ra gi

  // ⭐ 25/09 (lan wfk): KHONG con loc rieng "Cannot read properties of
  // undefined (reading 'tool')" — lo hong `data.tool` thieu sau /soan da va
  // (xem canh bao dau tep). Moi loi JavaScript sau buoc "Soan bang AI" gio
  // la mot regression THAT.
  check(pageErrors.length === 0, 'loi JavaScript ngoai y muon: ' + pageErrors.join('; '));
  // `/su-kien` (theo doi run qua SSE, workflowApi.ts::theoDoiRunV3) la mot
  // ket noi song lau; ERR_ABORTED khi test chu dong doi trang (reload de
  // reset, hoac chuyen sang run khac) la HE QUA MONG DOI cua dieu huong,
  // khong phai mot request that su hong.
  const failedRequestsThat = failedRequests.filter(f =>
    !(f.url.includes('/su-kien') && f.error === 'net::ERR_ABORTED'));
  check(failedRequestsThat.length === 0, 'request that bai ngoai y muon: ' + JSON.stringify(failedRequestsThat));
  check(serverErrors.length === 0, 'may chu tra loi 5xx ngoai y muon: ' + JSON.stringify(serverErrors));
  return {status: 'PASS', workflowId, note: 'ca ba nut + inspector bam that, co goi mang, may chu thu cong 8199 (khong dung 8100)'};
}
