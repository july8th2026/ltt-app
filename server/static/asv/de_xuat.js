/* asv/de_xuat.js — DE XUAT vung can che (`do_vung.de_xuat`) — v4-be-mat-de-xuat.
 *
 * 🔴 CHI la mot DE XUAT, KHONG bao gio tu dong che. Xem docstring dai o
 *    `apps/auto_scan_video/do_vung.py` muc 2 "Noi dang GOI Y, KHONG tu dong
 *    che" — nghiem thu 25/09 tren hai phim that cho thay V4b (dai chu goc)
 *    KHONG phan biet duoc dai phu de voi mot thanh HUD game. Module nay chi
 *    VE de xuat len man hinh; khach phai bam "Nhan" (`ASV.themVungDeXuat`,
 *    dinh nghia o `asv/vung.js`) truoc khi mot hop vao `vung[]` THAT gui len
 *    may chu.
 *
 * ## Luong: quet -> BA trang thai -> khach quyet -> (neu nhan) vao vung.js
 *
 *   1. Khach bam "Dò vùng cần che" -> `ASV.taiLenSom` (asv/tai_len.js) tai tep
 *      qua duong BEN VUNG — day la DIEM DUY NHAT may chu co tep cuc bo TRUOC
 *      khi lan chay duoc tao, nen la diem duy nhat goi `do_vung` duoc SOM.
 *      Tep khong di duoc duong nay (kieu/kich thuoc) -> nut chi bao, KHONG vo.
 *   2. `POST .../de-xuat-vung` -> `{trang_thai, vung, so_khung, ly_do}` DI
 *      THANG tu `do_vung.de_xuat()`, khong sua.
 *   3. Ba `trang_thai` PHAI hien BA cau khac nhau — bay gop hai trong ba da
 *      can kho nay 6 lan (`hai-trang-thai-gop-thanh-mot-gia-tri.md`):
 *        "co"            — co hop, khach xem tung hop va quyet
 *        "khong_co"      — DA quet that, khong thay gi (co bang chung `so_khung`)
 *        "khong_do_duoc" — CHUA quet duoc — khac hang voi "khong_co"
 *   4. Khach bam "Nhan" -> `ASV.themVungDeXuat({loai, x0..y1})` — loai MAC
 *      DINH theo nguon (logo tinh -> `lam_mo` "che kin"; dai chu -> `dien_nen`
 *      "dien nen", vi dai la mot bang ngang gan mep — dien nen mien mach hon
 *      mot o mo). Sau khi nhan, hop do do thuoc `vung.js` — sua/xoa o danh
 *      sach ben duoi nhu moi vung khac, KHONG con lien quan module nay.
 *
 * 🔑 `viewBox="0 0 1 1"`: toa do SVG CHINH LA phan so gui len — cung quy uoc
 *    voi `asv/vung.js` va `asv/logo.js`.
 */
