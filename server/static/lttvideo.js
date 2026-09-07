/* Studio Video AI — hành vi khoang tạo + thư viện.
 *
 * ⭐ Mượn khuôn của `apps/taovideo` (Seedance): drawer/scrim cho màn hẹp, quản
 *    lý `inert`/`aria-expanded`/focus, lưới⇄danh sách nhớ trong localStorage.
 *    Phần trợ năng ở đó đã làm đúng, chép lại rẻ hơn nghĩ lại.
 *
 * 📌 Tệp RIÊNG chứ không nhúng trong template: `CLAUDE.md` quy tắc 6 — static
 *    đi qua Cloudflare có TTL, nên nó phải cache-bust được bằng `?v=`. Một khối
 *    <script> nhúng thì không có URL để đổi.
 */
(function () {
  'use strict';
  var q = function (s) { return document.querySelector(s); };
  var qa = function (s) { return [].slice.call(document.querySelectorAll(s)); };

  /* Tiền tố route do nền tảng gắn — đọc từ chính liên kết trên trang chứ không
     gõ cứng, vì `MANIFEST.route_prefix` là nguồn duy nhất.
     📌 Đặt Ở ĐẦU: bản trước để nó ở cuối tệp và dựa vào hoisting của `var`.
        Nó *chạy* được, nhưng bất cứ ai thêm một lời gọi lúc nạp trang sẽ nhận
        `undefined` — một cái bẫy đặt sẵn cho người sau. */
  var PREFIX = (function () {
    var a = q('.tv-nav a.on');
    return a ? a.getAttribute('href').replace(/\/$/, '') : '/lttvideo';
  })();

  var compose = q('#tv-compose');
  var drawer = q('.tv-drawer');
  var scrim = q('.tv-compose-scrim');
  var closeBtn = q('.tv-compose-close');
  var hep = window.matchMedia('(max-width:1050px)');

  /* ── Khoang tạo: mở/đóng trên màn hẹp ───────────────────────────────── */
  function dongBoCheDo() {
    if (!compose) return;
    var an = hep.matches && !compose.classList.contains('open');
    compose.toggleAttribute('inert', an);
    if (an) compose.setAttribute('aria-hidden', 'true');
    else compose.removeAttribute('aria-hidden');
  }
  function dong() {
    if (!compose) return;
    compose.classList.remove('open');
    document.body.classList.remove('tv-compose-open');
    if (drawer) {
      drawer.setAttribute('aria-expanded', 'false');
      drawer.textContent = '☰ ' + drawer.dataset.openLabel;
    }
    dongBoCheDo();
    if (hep.matches && drawer) drawer.focus();
  }
  function mo() {
    if (!compose) return;
    compose.classList.add('open');
    document.body.classList.add('tv-compose-open');
    compose.removeAttribute('inert');
    compose.removeAttribute('aria-hidden');
    if (drawer) {
      drawer.setAttribute('aria-expanded', 'true');
      drawer.textContent = '✕ ' + drawer.dataset.closeLabel;
    }
    var dau = compose.querySelector('input:not([type=hidden]),textarea,select,button');
    if (dau) dau.focus();
  }
  if (drawer) drawer.addEventListener('click', function () {
    compose.classList.contains('open') ? dong() : mo();
  });
  if (closeBtn) closeBtn.addEventListener('click', dong);
  if (scrim) scrim.addEventListener('click', dong);
  qa('[data-open-compose]').forEach(function (b) { b.addEventListener('click', mo); });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && compose && compose.classList.contains('open')) dong();
  });
  if (hep.addEventListener) hep.addEventListener('change', dongBoCheDo);
  else if (hep.addListener) hep.addListener(dongBoCheDo);
  dongBoCheDo();

  qa('[data-open-assets]').forEach(function (a) {
    a.addEventListener('click', function () {
      var d = q('#tv-assets'); if (d) d.open = true;
    });
  });

  /* ── Xem trước tệp đính kèm ─────────────────────────────────────────────
   *
   * ⭐ Muon tu Seedance: thay tep minh vua chon TRUOC khi gui la khac biet giua
   *    "toi nghi minh da dinh dung anh" va "toi THAY anh cua minh".
   *
   * 🔴 ANH dung `FileReader` -> `data:`, VIDEO dung `createObjectURL` -> `blob:`.
   *    Khong phai tuy hung — do la dung ranh gioi CSP o `server/app.py:213-220`:
   *
   *        img-src   'self' data:  https://*.r2...        (KHONG co blob:)
   *        media-src 'self' blob:  https://*.r2...        (CO blob:)
   *
   *    Ban dau toi dung `blob:` cho ca hai. DOM van co the <img>, phep kiem cau
   *    truc van xanh — nhung trinh duyet CHAN anh va no chi hien ra o console.
   *    Mot that bai hinh anh im lang, chi trinh duyet that moi bat duoc.
   *
   * ⛔ KHONG co o chon vai tro (khung dau / khung cuoi) nhu Seedance. Doc
   *    `wgp.py:1437-1466`: `"E"` doi model khai `image_prompt_types_allowed`,
   *    va `"E"` khong kem `S`/`V`/`L` bi AM THAM go bo (dong 1458). Ta chi nhan
   *    MOT tep, nen "chi khung cuoi" hoac loi hoac khong lam gi — mot nut noi
   *    doi. Mo lai khi nhan duoc hai tep VA kiem duoc `image_prompt_types_allowed`
   *    tren may that.
   */
  (function () {
    var o = document.querySelector('input[type=file][name=media]');
    var khung = q('#tv-refs');
    if (!o || !khung) return;
    var urlDangGiu = [];

    function co(n) {
      return n < 1048576 ? (n / 1024).toFixed(0) + ' KB'
                         : (n / 1048576).toFixed(1) + ' MB';
    }

    function don() {
      urlDangGiu.forEach(function (u) { URL.revokeObjectURL(u); });
      urlDangGiu = [];
      khung.replaceChildren();
    }

    o.addEventListener('change', function () {
      don();
      var f = o.files && o.files[0];
      if (!f) return;
      var la_video = f.type.indexOf('video/') === 0;
      var el = document.createElement(la_video ? 'video' : 'img');
      el.className = 'tv-ref-preview';

      if (la_video) {
        var url = URL.createObjectURL(f);   // media-src cho phep blob:
        urlDangGiu.push(url);
        el.src = url;
        el.controls = true;
        el.muted = true;
      } else {
        var doc = new FileReader();          // img-src chi cho phep data:
        doc.addEventListener('load', function () {
          el.src = String(doc.result || '');
        });
        doc.readAsDataURL(f);
      }

      var ten = document.createElement('span');
      ten.textContent = f.name + ' · ' + co(f.size);
      var hang = document.createElement('div');
      hang.className = 'tv-ref-row';
      hang.append(el, ten);
      khung.append(hang);
    });

    // ⛔ Tra lai bo nho cho trinh duyet. Mot `createObjectURL` khong `revoke` la
    //    mot tep giu nguyen trong RAM cho toi khi dong tab.
    window.addEventListener('beforeunload', don);
  })();

  /* ── Giá giữ chỗ + cảnh báo video dài ───────────────────────────────── */
  var oDoDai = q('#tv-dodai');
  function capNhatGia() {
    if (!oDoDai) return;
    var chon = oDoDai.options[oDoDai.selectedIndex];
    var gia = q('#tv-gia');
    if (chon && gia) gia.textContent = (chon.dataset.gia || '?') + ' credit';
    var canhBao = q('#tv-canh-bao-dai');
    if (canhBao) canhBao.hidden = parseInt(oDoDai.value, 10) < 10;
  }
  if (oDoDai) oDoDai.addEventListener('change', capNhatGia);
  capNhatGia();

  /* ── Mô tả đã dùng ──────────────────────────────────────────────────── */
  var lichSu = q('#tv-history');
  if (lichSu) lichSu.addEventListener('change', function () {
    if (lichSu.value) { var o = q('#tv-prompt'); if (o) o.value = lichSu.value; }
  });

  /* ── Làm lại: nạp tham số của một video cũ vào khoang tạo ───────────── */
  qa('.tv-remix').forEach(function (b) {
    b.addEventListener('click', function () {
      var o = q('#tv-prompt');
      if (o) o.value = b.dataset.prompt || '';
      [['#tv-tile', 'tile'], ['#tv-dodai', 'dodai']].forEach(function (cap) {
        var el = q(cap[0]); if (!el) return;
        var co = [].some.call(el.options, function (x) { return x.value === b.dataset[cap[1]]; });
        if (co) el.value = b.dataset[cap[1]];
      });
      capNhatGia();
      mo();
    });
  });

  /* ── Lưới ⇄ danh sách, nhớ theo trình duyệt ─────────────────────────── */
  (function () {
    var luoi = q('.tv-grid');
    var nut = qa('[data-view]');
    if (!luoi) return;
    function dat(kieu) {
      kieu = kieu === 'list' ? 'list' : 'grid';
      luoi.classList.toggle('list-view', kieu === 'list');
      nut.forEach(function (b) {
        b.setAttribute('aria-pressed', String(b.dataset.view === kieu));
      });
      // ⛔ localStorage co the NEM (cua so rieng tu, chan du lieu trang) — mot
      //    tien nghi nho khong duoc lam vo ca trang.
      try { localStorage.setItem('ltt.lttvideo.view', kieu); } catch (e) { /* bo qua co y */ }
    }
    nut.forEach(function (b) { b.addEventListener('click', function () { dat(b.dataset.view); }); });
    var cu = null;
    try { cu = localStorage.getItem('ltt.lttvideo.view'); } catch (e) { cu = null; }
    dat(cu || 'grid');
  })();

  /* ── Nâng nét: báo giá TRƯỚC khi xác nhận ───────────────────────────────
   *
   * 🔑 Goi THANG be mat HTTP cong khai cua `upscalevideo`:
   *      POST /upscalevideo/batch-quote   -> bao gia
   *      POST /upscalevideo/queue         -> tao viec
   *
   * ⛔ KHONG import cheo, va KHONG chep lai cong thuc gia.
   *    `tests/test_147_layering.py:117` chi cho phep `taovideo -> upscalevideo`;
   *    `lttvideo` khong nam trong danh sach ay. Va chep cong thuc gia sang day
   *    la dung mot ban sao thu hai cua mot quy tac tien — thu chac chan se troi.
   *
   * ⭐ Route cua no CHINH LA hop dong. Gia tra ve tu chinh `upscalevideo.cost`,
   *    nen doi gia ben do thi man nay doi theo, khong can ai nho gi.
   */
  (function () {
    var dlg = q('#tv-upscale-dialog');
    if (!dlg) return;
    var khoa = '', giay = 0;
    var oCao = q('#tv-height');
    var oQuote = q('#tv-quote');

    function csrf() { var e = q('[name=csrf_token]'); return e ? e.value : ''; }

    async function baoGia() {
      oQuote.textContent = 'Đang tính chi phí…';
      try {
        var r = await fetch('/upscalevideo/batch-quote', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            durations: [giay], target_height: parseInt(oCao.value, 10),
            preset: 'fast'
          })
        });
        var d = await r.json();
        oQuote.textContent = d.ok
          ? 'Chi phí: ' + d.total_credit + ' credit · ' + oCao.value + 'p'
          : (d.error || 'Không tính được chi phí');
      } catch (e) {
        oQuote.textContent = 'Không kết nối được để báo giá';
      }
    }

    qa('.tv-upscale').forEach(function (b) {
      b.addEventListener('click', function () {
        khoa = b.dataset.khoa || '';
        giay = parseFloat(b.dataset.dodai || '0') || 0;
        dlg.showModal();
        baoGia();
      });
    });
    oCao.addEventListener('change', baoGia);

    q('#tv-confirm').addEventListener('click', function (e) {
      e.preventDefault();
      // Bieu mau that, dieu huong that — cung duong ma GUI cua `upscalevideo`
      // dung. CSRF gan theo PHIEN chu khong theo duong dan, nen token phat o
      // trang nay dung duoc o route ben kia.
      var f = document.createElement('form');
      f.method = 'post';
      f.action = '/upscalevideo/queue';
      [['csrf_token', csrf()], ['video_key', khoa],
       ['duration_s', String(giay)], ['target_height', oCao.value],
       ['preset', 'fast']].forEach(function (cap) {
        var i = document.createElement('input');
        i.type = 'hidden'; i.name = cap[0]; i.value = cap[1];
        f.appendChild(i);
      });
      document.body.appendChild(f);
      f.submit();
    });
  })();

})();
