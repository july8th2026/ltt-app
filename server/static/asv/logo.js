/* asv/logo.js — LOGO anh.
 *
 * 🔴 **Anh di CUNG bieu mau, khong qua mot cua tai len rieng.**
 *
 *    Mot cua rieng cap ra mot KHOA khach cam theo, roi lan chay sau nhac lai
 *    khoa do — tuc may chu phai tra loi *"khoa nay co that su cua nguoi dang
 *    goi khong"* o moi lan dung. Do dung la be mat IDOR ma
 *    `upload_sessions.owned(...)` phai loc ngay trong truy van de dong lai.
 *
 * ⇒ Moi logo co mot `<input type=file name=logo_anh>` RIENG, dung trong hang
 *   cua no. Chung di theo form, va may chu doi chieu SO LUONG voi mang hinh
 *   hoc — lech thi tu choi, khong zip mu.
 *
 * ⚠️ Thu tu cua cac `<input>` trong DOM la thu tu chung di trong multipart,
 *    va do la thu ta dua vao. Nen khi xoa mot hang, ta VE LAI ca danh sach
 *    thay vi go mot phan tu — ve lai thi hai mang khong the lech.
 */
(function () {
  "use strict";
  if (!window.ASV || !ASV.co) return;

  var t = ASV.t;
  var chu = ASV.chu;

  var nhomLg = document.getElementById("asv-nhom-logo");
  var dsLg = document.getElementById("asv-logo-ds");
  var oLg = document.getElementById("asv-logo");
  var ttLg = document.getElementById("asv-logo-tt");
  var chanLg = document.getElementById("asv-logo-chan");
  var nutLgThem = document.getElementById("asv-logo-them");
  var thanhLg = nhomLg ? nhomLg.querySelector(".asv-vung-thanh") : null;
  var dsLogo = [];
  var LG_TOI_DA = nhomLg
    ? (parseInt(nhomLg.getAttribute("data-toi-da"), 10) || 2) : 2;
  var LG_TRAN_MB = nhomLg
    ? (parseInt(nhomLg.getAttribute("data-tran-mb"), 10) || 8) : 8;
  var LG_KIEU = ["image/png", "image/jpeg", "image/webp"];

  function dongBoLogo() {
    /* ⛔ Chi gui nhung hang DA CO ANH. Mot hang chua chon anh la mot hang khach
     *    chua lam xong, va gui no se lam hai mang lech do dai — may chu tu choi
     *    ca lo. Bo qua thi phai NOI RA, va dong trang thai noi. */
    var gui = dsLogo.filter(function (l) { return !!l.tep; });
    if (oLg) {
      oLg.value = gui.length ? JSON.stringify(gui.map(function (l) {
        /* ⛔ KHONG gui `khoa`. May chu dat no sau khi `run.id` ton tai; bia
         *    mot chuoi gia o day roi de may chu ghi de la day client toi cho
         *    tao du lieu khong co that. */
        return {x: l.x, y: l.y, rong: l.rong, do_mo: l.do_mo};
      })) : "";
    }
    if (!dsLogo.length) { chu(ttLg, t("lg_chua_co")); return; }
    if (gui.length < dsLogo.length) { chu(ttLg, t("lg_chua_chon")); return; }
    chu(ttLg, t("lg_dem", {so: gui.length}));
  }

  function oLgSo(l, khoa, nhan, thap, cao) {
    var lb = document.createElement("label");
    lb.className = "asv-vung-gio";
    var s = document.createElement("span");
    s.textContent = nhan;
    var i = document.createElement("input");
    i.type = "number";
    i.className = "asv-cat-so";
    i.min = String(thap);
    i.max = String(cao);
    i.step = "1";
    i.value = String(Math.round(l[khoa] * 100));
    /* ⭐ Neo o de bo KEO tim lai duoc no: keo phai cap nhat o so, neu khong hai
     *    cho tren man hinh noi hai con so khac nhau ve cung mot logo.
     * ⛔ Va keo KHONG duoc ve lai ca danh sach de dong bo — ve lai huy cac
     *    `<input type=file>`, tuc **mat anh khach da chon**. Sua thang `.value`. */
    i.setAttribute("data-lg-o", khoa);
    i.addEventListener("input", function () {
      var x = parseFloat(i.value);
      /* Khong kep ve bien — may chu la cho phat bieu duy nhat cua luat do. */
      if (isFinite(x)) { l[khoa] = x / 100; veDiemLogo(); dongBoLogo(); }
    });
    lb.appendChild(s);
    lb.appendChild(i);
    return lb;
  }

  function veDanhSachLogo() {
    if (!dsLg) return;
    while (dsLg.firstChild) dsLg.removeChild(dsLg.firstChild);
    dsLogo.forEach(function (l, i) {
      var li = document.createElement("li");
      li.className = "asv-vung-muc";

      var lbTep = document.createElement("label");
      lbTep.className = "asv-lp-chu";
      var sTep = document.createElement("span");
      sTep.textContent = t("lg_chon_anh");
      var iTep = document.createElement("input");
      iTep.type = "file";
      iTep.name = "logo_anh";
      iTep.accept = LG_KIEU.join(",");
      iTep.addEventListener("change", function () {
        var f = iTep.files && iTep.files[0];
        if (!f) { l.tep = null; dongBoLogo(); return; }
        if (LG_KIEU.indexOf(f.type) < 0) {
          iTep.value = ""; l.tep = null;
          chu(ttLg, t("lg_sai_kieu"));
          return;
        }
        if (f.size > LG_TRAN_MB * 1024 * 1024) {
          iTep.value = ""; l.tep = null;
          chu(ttLg, t("lg_qua_lon", {mb: LG_TRAN_MB}));
          return;
        }
        l.tep = f.name;
        /* ⭐ Doc TI LE THAT cua anh de o xem truoc ve dung hinh dang se dan len
         *    video. `overlay` cua ffmpeg dat goc TREN-TRAI o `(W*x, H*y)` va
         *    `scale=w=<rong*W>:h=-2` giu nguyen ti le, nen chieu cao **suy ra
         *    duoc** — ⛔ khong phai doan.
         *
         * 🔴 **`data:` chu khong `blob:`** — do tren trinh duyet that: CSP chan
         *    `blob:` o `img-src` (`<video>` song duoc vi no thuoc `media-src`).
         *
         * ⛔ Cach sua dung khong phai noi rong CSP: doi mot rui ro that cua CA
         *    NEN TANG lay mot o xem truoc cua MOT app. `data:` da duoc phep, va
         *    `LG_TRAN_MB` chan tep nen chuoi khong lon vo han.
         *
         * ⚠️ Tep VAN khong di dau ca: `FileReader` doc trong trinh duyet. */
        l.tiLe = 0;
        l.anhUrl = "";
        var doc = new FileReader();
        doc.onload = function () {
          l.anhUrl = String(doc.result || "");
          var im = new Image();
          im.onload = function () {
            if (im.naturalWidth > 0) l.tiLe = im.naturalHeight / im.naturalWidth;
            veDiemLogo();
          };
          im.src = l.anhUrl;
        };
        doc.readAsDataURL(f);
        veDiemLogo();
        dongBoLogo();
      });
      lbTep.appendChild(sTep);
      lbTep.appendChild(iTep);

      var so = document.createElement("div");
      so.className = "asv-vung-gio-o asv-lp-o";
      so.appendChild(oLgSo(l, "x", t("lp_ngang"), 0, 100));
      so.appendChild(oLgSo(l, "y", t("lp_doc"), 0, 100));
      so.appendChild(oLgSo(l, "rong", t("lg_rong"), 3, 40));

      var xoa = document.createElement("button");
      xoa.type = "button";
      xoa.className = "btn ghost";
      xoa.textContent = t("lg_xoa_mot");
      xoa.addEventListener("click", function () {
        /* ⚠️ Ve lai CA danh sach, khong go mot phan tu: thu tu cac `<input
         *    type=file>` trong DOM la thu tu chung di trong multipart, va ve
         *    lai la cach duy nhat chac chan hai mang khong lech. Cai gia la
         *    khach phai chon lai anh cua nhung hang con lai — noi ra bang dong
         *    trang thai, chu khong de ho tu phat hien. */
        dsLogo.splice(i, 1);
        dsLogo.forEach(function (m) { m.tep = null; m.anhUrl = null; m.tiLe = 0; });
        veDanhSachLogo();
        veDiemLogo();
        dongBoLogo();
      });

      li.appendChild(lbTep);
      li.appendChild(so);
      li.appendChild(xoa);
      dsLg.appendChild(li);
    });
  }

  /* ══ KEO-THA vi tri tren khung hinh (V6) ═══════════════════════════════════
   *
   * 🔑 Keo la cach nhap THU HAI cho CUNG du lieu: ca hai ghi vao `dsLogo` roi
   *    goi `dongBoLogo()` — hai ban tay mot vo lang, khong hai trang thai.
   *
   * ⭐ `viewBox="0 0 1 1"`: toa do trong SVG CHINH LA phan so se gui len, khong
   *    co phep nhan nao de lam sai (cung ly do `asv/vung.js` chon cach nay).
   *
   * ⚠️ Hop ve dung TI LE THAT cua anh (`l.tiLe`), ⛔ khong phai mot hinh vuong
   *    dat cho co: `overlay` dat goc TREN-TRAI o `(W*x, H*y)` va
   *    `scale=w=rong*W:h=-2` giu nguyen ti le. Mot o xem truoc sai hinh dang la
   *    mot o xem truoc noi doi ve ket qua.
   */
  var NS = "http://www.w3.org/2000/svg";
  var lopLg = document.getElementById("asv-lop-logo");
  var video = document.getElementById("asv-xem");

  function caoHop(l) {
    /* Chieu cao cua logo theo PHAN SO KHUNG. `rong` la phan so BE NGANG khung,
     * nen doi sang phan so BE DOC phai nhan ti le khung hinh.
     * ⛔ Chua biet ti le anh hay ti le video thi tra `0` — goi y se ve mot diem
     *    neo thay vi mot hop co kich thuoc BIA RA. */
    var vw = video && video.videoWidth, vh = video && video.videoHeight;
    if (!l.tiLe || !vw || !vh) return 0;
    return l.rong * l.tiLe * (vw / vh);
  }

  function veDiemLogo() {
    if (!lopLg) return;
    while (lopLg.firstChild) lopLg.removeChild(lopLg.firstChild);
    var hien = ASV.thoiLuongVideo > 0 && dsLogo.length > 0
               && (!nhomLg || ASV.hopPreset(nhomLg));
    ASV.an(lopLg, !hien);   /* `<svg>`: xem `ASV.an` o `asv/nen.js` */
    if (!hien) return;
    dsLogo.forEach(function (l, i) {
      var h = caoHop(l);
      var g = document.createElementNS(NS, "g");
      g.setAttribute("class", "asv-lg-keo");
      g.setAttribute("data-lg-keo", String(i));
      if (l.anhUrl && h > 0) {
        var im = document.createElementNS(NS, "image");
        im.setAttribute("href", l.anhUrl);
        im.setAttribute("x", l.x); im.setAttribute("y", l.y);
        im.setAttribute("width", l.rong); im.setAttribute("height", h);
        im.setAttribute("preserveAspectRatio", "none");
        im.setAttribute("opacity", String(l.do_mo));
        g.appendChild(im);
      }
      var r = document.createElementNS(NS, "rect");
      r.setAttribute("x", l.x); r.setAttribute("y", l.y);
      r.setAttribute("width", l.rong);
      r.setAttribute("height", h > 0 ? h : 0.06);
      r.setAttribute("class", "asv-lg-hop");
      g.appendChild(r);
      lopLg.appendChild(g);
    });
  }

  /* Cap nhat o so cua hang `i` MA KHONG ve lai danh sach — ve lai se huy cac
   * `<input type=file>`, tuc mat anh khach da chon. */
  function datOSo(i, l) {
    if (!dsLg) return;
    var li = dsLg.children[i];
    if (!li) return;
    ["x", "y"].forEach(function (k) {
      var o = li.querySelector('[data-lg-o="' + k + '"]');
      if (o) o.value = String(Math.round(l[k] * 100));
    });
  }

  if (lopLg) {
    var dangKeo = null;
    lopLg.addEventListener("pointerdown", function (ev) {
      var g = ev.target.closest && ev.target.closest("[data-lg-keo]");
      if (!g) return;
      var l = dsLogo[parseInt(g.getAttribute("data-lg-keo"), 10)];
      if (!l) return;
      var o = lopLg.getBoundingClientRect();
      if (!o.width || !o.height) return;
      /* ⭐ Giu DO LECH giua con tro va goc hop: khong giu thi hop nhay sao cho
       *    goc cua no ve dung duoi ngon tay ngay cu bam dau tien. */
      dangKeo = {l: l, o: o, i: parseInt(g.getAttribute("data-lg-keo"), 10),
                 dx: (ev.clientX - o.left) / o.width - l.x,
                 dy: (ev.clientY - o.top) / o.height - l.y};
      lopLg.setPointerCapture(ev.pointerId);
      ev.preventDefault();
      if (video && !video.paused) video.pause();
    });
    lopLg.addEventListener("pointermove", function (ev) {
      if (!dangKeo) return;
      var o = dangKeo.o, l = dangKeo.l;
      /* Kep vao [0,1] — cung mien ma `logo.chuan_hoa` nhan. Day la mot phep kep
       * ve HIEN THI cua mot cu keo dang dien ra, khong phai "sua ho" mot gia tri
       * khach da nhap: khach keo ra ngoai khung thi y dinh la "sat mep". */
      l.x = Math.min(1, Math.max(0, (ev.clientX - o.left) / o.width - dangKeo.dx));
      l.y = Math.min(1, Math.max(0, (ev.clientY - o.top) / o.height - dangKeo.dy));
      veDiemLogo();
      datOSo(dangKeo.i, l);
    });
    ["pointerup", "pointercancel"].forEach(function (ten) {
      lopLg.addEventListener(ten, function () {
        if (!dangKeo) return;
        dangKeo = null;
        dongBoLogo();
      });
    });
  }

  ASV.khiCoVideo(function () { veDiemLogo(); });

  if (nutLgThem) {
    nutLgThem.addEventListener("click", function () {
      if (dsLogo.length >= LG_TOI_DA) {
        chu(ttLg, t("lg_het_cho", {n: LG_TOI_DA}));
        return;
      }
      dsLogo.push({x: 0.05, y: 0.05, rong: 0.15, do_mo: 1.0, tep: null});
      veDanhSachLogo();
      veDiemLogo();
      dongBoLogo();
    });
  }

  function capNhatLogoTheoPreset() {
    if (!nhomLg) return;
    var duoc = ASV.hopPreset(nhomLg);
    if (thanhLg) thanhLg.hidden = !duoc;
    if (dsLg) dsLg.hidden = !duoc;
    if (chanLg) chanLg.hidden = duoc;
    /* ⛔ Xoa han khi doi preset: giu lai mot `<input type=file>` da chon anh la
     *    van gui anh do len may chu theo form. An di khong phai la go. */
    if (!duoc && dsLogo.length) {
      dsLogo.length = 0;
      veDanhSachLogo();
    }
    veDiemLogo();
    if (!duoc && oLg) oLg.value = "";
    dongBoLogo();
  }

  ASV.khiDoiPreset(capNhatLogoTheoPreset);
  capNhatLogoTheoPreset();
})();
