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

  /* ── Loc + nghe thu giong ─────────────────────────────────────────────── */

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
})();
