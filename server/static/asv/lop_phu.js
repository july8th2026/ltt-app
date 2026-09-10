/* asv/lop_phu.js — LOP PHU CHU.
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
(function () {
  "use strict";
  if (!window.ASV || !ASV.co) return;

  var t = ASV.t;
  var chu = ASV.chu;

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
    var duoc = ASV.hopPreset(nhomLp);
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

  ASV.khiDoiPreset(capNhatLopPhuTheoPreset);
  capNhatLopPhuTheoPreset();
})();
