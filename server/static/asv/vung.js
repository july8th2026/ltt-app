/* asv/vung.js — TRINH SUA VUNG: ve tren khung hinh, va danh sach o ben duoi.
 *
 * 🔑 Toa do o day la PHAN SO 0..1 tu dau den cuoi, khong bao gio pixel.
 *    `viewBox="0 0 1 1"` cua SVG lam viec doi don vi bien mat: mot hop trong
 *    SVG CHINH LA hop se duoc gui len. Khong co phep nhan nao de lam sai.
 *
 * ⛔ Va khong co phep "sua hoc": hop ve nguoc hay qua nho bi BO tai cho, dung
 *    nhu `vung_che.chuan_hoa` se lam o may chu. Hai noi cung mot luat.
 */
(function () {
  "use strict";
  if (!window.ASV || !ASV.co) return;

  var t = ASV.t;
  var chu = ASV.chu;
  var pt = ASV.pt;

  var video = document.getElementById("asv-xem");
  var khung = document.getElementById("asv-khung");
  var lop = document.getElementById("asv-lop");
  var oVung = document.getElementById("asv-vung");
  var vungTt = document.getElementById("asv-vung-tt");

  var NS = "http://www.w3.org/2000/svg";
  var vung = [];          // toa do CHUAN HOA 0..1
  var loaiDangVe = null;  // null = khong o che do ve

  var CANH_TOI_THIEU = 0.01;   // khop `vung_che.CANH_TOI_THIEU`

  /* Ve LAI CHI cac hop tren SVG — tach khoi `veLai()` vi o so toa do (them o
   * pha nay, xem `oGioToaDo`) can cap nhat khung hinh SAU MOI KY TU go, va
   * dung lai ca `veDanhSachVung()` cho viec do se huy `<input>` dang go va mat
   * tieu diem — dung loi da tranh o `oGio` cho `tu_giay`/`den_giay`. */
  function veHop() {
    if (!lop) return;
    while (lop.firstChild) lop.removeChild(lop.firstChild);
    vung.forEach(function (v) {
      var r = document.createElementNS(NS, "rect");
      r.setAttribute("x", v.x0);
      r.setAttribute("y", v.y0);
      r.setAttribute("width", v.x1 - v.x0);
      r.setAttribute("height", v.y1 - v.y0);
      r.setAttribute("class", "asv-hop asv-hop-" + v.loai);
      lop.appendChild(r);
    });
  }

  function veLai() {
    veHop();
    veDanhSachVung();
    dongBoVung();
  }

  /* ── Danh sach vung: noi DUY NHAT dat duoc khoang thoi gian ──────────────
   *
   * 🔴 Ton tai vi mot ly do cu the. Tu V5 `vung_che` da nhan, kiem va luu
   *    `tu_giay`/`den_giay`, `ban_dung` da ghi chung xuong — va **khong co cho
   *    nao tren man hinh de dat chung**, cung khong co dong ma nao doc chung khi
   *    dung bo loc (sua o pha 12a). Nang luc co, khong ai di tren duong toi no.
   *
   * ⛔ Mo duong o day ma khong sua bo loc la ban mot thu khong xay ra. Hai nua
   *    phai di cung nhau, va chung da di cung nhau.
   */
  var dsVung = document.getElementById("asv-vung-ds");

  function dongBoVung() {
    if (oVung) oVung.value = vung.length ? JSON.stringify(vung) : "";
    chu(vungTt, vung.length
      ? t("vung_dem", {so: vung.length})
      : t("vung_chua_co"));
  }

  function oGio(v, khoa, nhan) {
    var l = document.createElement("label");
    l.className = "asv-vung-gio";
    var s = document.createElement("span");
    s.textContent = nhan;
    var i = document.createElement("input");
    i.type = "number";
    i.min = "0";
    i.step = "0.1";
    i.className = "asv-cat-so";
    i.placeholder = t("vung_ca_video");
    /* `ASV.thoiLuongVideo` do `asv/xem_truoc.js` dat qua `phatCoVideo`, va no
       duoc dat TRUOC khi bat ky nguoi dang ky nao chay — nen doc o day luon
       thay gia tri that, bat ke module nao nap truoc. */
    if (ASV.thoiLuongVideo > 0) i.max = String(ASV.thoiLuongVideo);
    if (v[khoa] !== undefined && v[khoa] !== null) i.value = v[khoa];
    i.addEventListener("input", function () {
      /* ⛔ O RONG = khong khai, khong phai 0. Ghi `0` vao `tu_giay` la mot cua
       *    so "tu dau video" — mot cau KHAC HAN "ca video", va tu pha 12a hai
       *    cau do cho hai van tay khac nhau. Nen phai `delete`, khong duoc
       *    gan 0. */
      if (i.value === "") {
        delete v[khoa];
      } else {
        var x = parseFloat(i.value);
        if (isFinite(x)) v[khoa] = x;
      }
      /* Chi dong bo, KHONG `veLai()`: ve lai la dung ca danh sach, va o dang
         go se mat tieu diem ngay sau ky tu dau tien. */
      dongBoVung();
    });
    l.appendChild(s);
    l.appendChild(i);
    return l;
  }

  /* O SO cho MOT canh toa do (0..100%) — duong SUA CHINH XAC, doc duoc bang
   * trinh doc man hinh, cho mot de xuat `do_vung` hoi lech. `veHop()` CHI (⛔
   * khong `veLai()`) — ve lai ca danh sach se huy `<input>` dang go, cung ly
   * do voi `oGio`. `oVt` la nhan vi tri cua CHINH hang nay, sua truc tiep. */
  function oGioToaDo(v, khoa, nhan, oVt) {
    var l = document.createElement("label");
    l.className = "asv-vung-gio";
    var s = document.createElement("span");
    s.textContent = nhan;
    var i = document.createElement("input");
    i.type = "number";
    i.min = "0";
    i.max = "100";
    i.step = "1";
    i.className = "asv-cat-so";
    i.value = String(pt(v[khoa]));
    i.addEventListener("input", function () {
      var x = parseFloat(i.value);
      if (!isFinite(x)) return;
      // Kep [0,1] o hien thi — may chu (`vung_che._so`) la cho phat bieu DUY
      // NHAT cua luat gia tri; o day chi tranh mot hop lat nguoc khi go.
      v[khoa] = Math.min(1, Math.max(0, x / 100));
      veHop();
      dongBoVung();
      if (oVt) {
        oVt.textContent = t("vung_vi_tri", {
          x: pt(v.x0), x2: pt(v.x1), y: pt(v.y0), y2: pt(v.y1)
        });
      }
    });
    l.appendChild(s);
    l.appendChild(i);
    return l;
  }

  function veDanhSachVung() {
    if (!dsVung) return;
    while (dsVung.firstChild) dsVung.removeChild(dsVung.firstChild);
    vung.forEach(function (v, i) {
      var li = document.createElement("li");
      li.className = "asv-vung-muc";

      var dauMuc = document.createElement("div");
      dauMuc.className = "asv-vung-dau";
      var ten = document.createElement("strong");
      ten.textContent = t("vung_loai_" + v.loai) || v.loai;
      var oVt = document.createElement("span");
      oVt.className = "asv-ghi-chu";
      oVt.textContent = t("vung_vi_tri", {
        x: pt(v.x0), x2: pt(v.x1), y: pt(v.y0), y2: pt(v.y1)
      });
      dauMuc.appendChild(ten);
      dauMuc.appendChild(oVt);

      var toaDoGio = document.createElement("div");
      toaDoGio.className = "asv-vung-gio-o";
      toaDoGio.appendChild(oGioToaDo(v, "x0", t("vung_trai"), oVt));
      toaDoGio.appendChild(oGioToaDo(v, "x1", t("vung_phai"), oVt));
      toaDoGio.appendChild(oGioToaDo(v, "y0", t("vung_tren"), oVt));
      toaDoGio.appendChild(oGioToaDo(v, "y1", t("vung_duoi"), oVt));

      var gio = document.createElement("div");
      gio.className = "asv-vung-gio-o";
      gio.appendChild(oGio(v, "tu_giay", t("vung_tu_giay")));
      gio.appendChild(oGio(v, "den_giay", t("vung_den_giay")));

      var xoa = document.createElement("button");
      xoa.type = "button";
      xoa.className = "btn ghost";
      xoa.textContent = t("vung_xoa_mot");
      xoa.addEventListener("click", function () {
        vung.splice(i, 1);
        veLai();
      });

      li.appendChild(dauMuc);
      li.appendChild(toaDoGio);
      li.appendChild(gio);
      li.appendChild(xoa);
      dsVung.appendChild(li);
    });
  }

  function toaDo(ev) {
    var o = lop.getBoundingClientRect();
    if (!o.width || !o.height) return null;
    // Kep vao [0,1]: keo ra ngoai khung la chuyen binh thuong khi ve.
    return {
      x: Math.min(1, Math.max(0, (ev.clientX - o.left) / o.width)),
      y: Math.min(1, Math.max(0, (ev.clientY - o.top) / o.height))
    };
  }

  Array.prototype.forEach.call(
    document.querySelectorAll(".asv-vung-che-nut"), function (nut) {
      nut.addEventListener("click", function () {
        loaiDangVe = nut.getAttribute("data-loai");
        if (khung) khung.classList.add("asv-dang-ve");
        // ⚠️ Tam dung video: mot khung hinh dang chay la mot khung hinh khach
        //    khong the ngam dung vao.
        if (video && !video.paused) video.pause();
        chu(vungTt, t("vung_keo"));
      });
    });

  var dau = null;
  if (lop) {
    lop.addEventListener("pointerdown", function (ev) {
      if (!loaiDangVe) return;
      dau = toaDo(ev);
      if (dau) { lop.setPointerCapture(ev.pointerId); ev.preventDefault(); }
    });
    lop.addEventListener("pointerup", function (ev) {
      if (!loaiDangVe || !dau) return;
      var cuoi = toaDo(ev);
      // ⚠️ Giu loai TRUOC khi go che do ve. Doc no sau khi gan `null` la doc mot
      //    hop khong co loai — va `vung_che.chuan_hoa` se tu choi ca lo o may
      //    chu, tuc khach mat het vung minh vua ve ma khong hieu vi sao.
      var loai = loaiDangVe;
      loaiDangVe = null;
      if (khung) khung.classList.remove("asv-dang-ve");
      if (!cuoi) { dau = null; return; }

      var v = {
        loai: loai,
        y0: Math.min(dau.y, cuoi.y), y1: Math.max(dau.y, cuoi.y),
        x0: Math.min(dau.x, cuoi.x), x1: Math.max(dau.x, cuoi.x)
      };
      dau = null;
      // ⛔ Qua nho thi BO, khong "no ra cho vua". Mot lan click nham khong phai
      //    mot y dinh, va no van ton mot bo loc trong lan encode.
      if (v.y1 - v.y0 < CANH_TOI_THIEU || v.x1 - v.x0 < CANH_TOI_THIEU) {
        chu(vungTt, t("vung_qua_nho"));
        return;
      }
      vung.push(v);
      veLai();
    });
  }

  var nutXoa = document.getElementById("asv-vung-xoa");
  if (nutXoa) {
    nutXoa.addEventListener("click", function () { vung.pop(); veLai(); });
  }

  /* ── Vung che chi song o preset CAT ───────────────────────────────────── */
  /*
   * 🔴 Rang buoc VAT LY, khong phai lua chon: preset giu hinh phat `-c:v copy`,
   *    tuc byte hinh di thang tu nguon sang tep ra ma khong giai ma lan nao —
   *    khong co khung hinh nao ton tai trong bo nho de sua mot vung diem anh.
   *
   * ⛔ Bay cong cu cho ca hai preset la mot **false feature**: khach ve xong,
   *    thay vung trong "Cai dat da dung", roi nhan mot video khong che gi.
   *
   * ⭐ Va khi doi sang preset khong ho tro thi **xoa vung da ve** chu khong chi
   *    an nut di: giu lai mot mang toa do ma khong ai thi hanh la giu lai dung
   *    cai loi vua tranh — no van di theo form len may chu.
   */
  var nhomVung = document.getElementById("asv-nhom-vung");
  var chanVung = document.getElementById("asv-vung-chan");
  var thanhVung = document.querySelector(".asv-vung-thanh");

  /* `data-toi-da` do template phat — lay TU `vung_che.SO_VUNG_TOI_DA`, khong
     go tay mot so thu hai o day. Cung khuon voi `LG_TOI_DA` o `asv/logo.js`. */
  var VUNG_TOI_DA = nhomVung
    ? (parseInt(nhomVung.getAttribute("data-toi-da"), 10) || 12) : 12;

  /* ── Be mat cho `asv/de_xuat.js` (v4-be-mat-de-xuat) ──────────────────────
   *
   * 🔑 Mot khi khach bam "Nhan" tren mot de xuat cua `do_vung`, no phai vao
   *    ĐUNG mot cho — mang `vung` nay — de di ca duong sau: dong bo `#asv-vung`
   *    JSON, hien trong danh sach, sua duoc bang o so/nut Xoa o TREN, va di
   *    qua CUNG `vung_che.chuan_hoa` ma may chu dung. ⛔ Khong dung mot mang
   *    RIENG cho "vung da nhan" — hai mang la hai nguon chan ly se lech.
   */
  ASV.themVungDeXuat = function (v) {
    if (vung.length >= VUNG_TOI_DA) return false;
    vung.push({loai: v.loai, x0: v.x0, y0: v.y0, x1: v.x1, y1: v.y1});
    veLai();
    return true;
  };

  /* `tranh` cho `do_vung.do_dai_chu` (BAT BIEN 2 cua `do_vung.py`): cap
     `[y0, y1]` cua MOI vung khach da ve, bat ke loai — dai chu tu do khong
     duoc trung >= 50% len bat ky vung nao trong so nay. */
  ASV.layTranhVung = function () {
    return vung.map(function (v) { return [v.y0, v.y1]; });
  };

  function capNhatVungTheoPreset() {
    if (!nhomVung) return;
    var duoc = ASV.hopPreset(nhomVung);
    if (thanhVung) thanhVung.hidden = !duoc;
    if (chanVung) chanVung.hidden = duoc;
    if (!duoc) {
      loaiDangVe = null;
      if (khung) khung.classList.remove("asv-dang-ve");
      if (vung.length) { vung.length = 0; veLai(); }
    }
  }

  ASV.khiDoiPreset(capNhatVungTheoPreset);
  capNhatVungTheoPreset();

  /* Ti le khung da biet -> ve lai lop phu cho dung. */
  ASV.khiCoVideo(function () { veLai(); });
})();
