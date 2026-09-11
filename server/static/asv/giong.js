/* asv/giong.js — o GIONG: khop luat `required` voi may chu, loc, nghe thu.
 *
 * ⛔ Khong loc giong o day theo cach GIAU bot. Danh sach `<option>` da duoc may
 *    chu loc theo chu so huu; viec o day chi la an/hien nhung muc ay theo nhan.
 */
(function () {
  "use strict";
  if (!window.ASV || !ASV.co) return;

  var t = ASV.t;
  var chu = ASV.chu;

  /* ── Che do giong: cho CLIENT khop dung luat cua MAY CHU ──────────────────
   *
   * 🔴 `routes.py` chi doi `giong_id` khi che do la USER_SELECTED. Nhung the
   *    `<select>` mang `required` **co dinh**, nen o che do AUTO_MATCH trinh
   *    duyet van cuong che mot truong ma may chu khong doi — hai ben noi hai
   *    luat khac nhau ve cung mot o.
   *
   * ⚠️ Hom nay no khong no, va do moi la ly do phai sua: danh sach giong luon
   *    co mot muc duoc chon san, nen phep cuong che khong bao gio chan ai. No la
   *    mot mau thuan **im lang**, se thanh loi that ngay khi co ai them mot muc
   *    rong vao dau danh sach.
   *
   * ⭐ Luat den tu `data-can-giong`, do template phat ra tu chinh
   *    `hop_dong_v4.CHE_DO_GIONG_TU_CHON`. Chep chuoi "USER_SELECTED" vao
   *    day se tao mot ban sao troi duoc, va troi im lang.
   *
   * ⭐ Khong dong `disabled` o day. Nhan cua AUTO_MATCH tu noi *"hien tai hay tu
   *    chon giong"* — tuc giong VAN duoc dung o che do do. Tat o chon se mau
   *    thuan voi chinh cau chu ay.
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

  /* ── Loc + tim + nguon + nghe thu giong (V6 pha 18) ─────────────────── */

  var oGiong = document.getElementById("asv-giong");
  var locGioi = document.getElementById("asv-loc-gioi");
  var locVung = document.getElementById("asv-loc-vung");
  var locPhongCach = document.getElementById("asv-loc-phong-cach");
  var oTim = document.getElementById("asv-tim-giong");
  var nutNguon = document.querySelectorAll("[data-nguon-giong]");
  var nutLamMoi = document.getElementById("asv-giong-lam-moi");
  var ttGiong = document.getElementById("asv-giong-tt");
  var nutNghe = document.getElementById("asv-nghe-nut");
  var ttNghe = document.getElementById("asv-nghe-tt");
  var amNghe = document.getElementById("asv-nghe-am");
  var nguon = "";

  /* Tim KHONG DAU: khach go "minh duc" phai thay "Minh Đức". `đ` khong tach
   * duoc bang NFD nen doi rieng. */
  function khongDau(s) {
    return String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "")
      .replace(/đ/g, "d").replace(/Đ/g, "D").toLowerCase().trim();
  }

  function laRieng(o) { return o.getAttribute("data-nguon") === "rieng"; }

  function locGiong() {
    if (!oGiong) return;
    var g = locGioi ? locGioi.value : "";
    var v = locVung ? locVung.value : "";
    var pc = locPhongCach ? locPhongCach.value : "";
    var tim = khongDau(oTim ? oTim.value : "");
    var conLai = 0, dangChon = oGiong.value, hopLe = false;
    var dem = { rieng: 0, mau: 0 };

    Array.prototype.forEach.call(oGiong.options, function (o) {
      var rieng = laRieng(o);
      dem[rieng ? "rieng" : "mau"]++;
      // ⭐ Giong NHAN BAN cua khach khong co ba nhan. Chung KHONG bi loc mat khi
      //    khach chon mot nhan — an giong rieng cua ho di la dieu ho khong
      //    doi, va ho khong co cach nao doan la vi sao. Tab "Giong mau" thi
      //    an chung: do la dieu khach VUA yeu cau.
      var khop = (!nguon || (nguon === "rieng") === rieng)
        && (!tim || khongDau(o.getAttribute("data-ten") || o.text).indexOf(tim) >= 0)
        && (rieng
            || ((!g || o.getAttribute("data-gioi") === g)
                && (!v || o.getAttribute("data-vung") === v)
                && (!pc || o.getAttribute("data-phong-cach") === pc)));
      o.hidden = !khop;
      if (khop) { conLai++; if (o.value === dangChon) hopLe = true; }
    });

    Array.prototype.forEach.call(nutNguon, function (n) {
      var k = n.getAttribute("data-nguon-giong");
      var so = n.querySelector("[data-dem]");
      if (so && k) so.textContent = "(" + dem[k] + ")";
    });

    // ⚠️ Giong dang chon bi loc mat thi phai chon lai — mot `<select>` giu mot
    //    `value` dang `hidden` van GUI gia tri do di.
    if (!hopLe && conLai > 0) {
      for (var i = 0; i < oGiong.options.length; i++) {
        if (!oGiong.options[i].hidden) { oGiong.selectedIndex = i; break; }
      }
    }
    // 🔴 **Khong con giong nao khop thi CHAN gui.** Truoc pha 18 nhanh nay khong
    //    lam gi: giong dang chon — da bi an — van nam trong `value` va van di
    //    len may chu. Khach loc "Nu · Mien Nam", thay danh sach rong, bam Gui, va
    //    nhan mot video doc bang giong NAM ho da loc bo.
    // ⛔ Khong them mot `<option value="">` de chon: `test_447` cam o giong co
    //    muc rong — do la duong "Giong mac dinh" quay lai.
    var rong = conLai === 0;
    oGiong.setCustomValidity(rong ? t("giong_khong_khop") : "");
    chu(ttGiong, rong ? t("giong_khong_khop") : "");
    capNhatNghe();
  }

  function capNhatNghe() {
    if (!oGiong || !nutNghe) return;
    var o = oGiong.options[oGiong.selectedIndex];
    var duong = o && !o.hidden ? o.getAttribute("data-nghe") : null;
    // ⭐ Khong co tep thi NOI RA. Mot nut bam duoc ma khong keu la thu te nhat —
    //    khach khong biet la giong hong hay may ho hong.
    nutNghe.disabled = !duong;
    chu(ttNghe, duong || !o ? "" : t("nghe_chua_co"));
  }

  /* ── Lam moi danh sach: catalog SONG, khong phai anh chup luc nap trang ───
   *
   * 🔑 Khach nhan ban giong o LTT VOICE (tab khac) roi quay lai. Truoc pha 18
   *    giong moi chi hien sau khi TAI LAI TRANG — tuc mat het video da chon va
   *    moi o da chinh. Nay: bam "Lam moi", hoac tu lam khi tab duoc nhin lai.
   *
   * ⛔ Danh sach den tu `routes.danh_muc_giong` — da loc theo CHU SO HUU o may
   *    chu. Khong bao gio ghep them giong tu nguon nao khac o day.
   */
  var lanCuoi = 0;

  function dungMuc(g) {
    var o = document.createElement("option");
    o.value = g.ma;
    o.setAttribute("data-ten", g.ten);
    o.setAttribute("data-nguon", g.la_mau ? "mau" : "rieng");
    o.setAttribute("data-gioi", g.gioi || "");
    o.setAttribute("data-vung", g.vung || "");
    o.setAttribute("data-phong-cach", g.phong_cach || "");
    if (g.duong_nghe) o.setAttribute("data-nghe", g.duong_nghe);
    o.textContent = g.duong_nghe ? g.ten : g.ten + " · " + t("giong_chua_mau");
    return o;
  }

  function lamMoi(imLang) {
    if (!oGiong || !nutLamMoi) return;
    lanCuoi = Date.now();
    var dangChon = oGiong.value;
    fetch(nutLamMoi.getAttribute("data-url"), { credentials: "same-origin" })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (d) {
        var ds = (d && d.giong) || [];
        // ⛔ Danh sach RONG tu may chu thi GIU danh sach cu: mot lan tra loi
        //    rong (kho giong dang khoi dong) khong duoc xoa sach o chon.
        if (!ds.length) throw new Error("rong");
        oGiong.textContent = "";
        ds.forEach(function (g) { oGiong.appendChild(dungMuc(g)); });
        if (ds.some(function (g) { return g.ma === dangChon; })) oGiong.value = dangChon;
        locGiong();
        if (!imLang && !oGiong.validationMessage) {
          chu(ttGiong, t("giong_da_lam_moi", { so: ds.length }));
        }
      })
      .catch(function () { if (!imLang) chu(ttGiong, t("giong_lam_moi_hong")); });
  }

  if (locGioi) locGioi.addEventListener("change", locGiong);
  if (locVung) locVung.addEventListener("change", locGiong);
  if (locPhongCach) locPhongCach.addEventListener("change", locGiong);
  if (oTim) oTim.addEventListener("input", locGiong);
  Array.prototype.forEach.call(nutNguon, function (n) {
    n.addEventListener("click", function () {
      nguon = n.getAttribute("data-nguon-giong") || "";
      Array.prototype.forEach.call(nutNguon, function (m) {
        var bat = m === n;
        m.setAttribute("aria-pressed", bat ? "true" : "false");
        m.classList.toggle("ghost", !bat);
      });
      locGiong();
    });
  });
  if (nutLamMoi) nutLamMoi.addEventListener("click", function () { lamMoi(false); });
  // Tu lam moi khi tab duoc nhin lai — toi da mot lan moi 30 giay.
  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "visible" && Date.now() - lanCuoi > 30000) lamMoi(true);
  });
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
  locGiong();
})();
