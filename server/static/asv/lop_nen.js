/* asv/lop_nen.js — BA LOP cua ban nen (B2 tach + B5 GUI, 25/09).
 *
 * Server tach ban nen lam ba lop demucs gom lai: "nhac" (drums+bass), "vfx"
 * (other — tieng dong/hieu ung), "giong" (vocals — LOI THOAI GOC). Moi lop co
 * mot cong tac bat/tat + mot gain 0..200% (khuon `tach_tieng.GAIN_NHO_NHAT/
 * GAIN_LON_NHAT`, mien lay TU `data-gain-min/max`, khong go so o day).
 *
 * ⛔ Am thanh khong cham diem anh, nen khoi nay KHONG an theo preset — cung
 *    ly do voi `asv/am_thanh.js`.
 *
 * ⛔ Ho so VANG MAT khi ca ba lop dang o MAC DINH (giong TAT, nhac+vfx BAT o
 *    100%): mot ho so day du gui o moi lan chay se lam ho so cua nhung lan
 *    khong dung tinh nang nay khac di ma khong vi ly do gi — dung dieu
 *    `cai_dat.KHOA_THUA` ton tai de tranh. May chu lam viec nay lan nua o
 *    `tach_tieng.tu_form_lop` (so voi `LOP_MAC_DINH`); o day chi la mot toi uu
 *    tranh gui JSON thua, khong phai nguon su that.
 */
(function () {
  "use strict";
  if (!window.ASV || !ASV.co) return;

  var nhom = document.getElementById("asv-nhom-lop");
  var oHidden = document.getElementById("asv-lop");
  if (!nhom || !oHidden) return;

  var MAC_DINH = {
    giong_bat: false, giong_gain: 1.0,
    nhac_bat: true, nhac_gain: 1.0,
    vfx_bat: true, vfx_gain: 1.0
  };

  var oNhacBat = document.getElementById("asv-lop-nhac-bat");
  var oNhacGain = document.getElementById("asv-lop-nhac-gain");
  var soNhac = document.getElementById("asv-lop-nhac-so");
  var oVfxBat = document.getElementById("asv-lop-vfx-bat");
  var oVfxGain = document.getElementById("asv-lop-vfx-gain");
  var soVfx = document.getElementById("asv-lop-vfx-so");
  var oGiongBat = document.getElementById("asv-lop-giong-bat");
  var oGiongGain = document.getElementById("asv-lop-giong-gain");
  var soGiong = document.getElementById("asv-lop-giong-so");

  function gain(o) {
    var v = parseFloat(o && o.value);
    /* Thanh truot ghi PHAN TRAM (0..200); ho so gui cho may chu la BIEN DO
     * TUYEN TINH (0,0..2,0) — khuon `tach_tieng.GAIN_NHO_NHAT/LON_NHAT`. */
    return isNaN(v) ? 1.0 : Math.round((v / 100) * 100) / 100;
  }

  function dongBo() {
    var nhacBat = !!(oNhacBat && oNhacBat.checked);
    var vfxBat = !!(oVfxBat && oVfxBat.checked);
    var giongBat = !!(oGiongBat && oGiongBat.checked);
    var nhacGain = gain(oNhacGain);
    var vfxGain = gain(oVfxGain);
    var giongGain = gain(oGiongGain);

    if (oNhacGain) oNhacGain.disabled = !nhacBat;
    if (oVfxGain) oVfxGain.disabled = !vfxBat;
    if (oGiongGain) oGiongGain.disabled = !giongBat;

    if (soNhac) soNhac.textContent = Math.round(nhacGain * 100) + "%";
    if (soVfx) soVfx.textContent = Math.round(vfxGain * 100) + "%";
    if (soGiong) soGiong.textContent = Math.round(giongGain * 100) + "%";

    var ho = {
      giong_bat: giongBat, giong_gain: giongGain,
      nhac_bat: nhacBat, nhac_gain: nhacGain,
      vfx_bat: vfxBat, vfx_gain: vfxGain
    };
    var bangMacDinh = Object.keys(MAC_DINH).every(function (k) {
      return ho[k] === MAC_DINH[k];
    });
    oHidden.value = bangMacDinh ? "" : JSON.stringify(ho);
  }

  [oNhacBat, oNhacGain, oVfxBat, oVfxGain, oGiongBat, oGiongGain]
    .forEach(function (o) {
      if (!o) return;
      o.addEventListener("input", dongBo);
      o.addEventListener("change", dongBo);
    });
  dongBo();
})();