(function () {
  "use strict";
  if (!window.ASV || !ASV.co) return;

  var t = ASV.t;
  var chu = ASV.chu;
  var an = ASV.an;
  var pt = ASV.pt;
  var form = ASV.form;

  var nut = document.getElementById("asv-dx-nut");
  var tt = document.getElementById("asv-dx-tt");
  var chiTiet = document.getElementById("asv-dx-chi-tiet");
  var soKhungP = document.getElementById("asv-dx-so-khung");
  var ds = document.getElementById("asv-dx-ds");
  var oTep = document.getElementById("asv-video");
  var oVe = document.getElementById("asv-ve");
  var video = document.getElementById("asv-xem");
  var lopDx = document.getElementById("asv-lop-de-xuat");
  var khoiDx = document.getElementById("asv-dx");
  var nhomVung = document.getElementById("asv-nhom-vung");

  if (!nut || !lopDx) return;

  var NS = "http://www.w3.org/2000/svg";
  var deXuat = [];       // {x0,y0,x1,y1,nguon} — CHUA nhan
  var dangQuet = false;
  var daQuetLanDau = false;

  //: Loai `vung_che` MAC DINH khi khach bam "Nhan", theo nguon cua de xuat.
  //: Xem docstring dau tep — "che kin" (logo) vs "dien nen" (dai chu).
  var LOAI_MAC_DINH = {logo_tinh: "lam_mo", dai_chu: "dien_nen"};

  var VUNG_TOI_DA = nhomVung
    ? (parseInt(nhomVung.getAttribute("data-toi-da"), 10) || 12) : 12;

  function goc() {
    return oVe ? oVe.getAttribute("data-url") : "";
  }

  function csrfTok() {
    var o = form && form.querySelector('[name="csrf_token"]');
    return o ? o.value : "";
  }

  function hienTt(s, canh) {
    if (!tt) return;
    an(tt, !s);
    tt.textContent = s || "";
    tt.classList.toggle("asv-dx-canh", !!canh);
  }

  function veHopDeXuat() {
    while (lopDx.firstChild) lopDx.removeChild(lopDx.firstChild);
    var hien = deXuat.length > 0
      && ASV.thoiLuongVideo > 0 && (!nhomVung || ASV.hopPreset(nhomVung));
    an(lopDx, !hien);
    if (!hien) return;
    deXuat.forEach(function (v, i) {
      var r = document.createElementNS(NS, "rect");
      r.setAttribute("x", v.x0);
      r.setAttribute("y", v.y0);
      r.setAttribute("width", Math.max(0, v.x1 - v.x0));
      r.setAttribute("height", Math.max(0, v.y1 - v.y0));
      r.setAttribute("class", "asv-dx-hop asv-dx-hop-" + v.nguon);
      r.setAttribute("data-dx-keo", String(i));
      lopDx.appendChild(r);
    });
  }

  function nhanDeXuat(v) {
    var loai = LOAI_MAC_DINH[v.nguon] || "lam_mo";
    var ok = ASV.themVungDeXuat({
      loai: loai, x0: v.x0, y0: v.y0, x1: v.x1, y1: v.y1
    });
    if (!ok) {
      hienTt(t("dx_het_cho", {n: VUNG_TOI_DA}), true);
      return false;
    }
    return true;
  }

  function veDanhSachDeXuat() {
    if (!ds) return;
    while (ds.firstChild) ds.removeChild(ds.firstChild);
    deXuat.forEach(function (v, i) {
      var li = document.createElement("li");
      li.className = "asv-vung-muc";

      var dau = document.createElement("div");
      dau.className = "asv-vung-dau";
      var ten = document.createElement("strong");
      ten.textContent = t(v.nguon === "logo_tinh"
        ? "dx_nguon_logo_tinh" : "dx_nguon_dai_chu");
      var viTri = document.createElement("span");
      viTri.className = "asv-ghi-chu";
      viTri.textContent = t("vung_vi_tri", {
        x: pt(v.x0), x2: pt(v.x1), y: pt(v.y0), y2: pt(v.y1)
      });
      dau.appendChild(ten);
      dau.appendChild(viTri);

      var hang = document.createElement("div");
      hang.className = "asv-dx-hang";

      var nhanNut = document.createElement("button");
      nhanNut.type = "button";
      nhanNut.className = "btn";
      nhanNut.textContent = t("dx_nhan");
      nhanNut.addEventListener("click", function () {
        if (!nhanDeXuat(v)) return;
        deXuat.splice(i, 1);
        veHopDeXuat();
        veDanhSachDeXuat();
      });

      var boNut = document.createElement("button");
      boNut.type = "button";
      boNut.className = "btn ghost";
      boNut.textContent = t("dx_bo");
      boNut.addEventListener("click", function () {
        deXuat.splice(i, 1);
        veHopDeXuat();
        veDanhSachDeXuat();
      });

      hang.appendChild(nhanNut);
      hang.appendChild(boNut);
      li.appendChild(dau);
      li.appendChild(hang);
      ds.appendChild(li);
    });
  }

  /* ── Keo DI CHUYEN ca hop (giu nguyen kich thuoc) — cung khuon `asv/logo.js`
   *    keo-tha logo (V6): giu do lech con tro-goc hop luc bat dau, kep [0,1].
   *    Chua co resize-tay-cam o day co y: san pham uu tien o SO % o danh sach
   *    "Vùng che" SAU khi nhan (them o `asv/vung.js:oGioToaDo`) — vua chinh
   *    xac hon keo bang ngon tay, vua doc duoc bang trinh doc man hinh (cung
   *    triet ly voi `.asv-vung-ds` — xem chu thich CSS `dai_test_...`). */
  var dangKeo = null;
  lopDx.addEventListener("pointerdown", function (ev) {
    var el = ev.target.closest && ev.target.closest("[data-dx-keo]");
    if (!el) return;
    var v = deXuat[parseInt(el.getAttribute("data-dx-keo"), 10)];
    if (!v) return;
    var o = lopDx.getBoundingClientRect();
    if (!o.width || !o.height) return;
    dangKeo = {
      v: v, o: o,
      dx: (ev.clientX - o.left) / o.width - v.x0,
      dy: (ev.clientY - o.top) / o.height - v.y0
    };
    lopDx.setPointerCapture(ev.pointerId);
    ev.preventDefault();
    if (video && !video.paused) video.pause();
  });
  lopDx.addEventListener("pointermove", function (ev) {
    if (!dangKeo) return;
    var o = dangKeo.o, v = dangKeo.v;
    var w = v.x1 - v.x0, h = v.y1 - v.y0;
    var nx = Math.min(1 - w, Math.max(0, (ev.clientX - o.left) / o.width - dangKeo.dx));
    var ny = Math.min(1 - h, Math.max(0, (ev.clientY - o.top) / o.height - dangKeo.dy));
    v.x0 = nx; v.x1 = nx + w; v.y0 = ny; v.y1 = ny + h;
    veHopDeXuat();
  });
  ["pointerup", "pointercancel"].forEach(function (ten) {
    lopDx.addEventListener(ten, function () {
      if (!dangKeo) return;
      dangKeo = null;
      veDanhSachDeXuat();      // cap nhat lai cac o "vi tri" trong danh sach
    });
  });

  /* ── Ket qua tu may chu -> ba trang thai KHAC nhau ───────────────────────
   *
   * 🔴 Bay gop "khong_co" voi "khong_do_duoc" da can kho nay nhieu lan — xem
   *    chu thich dau tep. Ba nhanh o day CHU Y viet RIENG, khong gop qua mot
   *    bieu thuc dung chung, de mot lan sua sau khong vo tinh nhap hai cau. */
  function xuLyKetQua(d) {
    deXuat = (d.vung || []).map(function (h) {
      return {x0: h.x0, y0: h.y0, x1: h.x1, y1: h.y1, nguon: h.nguon};
    });
    veHopDeXuat();
    veDanhSachDeXuat();

    var soKhung = d.so_khung || {};
    var logoN = soKhung.logo_tinh || 0;
    var daiN = soKhung.dai_chu || 0;
    if (chiTiet) {
      an(chiTiet, !(logoN || daiN));
      chu(soKhungP, t("dx_so_khung", {logo: logoN, dai: daiN}));
    }

    if (d.trang_thai === "khong_do_duoc") {
      hienTt(t("dx_khong_do_duoc", {ly_do: d.ly_do || ""}), true);
    } else if (d.trang_thai === "co") {
      hienTt(t("dx_co", {so: deXuat.length}), false);
    } else {
      hienTt(t("dx_khong_co"), false);
    }
  }

  function chayQuet() {
    if (dangQuet) return;
    var f = oTep && oTep.files && oTep.files[0];
    if (!f) { hienTt(t("dx_can_video"), true); return; }
    if (!ASV.benVungDuocKhong || !ASV.benVungDuocKhong(f)) {
      hienTt(t("dx_khong_ben_vung"), true);
      return;
    }
    dangQuet = true;
    nut.disabled = true;
    hienTt(t("dx_dang_tai"), false);

    ASV.taiLenSom(f).then(function (uploadId) {
      hienTt(t("dx_dang_quet"), false);
      var than = new FormData();
      than.append("csrf_token", csrfTok());
      than.append("tranh", JSON.stringify(
        ASV.layTranhVung ? ASV.layTranhVung() : []));
      return fetch(goc() + "/" + uploadId + "/de-xuat-vung", {
        method: "POST", body: than, credentials: "same-origin"
      });
    }).then(function (r) {
      if (!r.ok) throw r.status;
      return r.json();
    }).then(function (d) {
      dangQuet = false;
      nut.disabled = false;
      daQuetLanDau = true;
      chu(nut, t("dx_lai"));
      xuLyKetQua(d);
    }, function () {
      dangQuet = false;
      nut.disabled = false;
      if (daQuetLanDau) chu(nut, t("dx_lai"));
      hienTt(t("dx_loi"), true);
    });
  }

  nut.addEventListener("click", chayQuet);

  /* Chon LAI tep (con tai duoc, tuc chua quet lan nao) -> bo de xuat cu, vi
     no thuoc tep TRUOC. */
  if (oTep) {
    oTep.addEventListener("change", function () {
      if (!deXuat.length && !dangQuet) return;
      deXuat = [];
      veHopDeXuat();
      veDanhSachDeXuat();
      hienTt("", false);
    });
  }

  /* Vung che chi song o preset CAT — cung luat voi `asv/vung.js`. An ca khoi
     "Dò vùng cần che" thay vi chi khoa nut: hien mot cong cu khong lam gi la
     mot false feature, dung nhu vung.js da tranh. */
  function capNhatTheoPreset() {
    if (!nhomVung || !khoiDx) return;
    var duoc = ASV.hopPreset(nhomVung);
    an(khoiDx, !duoc);
    if (!duoc && deXuat.length) {
      deXuat = [];
      veHopDeXuat();
      veDanhSachDeXuat();
      hienTt("", false);
    }
  }
  ASV.khiDoiPreset(capNhatTheoPreset);
  capNhatTheoPreset();

  ASV.khiCoVideo(function () { veHopDeXuat(); });
})();
