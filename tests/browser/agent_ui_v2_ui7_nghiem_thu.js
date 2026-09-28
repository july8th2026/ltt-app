// UI-7 — mat THUC THI V2 tren LAYOUT THAT. Hop thu vite dev, cong 8202.
//
// ## ⭐ VI SAO HOP THU RUN GIA, KHONG PHAI MOT LUOT CHAY THAT
//
// Hai du kien do duoc, cong don:
//
//   1. Worker nap ma tu `nssm get LTTStudioWorker AppDirectory` =
//      `C:\LTTPlatform\app` — ban DA DEPLOY. Mot job that do ban deploy,
//      ⛔ khong do nhanh nay.
//   2. Worker chay duoi `LocalSystem`, PATH khac han phien nguoi dung.
//
// ⇒ "Chay mot workflow that roi xem timeline" cho so THAT nhung tra loi cau
//   KHAC. Viec cua lan UI-7 la lop TRINH BAY, nen phep do dung la: bom mot
//   `RunV3` co hinh dang DA BIET vao dung cac component ay
//   (`tests/runGia.ts`) roi kiem giao dien ve gi — tren layout THAT, vi jsdom
//   ⛔ khong tinh layout: mot dong thoi gian tran, mot thanh tien trinh de len
//   chu, mot `<details>` khong bam duoc — ca ba deu XANH trong vitest.
//
// ## Chay
//
//   cd frontend/agent-canvas && npx vite --port 8202 --strictPort --host 127.0.0.1
//   playwright-cli -s=ui7 run-code --filename=tests/browser/agent_ui_v2_ui7_nghiem_thu.js
//
// ⚠️ Cong 8202 la cong CUA LAN UI-7 (so dung chung, dieu phoi cap 28/09).
//    ⛔ Dung ket luan "cong ranh" tu mot lan thu: mot cong DANG KHOI DONG LAI
//    tra y het mot cong TRONG, va ⛔ dung giet tien trinh tren cong minh khong
//    tu khoi dong.
async page => {
  // ⭐ Hop thu mount CHINH `ExecutionPanel`. `?run=1` la pha DANG CHAY; khong co
  //    no la pha TRUOC KHI CHAY (bao gia + nut "Chay ngay") — hai pha loai tru
  //    nhau trong chinh component, nen phai do o HAI lan tai.
  const GOC = 'http://127.0.0.1:8202/static/agent-canvas/tests/harness/run-gia.html';
  const loi = [], soLieu = {};
  const check = (dk, m) => { if (!dk) loi.push(m); };

  // Bon thu phai thu O MOI PHA (plan TONG §3b.2 buoc 3).
  const pageErrors = [], consoleErrors = [], failedRequests = [], serverErrors = [];
  page.on('pageerror',     e => pageErrors.push(String(e.message)));
  page.on('console',       m => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  page.on('requestfailed', r => failedRequests.push({url: r.url(), err: r.failure()?.errorText}));
  page.on('response',      r => { if (r.status() >= 500) serverErrors.push({url: r.url(), status: r.status()}); });

  // ⭐ Khung nhin TUONG MINH. Ngan keo chay la `min(390px, 100vw - 72px)`, nen
  //    mot khung nhin mac dinh khac nhau giua may lam ket qua khong so duoc.
  await page.setViewportSize({width: 1440, height: 900});
  await page.goto(GOC + '?run=1');
  await page.locator('.run-timeline').waitFor({timeout: 15000});

  // ── 0. DOI CHUNG: trang nay co THAT SU mang bo bien cua ung dung khong? ──
  //
  // 🔴 Khong co buoc nay, moi phep do ben duoi van PASS tren mot trang KHONG
  //    NAP `canvas.css`: React ve du phan tu, nhung ⛔ khong mot token nao ton
  //    tai, ngan keo ⛔ khong co be rong 390px that, va ket luan ve bo cuc la
  //    ket luan ve mot trang khong ai co. Da xay ra that 28/09 — mot ban nhap
  //    cua hop thu lam roi dong `import canvas.css` va ca kich ban nay bao PASS.
  // ⚠️ PHAM VI: do HINH HOC do `canvas.css` SO HUU, ⛔ khong do token mau.
  //    `--text-primary` & co. ⛔ KHONG nam trong `canvas.css` — no chi dinh
  //    nghia chung duoi `.canvas-shell.theme-light` (dong 126); o che do TOI
  //    (mac dinh san pham, Q66) chung den tu bang mau NEN TANG, ma bang ay do
  //    template cua may chu nap, ⛔ khong thuoc goi `agent-canvas`. Hoi mot
  //    token o day la hoi mot cau ma hop thu KHONG the tra loi.
  //    ⇒ Mau CHOT o che do B (web that, sau deploy). O day chot CAU TRUC va
  //      HINH HOC — va `run.css` co gia tri lui cho MOI token chinh vi vay.
  soLieu.moiTruong = await page.evaluate(() => {
    const ngan = document.querySelector('.operation-drawer');
    return {
      // `.canvas-toolbar > .operation-drawer.is-open` dat
      // `width: min(390px, 100vw - 72px)` + `padding: 12px` (content-box)
      // ⇒ `clientWidth` = 390 + 24 = 414 tren man rong.
      nganRong: ngan ? ngan.clientWidth : 0,
      luoi: ngan ? getComputedStyle(ngan).display : '',
      soStylesheet: document.styleSheets.length,
    };
  });
  check(soLieu.moiTruong.luoi === 'grid',
    '🔴 ngan keo khong phai `display:grid` — `canvas.css` chua duoc nap');
  check(soLieu.moiTruong.nganRong > 300 && soLieu.moiTruong.nganRong <= 420,
    `be rong ngan keo ${soLieu.moiTruong.nganRong}px — phai la min(390,100vw-72)+24`);

  // ── 1. Dong thoi gian: TEN BUOC, ⛔ khong `node_id` tho ──────────────────
  soLieu.timeline = await page.evaluate(() => {
    const hang = [...document.querySelectorAll('.run-timeline tbody tr')];
    return {
      soHang: hang.length,
      cotDau: hang.map(tr => (tr.querySelector('.run-timeline-ten')?.innerText ?? '').trim()),
      thoiLuong: hang.map(tr => (tr.querySelector('.run-timeline-thoi-luong')?.innerText ?? '').trim()),
      // Tran ngang: mot bang rong hon o chua no la loi layout that ma jsdom
      // khong the thay.
      tranNgang: (() => {
        const t = document.querySelector('.run-timeline');
        const ngan = document.querySelector('.operation-drawer');
        return !!t && !!ngan && t.scrollWidth > ngan.clientWidth + 1;
      })(),
      // ⭐ DO CHIEU CAO HANG — thuoc do DOC DUOC duy nhat co the tu dong hoa o
      //    day. Ngan keo 390px voi 6 cot: neu de trinh duyet tu chia, cot nao
      //    co chuoi dai nhat thang, va mot hang phinh len 6 DONG (do 28/09:
      //    "Đang chờ tín hiệu (chờ người duyệt)"). Mot hang cao qua ~3 dong
      //    nghia la bang da vo bo cuc, du ⛔ khong tran ngang.
      caoNhat: Math.round(Math.max(...hang.map(tr => tr.getBoundingClientRect().height))),
    };
  });
  check(soLieu.timeline.soHang === 5,
    `dong thoi gian phai co 5 hang, dem duoc ${soLieu.timeline.soHang}`);
  check(soLieu.timeline.cotDau.includes('Lấy dòng Sheet'),
    'cot dau khong hien ten buoc "Lấy dòng Sheet"');
  const thoNoiRa = soLieu.timeline.cotDau.filter(
    t => t.includes('nmujtmc1b-0') || t.includes('n-sheet') || t.includes('n-cho'));
  check(thoNoiRa.length === 0,
    '🔴 node_id THO con o cot dau: ' + JSON.stringify(thoNoiRa));
  check(soLieu.timeline.cotDau.some(t => t.includes('Bước 5')),
    'node khong co nhan phai lui ve "Bước N"');
  check(!soLieu.timeline.tranNgang,
    'dong thoi gian TRAN ngang khoi ngan keo — loi layout that');
  check(soLieu.timeline.caoNhat <= 60,
    `hang cao nhat ${soLieu.timeline.caoNhat}px (> 60 = da vo bo cuc, chu xuong qua nhieu dong)`);
  // Khong do duoc thi `—`, ⛔ khong `0s`.
  check(!soLieu.timeline.thoiLuong.some(t => t === '0s'),
    `cot thoi luong in "0s" cho buoc khong do duoc: ${JSON.stringify(soLieu.timeline.thoiLuong)}`);
  check(soLieu.timeline.thoiLuong.filter(t => t === '—').length >= 1,
    'khong buoc nao hien "—" — phep do nay khong con doi chung');

  // ── 2. Nhat ky: MOI dong co dau thoi gian ────────────────────────────────
  soLieu.nhatKy = await page.evaluate(() => {
    const li = [...document.querySelectorAll('.run-v3-su-kien > li')];
    return {
      soDong: li.length,
      thieuGio: li.filter(x => !x.querySelector('time')).map(x => x.innerText.trim()),
      coTenBuoc: li.some(x => x.innerText.includes('Tạo ảnh AI')),
      conNodeIdTho: li.filter(x => x.innerText.includes('nmujtmc1b-0')).length,
    };
  });
  check(soLieu.nhatKy.soDong === 7,
    `nhat ky phai co 7 dong, dem duoc ${soLieu.nhatKy.soDong}`);
  check(soLieu.nhatKy.thieuGio.length === 0,
    `🔴 dong nhat ky THIEU dau thoi gian: ${JSON.stringify(soLieu.nhatKy.thieuGio)}`);
  check(soLieu.nhatKy.coTenBuoc,
    'nhat ky khong hien TEN buoc cho su kien mang `node_id` trong `du_lieu`');
  check(soLieu.nhatKy.conNodeIdTho === 0,
    'nhat ky con in `node_id` tho');

  // ── 3. Bam mot buoc mo Inspector 12 truong CO NHOM ───────────────────────
  check(await page.locator('.run-node-inspector').count() === 0,
    'Inspector hien san khi chua bam buoc nao');
  await page.getByRole('button', {name: 'Tạo ảnh AI'}).click();
  await page.locator('.run-node-inspector').waitFor({timeout: 5000});
  soLieu.inspector = await page.evaluate(() => {
    const insp = document.querySelector('.run-node-inspector');
    const truong = [...insp.querySelectorAll('[data-truong]')];
    const hien = el => el.getBoundingClientRect().height > 0;
    return {
      soTruong: truong.length,
      slug: truong.map(el => el.getAttribute('data-truong')),
      // ⭐ "Co tren DOM" ⛔ khong bang "nguoi doc duoc": do CHIEU CAO thuc.
      truongBiAn: truong.filter(el => !hien(el)).map(el => el.getAttribute('data-truong')),
      soNhom: insp.querySelectorAll('.run-nhom').length,
      truongNgoaiNhom: truong.filter(el => !el.closest('.run-nhom'))
        .map(el => el.getAttribute('data-truong')),
      tenNhom: [...insp.querySelectorAll('.run-nhom')].map(g => g.getAttribute('aria-label')),
      nodeIdTrongKyThuat: (insp.querySelector('.run-ky-thuat')?.textContent ?? '')
        .includes('nmujtmc1b-0'),
      tranNgang: insp.scrollWidth > insp.clientWidth + 1,
    };
  });
  const CHO = ['trang_thai', 'dau_vao', 'dau_ra', 'nhat_ky', 'loi', 'lan_thu',
               'thoi_luong', 'chi_phi', 'tai_nguyen', 'ly_do_cho',
               'lich_su_thu_lai', 'artifact'];
  const thieu = CHO.filter(s => !soLieu.inspector.slug.includes(s));
  check(thieu.length === 0, `Inspector thieu truong §8: ${JSON.stringify(thieu)}`);
  check(soLieu.inspector.truongBiAn.length === 0,
    `truong co tren DOM nhung KHONG hien: ${JSON.stringify(soLieu.inspector.truongBiAn)}`);
  check(soLieu.inspector.soNhom >= 3,
    `Inspector chi co ${soLieu.inspector.soNhom} nhom — phai co it nhat 3`);
  check(soLieu.inspector.truongNgoaiNhom.length === 0,
    `truong nam NGOAI nhom: ${JSON.stringify(soLieu.inspector.truongNgoaiNhom)}`);
  check(soLieu.inspector.tenNhom.every(Boolean), 'co nhom KHONG co ten');
  check(soLieu.inspector.nodeIdTrongKyThuat,
    '`node_id` khong con o dau ca — no phai o "Chi tiet ky thuat"');
  check(!soLieu.inspector.tranNgang, 'Inspector TRAN ngang — loi layout that');

  // ── 4. Loi: cau nguoi doc duoc, ma may GAP LAI va BAM DUOC ───────────────
  await page.getByRole('button', {name: 'Đăng YouTube'}).click();
  await page.locator('.run-loi').waitFor({timeout: 5000});
  soLieu.loi = await page.evaluate(() => {
    const khoi = document.querySelector('.run-loi');
    const gap = khoi.querySelector('details');
    return {
      cau: khoi.querySelector('.run-loi-cau').innerText.trim(),
      gapDongSan: !gap.open,
      // ⭐ jsdom ⛔ khong the tra loi cau nay: chi tiet co THAT SU an khong.
      //
      // 🔴 DO `innerText` + HOP CUA `<details>`, ⛔ KHONG do rect cua PHAN TU
      //    BEN TRONG.
      //
      //    Ban dau bai nay do `code.getBoundingClientRect().height` roi
      //    `p...height` va bao FAIL voi 12px, trong khi giao dien HOAN TOAN
      //    dung. Do duoc 28/09 tren Chromium, cung mot trang, cung luc:
      //
      //        details.getBoundingClientRect().height   = 10  (= summary)
      //        details.innerText                        = "Chi tiết kỹ thuật"
      //        p.getBoundingClientRect().height         = 12  ← va doi khi 0
      //        code.getBoundingClientRect().height      = 12
      //
      //    Con 12px ay ⛔ KHONG dong gop mot pixel nao vao hop cua `<details>`:
      //    trong cay `content-visibility: hidden`, mot phan tu con van tra ve
      //    kich thuoc bo tri noi tai cua no, va tra 0 hay 12 con tuy vao cay ay
      //    tung duoc bo tri chua — tuc no doi theo thao tac TRUOC do trong cung
      //    kich ban. Mot tin hieu doi theo lich su thao tac ⛔ khong tra loi
      //    duoc cau "nguoi dung co doc thay khong".
      //
      //    ⇒ Da BO phep do ay chu ⛔ khong noi nguong: no lech CHIEU, khong
      //      lech DO LON. Hai tin hieu duoi day tra loi dung cau can hoi:
      //      `innerText` la dinh nghia "van ban RENDER ra" cua trinh duyet, va
      //      `details` cao bang dung `summary` nghia la phan gap ⛔ khong chiem
      //      mot cho nao.
      chiTietTrongInnerText: gap.innerText.includes('credential_loi'),
      gapCaoKhiDong: gap.getBoundingClientRect().height,
      summaryCao: gap.querySelector('summary').getBoundingClientRect().height,
    };
  });
  check(!soLieu.loi.cau.includes('credential_loi') && !soLieu.loi.cau.includes('_'),
    `cau loi con mang ma may: ${soLieu.loi.cau}`);
  check(soLieu.loi.cau.length > 20, `cau loi qua ngan: ${soLieu.loi.cau}`);
  check(soLieu.loi.gapDongSan, '<details> ma may KHONG gap san');
  check(!soLieu.loi.chiTietTrongInnerText,
    'ma may DOC DUOC khi <details> dang dong — cai gap khong lam gi');
  check(soLieu.loi.gapCaoKhiDong <= soLieu.loi.summaryCao + 1,
    `<details> dong cao ${soLieu.loi.gapCaoKhiDong}px > summary ${soLieu.loi.summaryCao}px`);
  // Bam mo: chi tiet phai hien ra THAT.
  await page.locator('.run-loi details > summary').click();
  soLieu.loi.sauKhiMo = await page.evaluate(() => {
    const gap = document.querySelector('.run-loi details');
    return {
      moRa: gap.open,
      coMa: gap.innerText.includes('credential_loi'),
      coChiTiet: gap.innerText.includes('thieu access_token'),
      cao: gap.getBoundingClientRect().height,
    };
  });
  check(soLieu.loi.sauKhiMo.moRa && soLieu.loi.sauKhiMo.coMa
        && soLieu.loi.sauKhiMo.coChiTiet && soLieu.loi.sauKhiMo.cao > 0,
    `bam mo "Chi tiet ky thuat" khong hien ma may: ${JSON.stringify(soLieu.loi.sauKhiMo)}`);

  // ── 5. Bao gia hien TRUOC nut "Chay ngay", va la mot CON SO ──────────────
  //
  // ⭐ Pha TRUOC KHI CHAY: tai lai KHONG co `?run=1`. `ExecutionPanel` an bao
  //    gia + nut "Chay ngay" ngay khi co mot luot chay, nen do hai thu ay tren
  //    trang dang-chay se do mot man hinh KHONG ton tai.
  await page.goto(GOC);
  await page.locator('.run-bao-gia').waitFor({timeout: 15000});
  soLieu.baoGia = await page.evaluate(() => {
    const khoi = document.querySelector('.run-bao-gia');
    const nut = document.querySelector('.run-confirm');
    if (!khoi || !nut) return {thieu: true};
    const a = khoi.getBoundingClientRect(), b = nut.getBoundingClientRect();
    return {
      thieu: false,
      so: khoi.querySelector('strong').innerText.trim(),
      tong: khoi.querySelector('strong').getAttribute('data-bao-gia-tong'),
      // ⭐ TREN nut, do bang TOA DO THAT — thu tu trong DOM ⛔ khong bao dam
      //    thu tu tren man hinh khi container la mot luoi CSS.
      truocNut: a.bottom <= b.top + 1,
      caKhoiHien: a.height > 0 && a.width > 0,
    };
  });
  check(!soLieu.baoGia.thieu, 'khong tim thay khoi bao gia hoac nut "Chay ngay"');
  check(soLieu.baoGia.caKhoiHien, 'khoi bao gia khong hien');
  check(soLieu.baoGia.truocNut,
    '🔴 bao gia KHONG nam TREN nut "Chay ngay" tren man hinh');
  check(/^\d+ credit$/.test(soLieu.baoGia.so ?? ''),
    `bao gia phai la mot CON SO, doc duoc: ${JSON.stringify(soLieu.baoGia.so)}`);
  check(soLieu.baoGia.tong === '12',
    `tong bao gia sai: ${soLieu.baoGia.tong} (0+3+8+1+0 = 12)`);

  // ── 6. Ngan keo "Chay" ⛔ khong con 7 nut xem/sua ────────────────────────
  soLieu.nutLa = await page.evaluate(() => {
    const XEM_SUA = ['Nhân bản', 'Xóa', 'Tự xếp', 'Lớp', 'Lưới', 'Đường nối', 'Bản đồ'];
    const ngan = document.querySelector('.operation-drawer');
    const nhan = [...ngan.querySelectorAll('button')].map(b => b.innerText.trim());
    return {nhan, conLai: XEM_SUA.filter(t => nhan.includes(t))};
  });
  check(soLieu.nutLa.conLai.length === 0,
    `ngan keo "Chay" con nut xem/sua: ${JSON.stringify(soLieu.nutLa.conLai)}`);

  // ── 7. Khung hep: ⛔ khong tran ngang ────────────────────────────────────
  //
  // Quay ve pha DANG CHAY: dong thoi gian la thu de tran nhat, va no chi ton tai
  // o pha ay.
  await page.goto(GOC + '?run=1');
  await page.locator('.run-timeline').waitFor({timeout: 15000});
  await page.setViewportSize({width: 390, height: 844});
  await page.waitForTimeout(300);
  soLieu.hep = await page.evaluate(() => ({
    tranTrang: document.documentElement.scrollWidth > window.innerWidth + 1,
    timelineTran: (() => {
      const t = document.querySelector('.run-timeline');
      return !!t && t.scrollWidth > t.clientWidth + 1;
    })(),
  }));
  check(!soLieu.hep.tranTrang, 'khung 390px: trang TRAN ngang');
  check(!soLieu.hep.timelineTran, 'khung 390px: dong thoi gian TRAN ngang');

  soLieu.pageErrors = pageErrors;
  soLieu.consoleErrors = consoleErrors;
  soLieu.failedRequests = failedRequests;
  soLieu.serverErrors = serverErrors;
  check(pageErrors.length === 0, `pageerror: ${JSON.stringify(pageErrors)}`);
  check(consoleErrors.length === 0, `console error: ${JSON.stringify(consoleErrors)}`);
  check(failedRequests.length === 0, `request hong: ${JSON.stringify(failedRequests)}`);
  check(serverErrors.length === 0, `phan hoi 5xx: ${JSON.stringify(serverErrors)}`);

  return loi.length ? {status: 'FAIL', loi, so_lieu: soLieu}
                    : {status: 'PASS', so_lieu: soLieu};
}
