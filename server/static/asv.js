/* asv.js — man Studio cua Auto Scan Video.
 *
 * Bon viec, va khong viec nao trong so do la "logic nghiep vu":
 *
 *   1. Xem truoc video khach vua chon        (URL.createObjectURL — khong tai len)
 *   2. Hoi may chu uoc gia theo do dai       (/uoc-tinh)
 *   3. Loc + nghe thu giong                  (loc tren the da co san)
 *   4. Ve vung che, ghi ra toa do CHUAN HOA  (0..1, khong pixel)
 *
 * ⛔ Khong tinh gia o day. `/uoc-tinh` la mot duong may chu co chu dinh: cong
 *    thuc gia la thu san pham, va mot ban thu hai trong JavaScript se troi khoi
 *    ban that ngay lan dau ai do sua mot con so.
 *
 * ⛔ Khong loc giong o day theo cach GIAU bot. Danh sach `<option>` da duoc may
 *    chu loc theo chu so huu; viec o day chi la an/hien nhung muc ay theo nhan.
 *
 * ⚠️ Toan bo tep chay sau `defer`, va moi truy van deu kiem `null` truoc khi
 *    dung. Man Studio la trang DUY NHAT nap tep nay, nhung mot trang khac nap
 *    nham thi no phai im lang chu khong duoc nem.
 */
(function () {
  "use strict";

  var form = document.getElementById("asv-form");
  if (!form) return;

  /* Chuoi hien cho khach — do TEMPLATE cung cap, khong go o day.
   * Xem khoi `#asv-chu` trong `asv_trang_chinh.html` va ly do o do. */
  var CHU = {};
  try {
    var oChu = document.getElementById("asv-chu");
    if (oChu) CHU = JSON.parse(oChu.textContent) || {};
  } catch (e) { CHU = {}; }
  /* 🔴 `%%` -> `%`, va day la mot lo hong CO SAN tim ra khi kiem trinh duyet o
   *    pha 12b, khong phai mot nhu cau moi.
   *
   *    Cac chuoi o `#asv-chu` viet theo quy uoc printf cua Python, nen mot dau
   *    phan tram THAT phai go doi: `"Đang tải video lên… %(pct)s%%"`. Ham nay
   *    truoc day chi thay cho tham so va **khong go doi lai**, nen khach doc
   *    "tải lên… 50%%". Ban dau toi tuong do la loi cua chuoi minh vua them; do
   *    lai thi `tai_dang` cua V5 dinh y het.
   *
   * ⚠️ Go doi SAU khi thay tham so: mot gia tri thay vao co the chua `%`, va
   *    go truoc se an vao chinh no.
   *
   * ⭐ Va thay TOAN CUC: `String.replace` voi mot chuoi chi doi **lan dau**, nen
   *    mot chuoi dung `%(x)s` hai lan se lang le giu nguyen lan thu hai.
   */
  function t(khoa, thay) {
    var s = CHU[khoa] || "";
    if (thay) {
      Object.keys(thay).forEach(function (k) {
        s = s.split("%(" + k + ")s").join(thay[k]);
      });
    }
    return s.split("%%").join("%");
  }

  var oTep = document.getElementById("asv-video");
  var video = document.getElementById("asv-xem");
  var khung = document.getElementById("asv-khung");
  var rong = document.getElementById("asv-rong");
  var lop = document.getElementById("asv-lop");
  var tenTep = document.getElementById("asv-tep-ten");
  var uocTien = document.getElementById("asv-uoc-tien");
  var uocGio = document.getElementById("asv-uoc-gio");
  var oVung = document.getElementById("asv-vung");
  var vungTt = document.getElementById("asv-vung-tt");
  var nutBatDau = document.getElementById("asv-batdau");

  var NS = "http://www.w3.org/2000/svg";
  var vung = [];          // toa do CHUAN HOA 0..1
  var loaiDangVe = null;  // null = khong o che do ve

  /* ── Tien ich ─────────────────────────────────────────────────────────── */

  function chu(el, s) { if (el) el.textContent = s; }

  function phutGiay(giay) {
    var g = Math.max(0, Math.round(giay));
    var p = Math.floor(g / 60);
    return p > 0 ? p + " " + t("phut") + " " + (g % 60) + " " + t("giay")
                 : g + " " + t("giay");
  }

  /* ── 1. Xem truoc ─────────────────────────────────────────────────────── */

  function moTep() {
    var f = oTep && oTep.files && oTep.files[0];
    if (!f) return;

    // ⭐ `createObjectURL` — tep KHONG di dau ca. Khach thay khung hinh ngay,
    //    truoc khi mot byte nao roi khoi may ho.
    video.src = URL.createObjectURL(f);
    video.hidden = false;
    video.controls = true;
    if (lop) lop.hidden = false;
    if (rong) rong.hidden = true;

    var mb = (f.size / (1024 * 1024)).toFixed(1);
    chu(tenTep, f.name + " · " + mb + " MB");

    // ⚠️ Kiem tran o PHIA CLIENT, truoc khi gui. May chu van kiem lai — day chi
    //    la de khach biet NGAY thay vi sau khi tai len xong mot tep 200 MB.
    var tran = parseInt(form.getAttribute("data-tran-mb") || "0", 10);
    if (tran > 0 && f.size > tran * 1024 * 1024) {
      chu(tenTep, f.name + " · " + t("vuot_tran", {mb: tran}));
      if (nutBatDau) nutBatDau.disabled = true;
    } else if (nutBatDau) {
      nutBatDau.disabled = false;
    }
  }

  if (oTep) oTep.addEventListener("change", moTep);

  /* ── 2. Uoc gia — hoi MAY CHU, khong tinh o day ───────────────────────── */

  if (video) {
    video.addEventListener("loadedmetadata", function () {
      var giay = video.duration;
      if (!isFinite(giay) || giay <= 0) return;
      /* ⚠️ `batCat` TRUOC `veLai`: no dat `thoiLuongVideo`, va danh sach vung
       *    doc bien do de dat `max` cho hai o gio. Nguoc thu tu thi lan ve dau
       *    tien cho ra hai o khong co tran — mot loi khong bao gio no o may nay
       *    (danh sach luc do dang rong), nhung se no ngay khi co ai goi `veLai`
       *    som hon. */
      batCat(giay);
      veLai();   // ti le khung da biet -> ve lai lop phu cho dung

      var duong = form.getAttribute("data-uoc");
      if (!duong) return;
      fetch(duong + "?giay=" + encodeURIComponent(giay), {
        credentials: "same-origin"
      }).then(function (r) {
        return r.ok ? r.json() : null;
      }).then(function (d) {
        if (!d) return;
        // ⭐ Hien mot KHOANG, va can tren la thu khach thuc su doi mat.
        chu(uocTien, "~" + d.credit_thap + "–" + d.credit_cao
                     + " " + t("credit"));
        chu(uocGio, t("khoang") + " " + phutGiay(d.thoi_gian_giay));
      }).catch(function () {
        /* ⛔ Nuot CO CHU DICH: uoc gia hong khong duoc chan khach bat dau.
           Ho van thay so giu cho that o trang chi tiet. */
      });
    });
  }

  /* ── 3b. Che do giong: cho CLIENT khop dung luat cua MAY CHU ──────────

     🔴 `routes.py:315` chi doi `giong_id` khi che do la USER_SELECTED. Nhung
        the `<select>` mang `required` **co dinh**, nen o che do AUTO_MATCH trinh
        duyet van cuong che mot truong ma may chu khong doi — hai ben noi hai
        luat khac nhau ve cung mot o.

     ⚠️ Hom nay no khong no, va do moi la ly do phai sua: danh sach giong luon
        co mot muc duoc chon san, nen phep cuong che khong bao gio chan ai. No la
        mot mau thuan **im lang**, se thanh loi that ngay khi co ai them mot muc
        rong vao dau danh sach.

     ⭐ Luat den tu `data-can-giong`, do template phat ra tu chinh
        `hop_dong_v4.CHE_DO_GIONG_TU_CHON`. Chep chuoi "USER_SELECTED" vao
        day se tao mot ban sao troi duoc, va troi im lang.

     ⭐ Khong dong `disabled` o day. Nhan cua AUTO_MATCH tu noi *"hien tai hay tu
        chon giong"* — tuc giong VAN duoc dung o che do do. Tat o chon se mau
        thuan voi chinh cau chu ay.
  */

  (function dongBoCheDoGiong() {
    var oS = document.getElementById("asv-giong");
    var ds = document.querySelectorAll("input[name=che_do_giong]");
    if (!oS || !ds.length) return;

    function ap() {
      var chon = document.querySelector("input[name=che_do_giong]:checked");
      oS.required = !chon || chon.dataset.canGiong === "1";
    }
    for (var i = 0; i < ds.length; i++) ds[i].addEventListener("change", ap);
    ap();
  })();

  /* ── 3. Loc + nghe thu giong ──────────────────────────────────────────── */

  var oGiong = document.getElementById("asv-giong");
  var locGioi = document.getElementById("asv-loc-gioi");
  var locVung = document.getElementById("asv-loc-vung");
  var locPhongCach = document.getElementById("asv-loc-phong-cach");
  var nutNghe = document.getElementById("asv-nghe-nut");
  var ttNghe = document.getElementById("asv-nghe-tt");
  var amNghe = document.getElementById("asv-nghe-am");

  function locGiong() {
    if (!oGiong) return;
    var g = locGioi ? locGioi.value : "";
    var v = locVung ? locVung.value : "";
    var pc = locPhongCach ? locPhongCach.value : "";
    var conLai = 0, dangChon = oGiong.value, hopLe = false;

    Array.prototype.forEach.call(oGiong.options, function (o) {
      // ⭐ Giong NHAN BAN cua khach khong co ba nhan. Chung KHONG bi loc mat khi
      //    khach chon mot nhan — an giong rieng cua ho di la dieu ho khong
      //    doi, va ho khong co cach nao doan la vi sao.
      var laRieng = !o.getAttribute("data-gioi");
      var khop = laRieng
        || ((!g || o.getAttribute("data-gioi") === g)
            && (!v || o.getAttribute("data-vung") === v)
            && (!pc || o.getAttribute("data-phong-cach") === pc));
      o.hidden = !khop;
      if (khop) { conLai++; if (o.value === dangChon) hopLe = true; }
    });

    // ⚠️ Giong dang chon bi loc mat thi phai chon lai — mot `<select>` giu mot
    //    `value` dang `hidden` van GUI gia tri do di.
    if (!hopLe && conLai > 0) {
      for (var i = 0; i < oGiong.options.length; i++) {
        if (!oGiong.options[i].hidden) { oGiong.selectedIndex = i; break; }
      }
    }
    capNhatNghe();
  }

  function capNhatNghe() {
    if (!oGiong || !nutNghe) return;
    var o = oGiong.options[oGiong.selectedIndex];
    var duong = o ? o.getAttribute("data-nghe") : null;
    // ⭐ Khong co tep thi NOI RA. Mot nut bam duoc ma khong keu la thu te nhat —
    //    khach khong biet la giong hong hay may ho hong.
    nutNghe.disabled = !duong;
    chu(ttNghe, duong ? "" : t("nghe_chua_co"));
  }

  if (locGioi) locGioi.addEventListener("change", locGiong);
  if (locVung) locVung.addEventListener("change", locGiong);
  if (locPhongCach) locPhongCach.addEventListener("change", locGiong);
  if (oGiong) oGiong.addEventListener("change", capNhatNghe);
  if (nutNghe) {
    nutNghe.addEventListener("click", function () {
      var o = oGiong.options[oGiong.selectedIndex];
      var duong = o ? o.getAttribute("data-nghe") : null;
      if (!duong || !amNghe) return;
      amNghe.src = duong;
      amNghe.play().catch(function () {
        chu(ttNghe, t("nghe_hong"));
      });
    });
  }
  capNhatNghe();

  /* ── 4. Trinh sua vung ────────────────────────────────────────────────── */
  /*
   * 🔑 Toa do o day la PHAN SO 0..1 tu dau den cuoi, khong bao gio pixel.
   *    `viewBox="0 0 1 1"` cua SVG lam viec doi don vi bien mat: mot hop trong
   *    SVG CHINH LA hop se duoc gui len. Khong co phep nhan nao de lam sai.
   *
   * ⛔ Va khong co phep "sua hoc": hop ve nguoc hay qua nho bi BO tai cho, dung
   *    nhu `vung_che.chuan_hoa` se lam o may chu. Hai noi cung mot luat.
   */

  var CANH_TOI_THIEU = 0.01;   // khop `vung_che.CANH_TOI_THIEU`

  function veLai() {
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

  function pt(x) { return Math.round(x * 100); }

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
    if (thoiLuongVideo > 0) i.max = String(thoiLuongVideo);
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

  function veDanhSachVung() {
    if (!dsVung) return;
    while (dsVung.firstChild) dsVung.removeChild(dsVung.firstChild);
    vung.forEach(function (v, i) {
      var li = document.createElement("li");
      li.className = "asv-vung-muc";

      var dau = document.createElement("div");
      dau.className = "asv-vung-dau";
      var ten = document.createElement("strong");
      ten.textContent = t("vung_loai_" + v.loai) || v.loai;
      var oVt = document.createElement("span");
      oVt.className = "asv-ghi-chu";
      oVt.textContent = t("vung_vi_tri", {
        x: pt(v.x0), x2: pt(v.x1), y: pt(v.y0), y2: pt(v.y1)
      });
      dau.appendChild(ten);
      dau.appendChild(oVt);

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

      li.appendChild(dau);
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

  function capNhatVungTheoPreset() {
    if (!nhomVung) return;
    var can = nhomVung.getAttribute("data-preset-can") || "";
    var chon = form.querySelector('input[name="preset"]:checked');
    var duoc = !!chon && chon.value === can;

    if (thanhVung) thanhVung.hidden = !duoc;
    if (chanVung) chanVung.hidden = duoc;
    if (!duoc) {
      loaiDangVe = null;
      if (khung) khung.classList.remove("asv-dang-ve");
      if (vung.length) { vung.length = 0; veLai(); }
    }
  }

  Array.prototype.forEach.call(
    form.querySelectorAll('input[name="preset"]'), function (o) {
      o.addEventListener("change", capNhatVungTheoPreset);
    });
  capNhatVungTheoPreset();

  /* ── 4b. Cat dau/cuoi ─────────────────────────────────────────────────
   *
   * ⭐ Khach nhap GIAY, may chu nhan PHAN SO. Doi don vi xay ra o day va chi o
   *    day, vi day la noi duy nhat phia khach biet `video.duration`.
   *
   * ⛔ **Khong kep ve bien, khong dao lai.** `cat_dau_cuoi` L2 noi thang: mot
   *    cua so bi "sua ho" thanh hop le se duoc thi hanh, tuc ta cat mot doan
   *    khach khong chon va khach khong co cach nao biet. Nen o day ta gui
   *    NGUYEN thu khach nhap va de may chu tu choi — mot bo luat, mot cho phat
   *    bieu. Dong chu duoi o chi la mot loi nhac som, khong phai mot phep kiem
   *    thu hai.
   */
  var nhomCat = document.getElementById("asv-nhom-cat");
  var chanCat = document.getElementById("asv-cat-chan");
  var oCatTu = document.getElementById("asv-cat-tu");
  var oCatDen = document.getElementById("asv-cat-den");
  var oCat = document.getElementById("asv-cat");
  var ttCat = document.getElementById("asv-cat-tt");
  var nutCatXoa = document.getElementById("asv-cat-xoa");
  var oCatO = document.querySelector(".asv-cat-o");
  /* Cung hang so voi `cat_dau_cuoi.TOI_THIEU`. Hai ban cua mot nguong la hai
     ban se lech — nhung ban o day chi de NOI SOM, con ban cuong che nam o may
     chu, nen lech chi lam loi toi muon hon chu khong lam sai ket qua. */
  var TOI_THIEU_CAT = 0.02;
  /* Do dai video, doc mot lan o `loadedmetadata`. Dung CHUNG: phan CAT
     doi giay -> phan so, con danh sach VUNG dat tran cho hai o gio. */
  var thoiLuongVideo = 0;

  /* ⭐ Hai o mac dinh `disabled`, va chi mo khi da biet thoi luong. Mot o nhan
   *    GIAY trong khi chua ai biet video dai bao nhieu la mot o khong the doi
   *    ra phan so — khach go vao do se gui len mot con so vo nghia. */
  function batCat(giay) {
    thoiLuongVideo = giay;
    if (oCatTu) { oCatTu.disabled = false; oCatTu.max = String(giay); }
    if (oCatDen) {
      oCatDen.disabled = false;
      oCatDen.max = String(giay);
      oCatDen.placeholder = giay.toFixed(1);
    }
    tinhCat();
  }

  function xoaCat() {
    if (oCatTu) oCatTu.value = "";
    if (oCatDen) oCatDen.value = "";
    if (oCat) oCat.value = "";
    chu(ttCat, t("cat_ca_video"));
  }

  function tinhCat() {
    if (!oCat) return;
    if (!(thoiLuongVideo > 0)) { oCat.value = ""; return; }
    var coA = oCatTu && oCatTu.value !== "";
    var coB = oCatDen && oCatDen.value !== "";
    if (!coA && !coB) { oCat.value = ""; chu(ttCat, t("cat_ca_video")); return; }

    var a = coA ? parseFloat(oCatTu.value) : 0;
    var b = coB ? parseFloat(oCatDen.value) : thoiLuongVideo;
    if (!isFinite(a) || !isFinite(b)) {
      oCat.value = ""; chu(ttCat, t("cat_khong_doc_duoc")); return;
    }
    var fa = a / thoiLuongVideo, fb = b / thoiLuongVideo;
    /* L4: khong thu hep gi thi khong gui gi. */
    if (fa <= 0 && fb >= 1) { oCat.value = ""; chu(ttCat, t("cat_ca_video")); return; }

    oCat.value = JSON.stringify([fa, fb]);
    if (!(fa >= 0 && fa < fb && fb <= 1)) { chu(ttCat, t("cat_ngoai_khoang")); return; }
    if (fb - fa < TOI_THIEU_CAT) { chu(ttCat, t("cat_qua_ngan")); return; }
    chu(ttCat, t("cat_con_lai", { giay: phutGiay(b - a) }));
  }

  if (oCatTu) oCatTu.addEventListener("input", tinhCat);
  if (oCatDen) oCatDen.addEventListener("input", tinhCat);
  if (nutCatXoa) nutCatXoa.addEventListener("click", xoaCat);

  /* ⛔ Doi preset ma chi AN o nhap di la giu lai dung cai loi vua tranh: gia
   *    tri van di theo form len may chu. Xoa han — cung luat voi vung che. */
  function capNhatCatTheoPreset() {
    if (!nhomCat) return;
    var can = nhomCat.getAttribute("data-preset-can") || "";
    var chon = form.querySelector('input[name="preset"]:checked');
    var duoc = !!chon && chon.value === can;
    if (oCatO) oCatO.hidden = !duoc;
    if (chanCat) chanCat.hidden = duoc;
    if (!duoc) xoaCat();
  }

  Array.prototype.forEach.call(
    form.querySelectorAll('input[name="preset"]'), function (o) {
      o.addEventListener("change", capNhatCatTheoPreset);
    });
  capNhatCatTheoPreset();

  /* ── 4c. Lop phu chu ──────────────────────────────────────────────────
   *
   * 🔴 **Day KHONG phai o dat phu de.** `apps/autosubvideo` so huu viec do, va
   *    ranh gioi duoc giu bang CO HOC chu khong bang mot cau ghi chu:
   *
   *      · moi lop la MOT dong — `input` mot dong, va may chu TU CHOI ky tu
   *        xuong dong thay vi loc bo no
   *      · toi da `data-toi-da` lop, doc tu `lop_phu.SO_LOP_PHU_TOI_DA`
   *
   * ⭐ Khach nghi bang PHAN TRAM, may chu nhan PHAN SO 0..1 (`lop_phu` L1). Doi
   *    don vi xay ra o day va chi o day — mot con so tinh bang pixel tro thanh
   *    sai ngay khi ban xem truoc co do phan giai khac ban goc.
   *
   * ⚠️ Mot dong CHUA go chu thi khong duoc gui: may chu tu choi chuoi rong, va
   *    mot o trong la mot dong khach chua viet xong chu khong phai mot y dinh.
   *    Nhung viec bo qua no duoc NOI RA o dong trang thai — bo im lang la dung
   *    cai loi ma `vung_che` L2 ton tai de tranh.
   */
  var nhomLp = document.getElementById("asv-nhom-lop-phu");
  var dsLp = document.getElementById("asv-lop-phu-ds");
  var oLp = document.getElementById("asv-lop-phu");
  var ttLp = document.getElementById("asv-lop-phu-tt");
  var chanLp = document.getElementById("asv-lop-phu-chan");
  var nutLpThem = document.getElementById("asv-lop-phu-them");
  var thanhLp = nhomLp ? nhomLp.querySelector(".asv-vung-thanh") : null;
  var lopPhu = [];
  var LP_TOI_DA = nhomLp
    ? (parseInt(nhomLp.getAttribute("data-toi-da"), 10) || 3) : 3;
  var LP_MAU = ["trang", "den", "vang"];

  function dongBoLopPhu() {
    var gui = lopPhu.filter(function (l) {
      return String(l.chu || "").trim() !== "";
    });
    if (oLp) oLp.value = gui.length ? JSON.stringify(gui) : "";
    if (!lopPhu.length) { chu(ttLp, t("lp_chua_co")); return; }
    if (gui.length < lopPhu.length) { chu(ttLp, t("lp_trong")); return; }
    chu(ttLp, t("lp_dem", { so: gui.length }));
  }

  function oLpSo(l, khoa, nhan, thap, cao) {
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
    i.addEventListener("input", function () {
      var x = parseFloat(i.value);
      /* ⛔ Khong kep ve bien o day. Mot gia tri ngoai khoang phai di len va bi
       *    may chu TU CHOI — `lop_phu._so` la cho phat bieu duy nhat cua luat
       *    ay. Kep o giao dien la sua ho mot y dinh cua khach. */
      if (isFinite(x)) { l[khoa] = x / 100; dongBoLopPhu(); }
    });
    lb.appendChild(s);
    lb.appendChild(i);
    return lb;
  }

  function veDanhSachLopPhu() {
    if (!dsLp) return;
    while (dsLp.firstChild) dsLp.removeChild(dsLp.firstChild);
    lopPhu.forEach(function (l, i) {
      var li = document.createElement("li");
      li.className = "asv-vung-muc";

      var lbChu = document.createElement("label");
      lbChu.className = "asv-lp-chu";
      var sChu = document.createElement("span");
      sChu.textContent = t("lp_chu");
      var iChu = document.createElement("input");
      iChu.type = "text";
      /* ⛔ `type="text"` chu khong `textarea`: mot o nhieu dong la mot loi moi
       *    dan phu de vao, va ranh gioi phai la CO HOC. */
      iChu.maxLength = 80;
      iChu.placeholder = t("lp_chu_goi_y");
      iChu.value = l.chu || "";
      iChu.addEventListener("input", function () {
        l.chu = iChu.value;
        dongBoLopPhu();
      });
      lbChu.appendChild(sChu);
      lbChu.appendChild(iChu);

      var so = document.createElement("div");
      /* ⚠️ `asv-lp-o` ngoai `asv-vung-gio-o`: hang nay co BON o dieu khien,
         con hang cua vung che chi co hai. Do that o 375px: bon o chia nhau
         234px con **40px moi cai** — mot o so 40px khong hien noi "100" va
         mot o chon 40px khong hien noi mot ten mau. Khong tran ngang, nen
         khong phep kiem nao thay; chi trinh duyet thay. */
      so.className = "asv-vung-gio-o asv-lp-o";
      so.appendChild(oLpSo(l, "x", t("lp_ngang"), 0, 100));
      so.appendChild(oLpSo(l, "y", t("lp_doc"), 0, 100));
      so.appendChild(oLpSo(l, "co_chu", t("lp_co_chu"), 2, 25));

      var lbMau = document.createElement("label");
      lbMau.className = "asv-vung-gio";
      var sMau = document.createElement("span");
      sMau.textContent = t("lp_mau");
      var sel = document.createElement("select");
      LP_MAU.forEach(function (m) {
        var op = document.createElement("option");
        op.value = m;
        op.textContent = t("lp_mau_" + m) || m;
        if (l.mau === m) op.selected = true;
        sel.appendChild(op);
      });
      sel.addEventListener("change", function () {
        l.mau = sel.value;
        dongBoLopPhu();
      });
      lbMau.appendChild(sMau);
      lbMau.appendChild(sel);
      so.appendChild(lbMau);

      var lbVien = document.createElement("label");
      lbVien.className = "asv-vung-gio asv-lp-vien";
      var iVien = document.createElement("input");
      iVien.type = "checkbox";
      iVien.checked = l.vien !== false;
      iVien.addEventListener("change", function () {
        l.vien = iVien.checked;
        dongBoLopPhu();
      });
      var sVien = document.createElement("span");
      sVien.textContent = t("lp_vien");
      lbVien.appendChild(iVien);
      lbVien.appendChild(sVien);
      so.appendChild(lbVien);

      var xoa = document.createElement("button");
      xoa.type = "button";
      xoa.className = "btn ghost";
      xoa.textContent = t("lp_xoa_mot");
      xoa.addEventListener("click", function () {
        lopPhu.splice(i, 1);
        veDanhSachLopPhu();
        dongBoLopPhu();
      });

      li.appendChild(lbChu);
      li.appendChild(so);
      li.appendChild(xoa);
      dsLp.appendChild(li);
    });
  }

  if (nutLpThem) {
    nutLpThem.addEventListener("click", function () {
      if (lopPhu.length >= LP_TOI_DA) {
        chu(ttLp, t("lp_het_cho", { n: LP_TOI_DA }));
        return;
      }
      /* Mac dinh: goc duoi ben trai, co chu 6% chieu cao, chu trang co vien —
         cung mac dinh voi `lop_phu.CO_CHU_MAC_DINH` / `MAU_MAC_DINH`. */
      lopPhu.push({ chu: "", x: 0.08, y: 0.80, co_chu: 0.06,
                    mau: "trang", vien: true });
      veDanhSachLopPhu();
      dongBoLopPhu();
    });
  }

  /* ⛔ Cung luat voi vung che va cat: doi preset ma chi AN di la giu lai dung
   *    cai loi vua tranh — gia tri van di theo form len may chu. */
  function capNhatLopPhuTheoPreset() {
    if (!nhomLp) return;
    var can = nhomLp.getAttribute("data-preset-can") || "";
    var chon = form.querySelector('input[name="preset"]:checked');
    var duoc = !!chon && chon.value === can;
    if (thanhLp) thanhLp.hidden = !duoc;
    if (dsLp) dsLp.hidden = !duoc;
    if (chanLp) chanLp.hidden = duoc;
    if (!duoc && lopPhu.length) {
      lopPhu.length = 0;
      veDanhSachLopPhu();
    }
    if (!duoc) { if (oLp) oLp.value = ""; }
    dongBoLopPhu();
  }

  Array.prototype.forEach.call(
    form.querySelectorAll('input[name="preset"]'), function (o) {
      o.addEventListener("change", capNhatLopPhuTheoPreset);
    });
  capNhatLopPhuTheoPreset();

  /* ── 5. Tai len BEN VUNG: trinh duyet -> kho, khong qua may chu ────────── */
  /*
   * 🔑 Day la thu go bo tran 90 MB. Tran do ton tai vi Cloudflare cat o 100 MB
   *    **tren duong vao may chu** — mot duong ma tep khong con di khi ta PUT
   *    thang len kho.
   *
   * Ba buoc: xin ve (`/ve`) -> PUT tep -> nop form kem `upload_id`.
   *
   * ⛔ **Phai TAT o chon tep truoc khi nop.** `routes.tao` uu tien `upload_id`
   *    va tra ve truoc khi cham toi `video` — nhung trinh duyet thi **da gui
   *    ca than multipart roi**. Tuc tep se di len HAI LAN, va lan thu hai dam
   *    thang vao dung cai tran ta vua tranh. `disabled` chu khong `value=""`:
   *    o nay co `required`, va mot o rong nhung con `required` chan ca form.
   *
   * ⚠️ Hong o BAT KY buoc nao deu lui ve duong multipart, khong bao loi cho
   *    khach. Duong multipart van chay (duoi 90 MB), nen mot lan xin ve that
   *    bai khong duoc bien thanh mot lan chay khong xay ra.
   */
  var oVe = document.getElementById("asv-ve");
  var oUploadId = document.getElementById("asv-upload-id");
  var khoiTai = document.getElementById("asv-tai");
  var thanhTai = document.getElementById("asv-tai-thanh");
  var ttTai = document.getElementById("asv-tai-tt");

  function datTienDo(pct) {
    if (!khoiTai) return;
    khoiTai.hidden = false;
    var i = thanhTai && thanhTai.querySelector("i");
    if (i) i.style.width = pct + "%";
    if (thanhTai) thanhTai.setAttribute("aria-valuenow", String(pct));
    chu(ttTai, t("tai_dang", {pct: pct}));
  }

  function benVungDuocKhong(f) {
    if (!oVe || !f) return false;
    // ⚠️ Duong ben vung nhan IT kieu hon o chon tep (`KIEU_VIDEO_HOP_LE` khong
    //    co `x-matroska`/`webm`). Kieu ngoai danh sach -> lui ve multipart NGAY,
    //    dung xin mot cai ve chac chan bi tu choi.
    var duoc = (oVe.getAttribute("data-kieu-ben-vung") || "").split(",");
    if (duoc.indexOf(f.type) < 0) return false;
    var tran = parseInt(oVe.getAttribute("data-tran-ben-vung") || "0", 10);
    return !(tran > 0 && f.size > tran * 1024 * 1024);
  }

  function xinVe(f) {
    var d = new FormData();
    d.append("csrf_token", form.querySelector('[name="csrf_token"]').value);
    d.append("ten_tep", f.name);
    d.append("kieu", f.type);
    d.append("co", String(f.size));
    return fetch(oVe.getAttribute("data-url"), {
      method: "POST", body: d, credentials: "same-origin"
    }).then(function (r) { return r.ok ? r.json() : null; });
  }

  function dayLen(ve, f) {
    // XHR chu khong `fetch`: chi XHR bao duoc tien do TAI LEN. Voi mot tep
    // hang tram MB, mot thanh tien do khong phai trang tri — khong co no thi
    // trang dung im vai phut va khach tuong may treo.
    return new Promise(function (ok, hong) {
      var x = new XMLHttpRequest();
      x.open(ve.method || "PUT", ve.url, true);
      Object.keys(ve.headers || {}).forEach(function (k) {
        x.setRequestHeader(k, ve.headers[k]);
      });
      x.upload.onprogress = function (e) {
        if (e.lengthComputable) {
          datTienDo(Math.round(e.loaded * 100 / e.total));
        }
      };
      x.onload = function () {
        (x.status >= 200 && x.status < 300) ? ok() : hong(x.status);
      };
      x.onerror = function () { hong(0); };
      x.send(f);
    });
  }

  var dangTai = false;

  form.addEventListener("submit", function (ev) {
    var f = oTep && oTep.files && oTep.files[0];

    // 🔴 Loi RE NHAT trong ban audit, va la loi DUY NHAT co the tao ra hai lan
    //    tru tien cho mot y dinh: nut khong disable, va trang dung im.
    function khoaNut() {
      if (!nutBatDau) return;
      nutBatDau.disabled = true;
      nutBatDau.classList.add("asv-dang-gui");
      chu(nutBatDau, t("dang_gui"));
    }

    // Da tai xong roi (lan nop thu hai sau khi PUT) -> di tiep binh thuong.
    if (dangTai || !f || (oUploadId && oUploadId.value)) {
      khoaNut();
      return;
    }
    if (!benVungDuocKhong(f)) {
      khoaNut();                 // lui ve multipart — duong cu, van chay
      return;
    }

    ev.preventDefault();
    dangTai = true;
    khoaNut();
    datTienDo(0);

    xinVe(f).then(function (ve) {
      // `{"mode":"local"}` = kho khong cap presigned duoc (LocalStorage tren
      // may phat trien va trong bo test). Khong phai loi — lui ve multipart.
      if (!ve || ve.mode !== "direct" || !ve.url) {
        throw new Error("khong-co-ve");
      }
      return dayLen(ve, f).then(function () {
        oUploadId.value = ve.upload_id;
        // ⛔ TAT o chon tep: xem ghi chu dai o dau muc 5.
        oTep.disabled = true;
        chu(ttTai, t("tai_xong"));
        form.submit();
      });
    }).catch(function () {
      // Lui ve multipart. Khong bao loi: duong cu van chay duoi 90 MB, va mot
      // lan xin ve hong khong duoc bien thanh mot lan chay khong xay ra.
      dangTai = false;
      if (khoiTai) khoiTai.hidden = true;
      if (oUploadId) oUploadId.value = "";
      form.submit();
    });
  });
})();
