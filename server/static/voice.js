/* voice.js — hanh vi dung chung cua LTT Voice Studio.
 *
 * ⭐ MOT TEP CHO CA SAU MAN, khong mot tep moi trang. Sau man deu chep ma giong,
 *    deu theo doi mot job dang chay — va nhung thu do viet lai sau lan la sau
 *    ban se lech nhau.
 *
 * ⭐ Tang cuong dan (progressive enhancement): khong co JS thi trang van doc va
 *    dung duoc, chi mat vai tien nghi. Khong phu thuoc thu vien nao — CSP cua
 *    nen tang chan CDN ngoai.
 *
 * ⚠️ PHAI dinh `?v={{ asset_ver }}` o cho nap tep nay. Static di qua Cloudflare
 *    co TTL; doi tep ma URL khong doi thi khach nhan ban cu toi khi het TTL.
 *    CLAUDE.md quy tac 6 — da dinh that mot lan voi `ltt.css` (4 gio).
 *
 * ⛔ TEP NAY CHI CHUA THU DANG CO NGUOI DUNG. Khong them san ham cho man chua
 *    xay: ma khong ai goi la ma khong ai kiem, va no se lech khoi cho no phuc vu
 *    truoc khi cho do kip ra doi. Dem ky tu, ve song am va theo doi job se vao
 *    day o P2 — cung luc man Studio that su goi chung.
 */
(function () {
  "use strict";

  /* ── Chep ma giong ────────────────────────────────────────────────────────
   *
   * 🔴 `voice_id` la hop dong dai han: `tables.py` cam ket no khong bao gio doi,
   *    ke ca khi len engine moi. Khach dan no vao ma nguon cua ho. Chep hut mot
   *    ky tu thi loi hien ra o tan luc goi API duoi dang "khong tim thay giong"
   *    — mot thong diep tro sai cho hoan toan.
   *
   * ⚠️ `navigator.clipboard` chi ton tai tren ngu canh bao mat (https hoac
   *    localhost). Trang nay luon https, nhung van phai kiem — thieu buoc do thi
   *    tren mot ngu canh la nut se nem loi va KHONG NOI GI, dung kieu hong im
   *    lang ma du an nay da tra gia nhieu lan.
   */
  function ganChep(nut) {
    if (nut.dataset.ganChep === "1") return;
    nut.dataset.ganChep = "1";

    var goc = nut.textContent;
    var dongHo = null;

    function bao(chu, lop) {
      nut.textContent = chu;
      if (lop) nut.classList.add(lop);
      if (dongHo) clearTimeout(dongHo);
      dongHo = setTimeout(function () {
        nut.textContent = goc;
        nut.classList.remove("da");
      }, 1600);
    }

    nut.addEventListener("click", function () {
      var ma = nut.dataset.ma || "";
      if (!ma) return;
      // Noi that la khong chep duoc, thay vi im lang nhu chua bam.
      var hong = function () { bao("Ctrl+C", null); };
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(ma).then(function () {
          bao("✓", "da");
        }, hong);
      } else {
        hong();
      }
    });
  }

  function chay(goc) {
    var pv = goc || document;
    var ds = pv.querySelectorAll(".lv-ma-chep");
    for (var i = 0; i < ds.length; i++) ganChep(ds[i]);
  }

  /* ── Luoi giong: loc + chon the + panel chi tiet ──────────────────────────
   *
   * ⭐ LOC PHIA TRINH DUYET, khong goi may chu.
   *
   *    Tap du lieu la HAI MUOI giong mau cong vai giong rieng — no da nam san
   *    tren trang. Goi mot vong mang cho moi lan bam mot nut loc la tra mot cai
   *    gia that cho mot thu da biet, va no bien mot thao tac tuc thi thanh mot
   *    thao tac co do tre. Ngay tap nay lon toi muc phai phan trang thi doi
   *    sang loc phia may chu — nhung do la mot van de chua ton tai.
   *
   * ⛔ Doi lai: moi the phai mang du du lieu de loc trong `data-*`. Thieu mot
   *    thuoc tinh thi the do bien mat khoi luoi khi loc, va no bien mat IM
   *    LANG — khong loi nao bao.
   */
  function luoiGiong(cauHinh) {
    var luoi = document.getElementById("lv-luoi");
    if (!luoi) return;

    var cfg = cauHinh || {};
    var chu = cfg.chu || {};
    var chiTiet = cfg.chiTiet || {};
    var duong = cfg.duong || "";

    var the = [].slice.call(luoi.querySelectorAll(".lv-the"));
    var oTim = document.getElementById("lv-tim");
    var oSo = document.getElementById("lv-g-so");
    var oKhongHop = document.getElementById("lv-g-khonghop");
    var dangLoc = {loai: "", gioi: "", vung: "", phongcach: ""};

    function loc() {
      var q = ((oTim && oTim.value) || "").trim().toLowerCase();
      var con = 0;
      for (var i = 0; i < the.length; i++) {
        var t = the[i], d = t.dataset;
        // Giong nhan ban khong co ba mat cua giong mau. Khi mot mat do dang
        // duoc loc thi chung KHONG khop — va do la dung: loc "giong nu mien
        // Bac" ma van tra ve mot giong rieng chua phan loai la tra ket qua sai.
        var hop =
          (!dangLoc.loai || d.loai === dangLoc.loai) &&
          (!dangLoc.gioi || d.gioi === dangLoc.gioi) &&
          (!dangLoc.vung || d.vung === dangLoc.vung) &&
          (!dangLoc.phongcach || d.phongcach === dangLoc.phongcach) &&
          (!q || (d.ten || "").toLowerCase().indexOf(q) >= 0);
        t.hidden = !hop;
        if (hop) con++;
      }
      if (oSo) oSo.textContent = String(con);
      if (oKhongHop) oKhongHop.hidden = con !== 0;
    }

    var nutLoc = document.querySelectorAll(".lv-loc-nut");
    for (var i = 0; i < nutLoc.length; i++) {
      (function (nut) {
        nut.addEventListener("click", function () {
          dangLoc[nut.dataset.loc] = nut.dataset.gt || "";
          // Chi mot nut sang trong moi nhom.
          var anhEm = nut.parentNode.querySelectorAll(".lv-loc-nut");
          for (var k = 0; k < anhEm.length; k++) anhEm[k].classList.remove("on");
          nut.classList.add("on");
          loc();
        });
      })(nutLoc[i]);
    }
    if (oTim) oTim.addEventListener("input", loc);

    /* ── Panel chi tiet ───────────────────────────────────────────────────── */
    var oCt = document.getElementById("lv-ct");
    var oCtRong = document.getElementById("lv-ct-rong");

    function dat(id, giaTri) {
      var o = document.getElementById(id);
      if (o) o.textContent = giaTri == null ? "" : String(giaTri);
    }

    function moChiTiet(t) {
      if (!oCt) return;
      var d = t.dataset;
      var laMau = d.loai === "mau";
      var ct = chiTiet[d.ma] || {};

      for (var k = 0; k < the.length; k++) {
        the[k].classList.remove("chon");
        the[k].setAttribute("aria-pressed", "false");
      }
      t.classList.add("chon");
      t.setAttribute("aria-pressed", "true");

      dat("lv-ct-ten", d.ten);
      dat("lv-ct-loai", laMau ? chu.mau : chu.cuaToi);
      dat("lv-ct-ma", d.ma);
      // Dong tinh chat CHI cho giong mau ("Nam · Mien Bac · Tin tuc"). Giong
      // nhan ban khong co ba mat do, va thu the cua no hien la trang thai —
      // thu da co dong rieng ngay duoi. Chep sang day thi panel noi "Ready"
      // hai lan trong bon dong, va lan thu hai khong them thong tin nao.
      var oTinh = t.querySelector(".lv-the-tinh");
      dat("lv-ct-tinh", (laMau && oTinh) ? oTinh.textContent.trim() : "");
      dat("lv-ct-tt", d.trangthai === "active" ? chu.sanSang
        : (d.trangthai === "dang_ghi_danh" ? chu.dangGhiDanh : chu.daTat));

      var nutChep = document.getElementById("lv-ct-chep");
      if (nutChep) nutChep.dataset.ma = d.ma;

      var nutDung = document.getElementById("lv-ct-dung");
      if (nutDung) {
        nutDung.href = duong + "?giong=" + encodeURIComponent(d.ma);
        // Giong dang ghi danh hoac da tat thi khong dung duoc. Mot lien ket dan
        // toi mot man se bao loi ngay la mot lien ket khong nen bam duoc.
        var dungDuoc = d.trangthai === "active";
        nutDung.classList.toggle("lv-tat", !dungDuoc);
        nutDung.setAttribute("aria-disabled", dungDuoc ? "false" : "true");
      }

      var khoiToi = document.getElementById("lv-ct-cuatoi");
      if (khoiToi) {
        khoiToi.hidden = laMau;
        if (!laMau) {
          dat("lv-ct-luot", ct.so_luot || 0);
          dat("lv-ct-phut", ct.phut || 0);
          dat("lv-ct-cuoi", ct.lan_cuoi || chu.chuaDung || "-");

          var oClip = document.getElementById("lv-ct-clip");
          if (oClip) {
            oClip.textContent = "";
            var ds = ct.clip || [];
            for (var j = 0; j < ds.length; j++) {
              var hang = document.createElement("div");
              hang.className = "lv-ct-clip-hang";
              var au = document.createElement("audio");
              au.controls = true; au.preload = "none"; au.src = ds[j].url;
              var nhan = document.createElement("small");
              nhan.textContent = ds[j].giay ? ds[j].giay + "s" : "";
              hang.appendChild(au); hang.appendChild(nhan);
              oClip.appendChild(hang);
            }
          }

          var form = document.getElementById("lv-ct-tat");
          if (form) {
            form.action = duong + "/giong/" + encodeURIComponent(d.ma) + "/tat";
            form.hidden = d.trangthai !== "active";
          }
        }
      }

      oCt.hidden = false;
      if (oCtRong) oCtRong.hidden = true;
      chay(oCt);          // gan lai nut chep ben trong panel
    }

    for (var m = 0; m < the.length; m++) {
      (function (t) {
        t.addEventListener("click", function (e) {
          // Nut "Dung" la mot lien ket that — dung nuot cu bam cua no.
          if (e.target.closest("a")) return;
          moChiTiet(t);
        });
        // The mang `role="button"` nen ban phim phai nhan ca Enter lan Space.
        t.addEventListener("keydown", function (e) {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            moChiTiet(t);
          }
        });
      })(the[m]);
    }

    loc();
  }

  /* ── Song am that, ve tu chinh tep vua sinh ───────────────────────────────
   *
   * ⭐ KHONG THU VIEN. `AudioContext.decodeAudioData` + mot `<canvas>` la du,
   *    va CSP cua nen tang chan CDN ngoai nen mot thu vien se phai tu-host —
   *    them mot tep nua phai nho dinh `?v=`.
   *
   * ⛔ CHI ve o cho co MOT tep cu the de ve. Hinh song trong luoi giong la SVG
   *    dung san, khong phai song that: giai ma mot tep tieng cho moi o trong
   *    mot luoi hai muoi o la tra mot cai gia that cho mot thu trang tri.
   *
   * ⚠️ `decodeAudioData` giai ma TOAN BO tep trong bo nho. Voi mot luot doc
   *    1.500 ky tu (~90 giay, WAV 48 kHz mono ~8,6 MB) thi on. Neu tran ky tu
   *    duoc noi nhieu lan thi cho nay phai doi sang doc dan — nhung do la mot
   *    van de chua ton tai, va no se bao bang mot khoang lag chu khong bang
   *    mot loi im lang.
   */
  function veSong(canvas, url) {
    if (!canvas || !url || !window.AudioContext) return;
    var Ctx = window.AudioContext || window.webkitAudioContext;
    fetch(url)
      .then(function (r) { return r.arrayBuffer(); })
      .then(function (buf) { return new Ctx().decodeAudioData(buf); })
      .then(function (am) {
        var dpr = window.devicePixelRatio || 1;
        var rong = canvas.clientWidth || 300;
        var cao = canvas.clientHeight || 72;
        canvas.width = Math.round(rong * dpr);
        canvas.height = Math.round(cao * dpr);
        var g = canvas.getContext("2d");
        g.scale(dpr, dpr);

        var du = am.getChannelData(0);
        var rongCot = 3, khe = 1;
        var soCot = Math.max(1, Math.floor(rong / rongCot));
        var moiCot = Math.floor(du.length / soCot) || 1;

        // Mau lay tu bien CSS, khong go cung — doi bang mau la doi mot cho.
        var mau = getComputedStyle(document.documentElement)
          .getPropertyValue("--brand-hover").trim() || "#ff514a";
        g.fillStyle = mau;

        for (var i = 0; i < soCot; i++) {
          var dinh = 0;
          for (var j = 0; j < moiCot; j++) {
            var v = Math.abs(du[i * moiCot + j] || 0);
            if (v > dinh) dinh = v;
          }
          var h = Math.max(2, dinh * cao * 0.92);
          g.fillRect(i * rongCot, (cao - h) / 2, rongCot - khe, h);
        }
      })
      .catch(function () {
        // Khong ve duoc song thi trinh phat van chay. An canvas di, dung de
        // mot o trong khong giai thich duoc.
        canvas.hidden = true;
      });
  }

  /* ── Man Studio ───────────────────────────────────────────────────────── */
  function studio(cauHinh) {
    var form = document.getElementById("lv-form");
    if (!form) return;

    var cfg = cauHinh || {};
    var chu = cfg.chu || {};
    var duong = cfg.duong || "";

    var oText = document.getElementById("lv-text");
    var oSo = document.getElementById("lv-so");
    var oUoc = document.getElementById("lv-uoc");
    var oUocDong = document.getElementById("lv-uoc-dong");
    var nutTao = document.getElementById("lv-nut-tao");

    /* Dem ky tu.
     * ⛔ Con so credit o day CHI de hien thi. So that do may chu tinh khi nop —
     *    hai cho tinh tien la hai cho lech nhau, nen cho nay khong bao gio duoc
     *    la nguon cua con so bi tru. No la mot uoc luong tho de khach khong bi
     *    bat ngo; `POST /xem-truoc` moi cho con so dung. */
    function dem() {
      var n = oText.value.length;
      oSo.textContent = String(n);
      var tran = cfg.tranKyTu || 0;
      if (tran) oSo.classList.toggle("sap-tran", n >= tran * 0.9);
      if (oUocDong) oUocDong.hidden = n === 0;
      if (oUoc && n) oUoc.textContent = String(Math.max(1, Math.ceil((1.5 + n / 18) * 0.2)));
    }
    oText.addEventListener("input", dem);
    dem();

    document.getElementById("lv-nut-xoa").addEventListener("click", function () {
      oText.value = ""; dem(); oText.focus();
      document.getElementById("lv-xt").hidden = true;
    });

    /* Xem truoc cach doc. */
    var oXt = document.getElementById("lv-xt");
    document.getElementById("lv-xt-dong").addEventListener("click", function () {
      oXt.hidden = true;
    });
    document.getElementById("lv-nut-xem").addEventListener("click", function () {
      var fd = new FormData();
      fd.append("csrf_token", form.csrf_token.value);
      fd.append("text", oText.value);
      fetch(duong + "/xem-truoc", {method: "POST", body: fd})
        .then(function (r) { return r.json(); })
        .then(function (d) {
          var oChu = document.getElementById("lv-xt-chu");
          var oGhi = document.getElementById("lv-xt-ghi");
          if (!d.ok) { oChu.textContent = d.loi || chu.khongXem; oGhi.textContent = ""; }
          else {
            oChu.textContent = d.da_chuan_hoa;
            var ghi = [];
            if (!d.doi_khac) ghi.push(chu.khongDoi);
            if (d.so_doan > 1) ghi.push((chu.doanNhieu || "").replace("{n}", d.so_doan));
            ghi.push(d.so_ky_tu + " / " + (cfg.tranKyTu || "?"));
            oGhi.textContent = ghi.join(" · ");
            // Con so nay den tu CHINH ham ra hoa don (`gia.uoc_tran`), nen no
            // khong the lech voi phan se bi tam giu.
            if (oUoc && d.uoc_credit != null) oUoc.textContent = String(d.uoc_credit);
          }
          oXt.hidden = false;
        })
        .catch(function () {
          document.getElementById("lv-xt-chu").textContent = chu.khongXem;
          document.getElementById("lv-xt-ghi").textContent = "";
          oXt.hidden = false;
        });
    });

    /* Nop + theo doi TAI CHO.
     *
     * ⭐ Ban truoc lam `window.location.href = '/jobs/' + id` — tuc bam Tao la
     *    ROI KHOI trang, mat van ban, va muon sinh lai thi phai go lai. Anh
     *    tham chieu 01 (va le thuong) muon ket qua hien ngay tai cho. */
    var oCho = document.getElementById("lv-kq-cho");
    var oChay = document.getElementById("lv-kq-chay");
    var oXong = document.getElementById("lv-kq-xong");
    var oLoi = document.getElementById("lv-kq-loi");
    var oTt = document.getElementById("lv-kq-tt");
    var oThanh = document.getElementById("lv-tiendo-thanh");
    var oBuoc = document.getElementById("lv-kq-buoc");
    var dongHo = null;

    function nhan(lop, chuNhan) {
      oTt.innerHTML = "";
      var s = document.createElement("span");
      s.className = "badge " + lop;
      var d = document.createElement("span"); d.className = "dot";
      s.appendChild(d); s.appendChild(document.createTextNode(chuNhan));
      oTt.appendChild(s);
    }

    function hien(cai) {
      oCho.hidden = cai !== "cho";
      oChay.hidden = cai !== "chay";
      oXong.hidden = cai !== "xong";
      oLoi.hidden = cai !== "loi";
    }

    function baoLoi(cau) {
      if (dongHo) clearTimeout(dongHo);
      oLoi.textContent = cau;
      hien("loi");
      nhan("b-err", chu.loi);
      nutTao.disabled = false;
    }

    function xong(d, jobId) {
      if (dongHo) clearTimeout(dongHo);
      hien("xong");
      nhan("b-ok", chu.xong);
      nutTao.disabled = false;

      var au = document.getElementById("lv-player");
      au.src = d.audio_url;
      var tai = document.getElementById("lv-tai");
      tai.href = d.audio_url;
      tai.setAttribute("download", "ltt-voice-" + jobId.slice(0, 8) + ".wav");
      document.getElementById("lv-mo-job").href = "/jobs/" + jobId;
      document.getElementById("lv-ct-giay").textContent =
        d.giay != null ? d.giay + "s" : "-";
      document.getElementById("lv-ct-credit").textContent =
        d.credit != null ? String(d.credit) : "-";
      document.getElementById("lv-ct-job").textContent = jobId;
      var nutChep = document.getElementById("lv-ct-job-chep");
      if (nutChep) { nutChep.dataset.ma = jobId; chay(oXong); }

      var canvas = document.getElementById("lv-song");
      canvas.hidden = false;
      veSong(canvas, d.audio_url);
    }

    function theoDoi(jobId, cho) {
      // Gian cach tang dan: nhanh luc dau (job ngan xong trong vai giay), thua
      // dan de mot job dai khong bien thanh mot may bom yeu cau.
      fetch(duong + "/ket-qua/" + encodeURIComponent(jobId))
        .then(function (r) {
          if (!r.ok) throw new Error("http " + r.status);
          return r.json();
        })
        .then(function (d) {
          if (d.trang_thai === "done") { xong(d, jobId); return; }
          if (d.trang_thai === "error" || d.trang_thai === "cancelled") {
            baoLoi(d.loi || chu.loi); return;
          }
          hien("chay");
          nhan("b-warn", d.trang_thai === "running" ? chu.dangTao : chu.dangCho);
          oThanh.style.width = (d.tien_do || 0) + "%";
          oThanh.setAttribute("aria-valuenow", String(d.tien_do || 0));
          oBuoc.textContent = d.trang_thai === "running" ? chu.dangTao : chu.dangCho;
          dongHo = setTimeout(function () {
            theoDoi(jobId, Math.min(cho * 1.4, 8000));
          }, cho);
        })
        .catch(function () {
          // Mang chap chon KHONG phai job hong. Noi ro va thu lai cham hon,
          // dung bao khach rang luot doc cua ho da that bai.
          oBuoc.textContent = chu.matKetNoi;
          dongHo = setTimeout(function () {
            theoDoi(jobId, Math.min(cho * 2, 15000));
          }, Math.min(cho * 2, 15000));
        });
    }

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      if (dongHo) clearTimeout(dongHo);
      nutTao.disabled = true;
      hien("chay");
      nhan("b-warn", chu.dangCho);
      oThanh.style.width = "0%";
      oBuoc.textContent = chu.dangCho;

      var g = (form.querySelector('input[name="giong"]:checked') || {}).value || "";
      var fd = new FormData();
      fd.append("csrf_token", form.csrf_token.value);
      fd.append("text", oText.value);
      // Hai tien to, hai truong khac nhau o phia may chu — va
      // `features.chuan_hoa` TU CHOI neu gui ca hai.
      if (g.indexOf("v:") === 0) fd.append("voice_id", g.slice(2));
      else if (g.indexOf("m:") === 0) fd.append("preset", g.slice(2));

      fetch(duong + "/tao", {method: "POST", body: fd})
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (!d.ok) { baoLoi(d.loi); return; }
          theoDoi(d.job_id, 1200);
        })
        .catch(function () { baoLoi(chu.khongGui); });
    });

    /* Loc trong bo chon giong. */
    var dsMuc = [].slice.call(document.querySelectorAll(".lv-chon-muc"));
    var oTimChon = document.getElementById("lv-chon-tim");
    var oChonRong = document.getElementById("lv-chon-rong");
    var locLoai = "";

    function locChon() {
      var q = ((oTimChon && oTimChon.value) || "").trim().toLowerCase();
      var con = 0;
      for (var i = 0; i < dsMuc.length; i++) {
        var m = dsMuc[i], d = m.dataset;
        // Muc mac dinh (data-loai rong) LUON hien: no la loi thoat khi bo loc
        // khong con gi, va la thu khach chon neu ho khong muon nghi.
        var hop = d.loai === ""
          || ((!locLoai || d.loai === locLoai)
              && (!q || (d.ten || "").toLowerCase().indexOf(q) >= 0));
        m.hidden = !hop;
        if (hop && d.loai !== "") con++;
      }
      if (oChonRong) oChonRong.hidden = con !== 0;
    }

    var nutChonLoai = document.querySelectorAll("[data-chon-loai]");
    for (var i = 0; i < nutChonLoai.length; i++) {
      (function (nut) {
        nut.addEventListener("click", function () {
          locLoai = nut.dataset.chonLoai || "";
          var anhEm = nut.parentNode.querySelectorAll(".lv-loc-nut");
          for (var k = 0; k < anhEm.length; k++) anhEm[k].classList.remove("on");
          nut.classList.add("on");
          locChon();
        });
      })(nutChonLoai[i]);
    }
    if (oTimChon) oTimChon.addEventListener("input", locChon);

    chay();
  }

  /* ── Man Lich su: chon mot dong -> panel chi tiet ──────────────────────────
   *
   * ⭐ Loc o man nay chay PHIA MAY CHU (form GET), khac man Giong. Ly do: lich
   *    su co the dai va duoc doc theo tran, nen loc phia trinh duyet se loc tren
   *    mot tap DA BI CAT — tra ra it hon su that ma khong noi gi. Loc o may chu
   *    thi tran duoc ap SAU khi loc, va giao dien noi ro pham vi.
   *
   *    Doi lai: moi lan doi bo loc la mot vong tai trang. Chap nhan duoc, va no
   *    cho URL chia se duoc — mot thu loc phia trinh duyet khong cho.
   */
  function lichSu(cauHinh) {
    var ds = [].slice.call(document.querySelectorAll(".lv-ls-dong"));
    if (!ds.length) return;

    var chu = (cauHinh || {}).chu || {};
    var oCt = document.getElementById("lv-ls-ct");
    if (!oCt) return;

    var TEN_TT = {
      done: chu.sanSang, running: chu.dangTao, queued: chu.dangCho,
      cancelled: chu.daHuy, error: chu.loi
    };
    var LOP_TT = {
      done: "b-ok", running: "b-warn", queued: "b-warn",
      cancelled: "b-grey", error: "b-err"
    };

    function dat(id, v) {
      var o = document.getElementById(id);
      if (o) o.textContent = (v === "" || v == null) ? (chu.khong || "-") : String(v);
    }

    function mo(dong) {
      var d = dong.dataset;
      for (var i = 0; i < ds.length; i++) ds[i].classList.remove("chon");
      dong.classList.add("chon");

      var tt = document.getElementById("lv-ls-ct-tt");
      tt.innerHTML = "";
      var s = document.createElement("span");
      s.className = "badge " + (LOP_TT[d.tt] || "b-grey");
      var cham = document.createElement("span"); cham.className = "dot";
      s.appendChild(cham);
      s.appendChild(document.createTextNode(TEN_TT[d.tt] || d.tt));
      tt.appendChild(s);

      dat("lv-ls-ct-luc", d.luc);
      dat("lv-ls-ct-giong", d.giong);
      dat("lv-ls-ct-giay", d.giay ? d.giay + "s" : "");
      dat("lv-ls-ct-credit", d.credit);
      dat("lv-ls-ct-id", d.id);

      var nutChep = document.getElementById("lv-ls-ct-chep");
      if (nutChep) { nutChep.dataset.ma = d.id; chay(oCt); }

      var tai = document.getElementById("lv-ls-ct-tai");
      if (tai) {
        // An nut tai khi khong co tep — mot nut tai ve mot thu khong ton tai la
        // mot nut lam nguoi dung tuong ho lam sai.
        tai.hidden = !d.audio;
        if (d.audio) {
          tai.href = d.audio;
          tai.setAttribute("download", "ltt-voice-" + d.id.slice(0, 8) + ".wav");
        }
      }
      var job = document.getElementById("lv-ls-ct-job");
      if (job) job.href = "/jobs/" + d.id;

      oCt.hidden = false;
    }

    for (var i = 0; i < ds.length; i++) {
      (function (dong) {
        dong.addEventListener("click", function (e) {
          // Trinh phat va lien ket giu cu bam cua chinh chung.
          if (e.target.closest("audio, a, button")) return;
          mo(dong);
        });
        dong.addEventListener("keydown", function (e) {
          if (e.key === "Enter" || e.key === " ") { e.preventDefault(); mo(dong); }
        });
      })(ds[i]);
    }

    chay();
  }

  /* ── Tien ich chung cho hai man Du an ─────────────────────────────────── */

  function nop(duong, csrf, du_lieu) {
    var fd = new FormData();
    fd.append("csrf_token", csrf);
    for (var k in du_lieu) {
      if (du_lieu[k] !== null && du_lieu[k] !== undefined) fd.append(k, du_lieu[k]);
    }
    return fetch(duong, {method: "POST", body: fd}).then(function (r) {
      return r.json();
    });
  }

  function csrfCua(goc) {
    var o = (goc || document).querySelector('input[name="csrf_token"]');
    return o ? o.value : "";
  }

  /* ── Man danh sach du an ───────────────────────────────────────────────── */
  function duAnDanhSach(cauHinh) {
    var form = document.getElementById("lv-da-moi");
    if (!form) return;
    var cfg = cauHinh || {}, chu = cfg.chu || {}, duong = cfg.duong || "";
    var oLoi = document.getElementById("lv-da-loi");

    function mo(hien) {
      form.hidden = !hien;
      if (hien) document.getElementById("lv-da-ten").focus();
    }
    document.getElementById("lv-da-nut-moi").addEventListener("click", function () {
      mo(form.hidden);
    });
    document.getElementById("lv-da-huy").addEventListener("click", function () {
      mo(false);
    });

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      oLoi.hidden = true;
      var nut = form.querySelector('button[type="submit"]');
      nut.disabled = true;
      var giong = (form.querySelector('input[name="giong"]:checked') || {}).value || "";
      nop(duong + "/du-an/tao", csrfCua(form),
          {ten: form.ten.value, giong: giong})
        .then(function (d) {
          if (!d.ok) { oLoi.textContent = d.loi; oLoi.hidden = false; nut.disabled = false; return; }
          // Di thang vao du an vua tao: nguoi ta tao du an DE soan no, khong de
          // ngam no trong danh sach.
          window.location.href = duong + "/du-an/" + encodeURIComponent(d.id);
        })
        .catch(function () {
          oLoi.textContent = chu.khongGui; oLoi.hidden = false; nut.disabled = false;
        });
    });

    chay();
  }

  /* ── Man mot du an ─────────────────────────────────────────────────────── */
  function motDuAn(cauHinh) {
    var ds = document.getElementById("lv-khoi-ds");
    var cfg = cauHinh || {}, chu = cfg.chu || {};
    var duong = cfg.duong || "";
    var goc = duong + "/du-an/" + encodeURIComponent(cfg.maDuAn || "");
    var csrf = csrfCua(document);
    var oLoi = document.getElementById("lv-mda-loi");
    var dongHo = null;

    function baoLoi(cau) {
      if (!oLoi) return;
      oLoi.textContent = cau || chu.khongGui;
      oLoi.hidden = false;
    }
    function xoaLoi() { if (oLoi) oLoi.hidden = true; }

    /* Luu mot khoi. Goi khi o van ban mat tieu diem, khong goi moi phim go.
     *
     * ⭐ `blur` chu khong `input`: mot yeu cau moi ky tu la mot yeu cau moi 50ms
     *    khi go nhanh, va no khong cho them gi — khoi chi can dung TRUOC khi
     *    duoc doc. Cai gia la neu khach dong tab giua chung thi mat, nen o van
     *    ban co vien doi mau bao "chua luu". */
    function luuKhoi(li, xong) {
      var id = li.dataset.id;
      var chuMoi = li.querySelector(".lv-khoi-chu").value;
      var giongMoi = li.querySelector(".lv-khoi-giong").value;
      return nop(goc + "/khoi/" + id + "/sua", csrf, {text: chuMoi, giong: giongMoi})
        .then(function (d) {
          if (d.ok) {
            li.classList.remove("chua-luu");
            if (d.trang_thai) datTrangThai(li, d.trang_thai);
          }
          if (xong) xong(d);
          return d;
        });
    }

    function datTrangThai(li, tt) {
      li.dataset.tt = tt;
      var o = li.querySelector(".lv-khoi-tt");
      if (!o) return;
      var ban = {xong: ["b-ok", chu.daDoc], dang_tao: ["b-warn", chu.dangDoc],
                 can_tao_lai: ["b-warn", chu.doiChu], loi: ["b-err", chu.loi],
                 moi: ["b-grey", chu.chuaDoc]}[tt] || ["b-grey", tt];
      o.innerHTML = "";
      var s = document.createElement("span");
      s.className = "badge " + ban[0];
      var c = document.createElement("span"); c.className = "dot";
      s.appendChild(c); s.appendChild(document.createTextNode(ban[1]));
      o.appendChild(s);
    }

    function ganKhoi(li) {
      var oChu = li.querySelector(".lv-khoi-chu");
      var oGiong = li.querySelector(".lv-khoi-giong");

      oChu.addEventListener("input", function () { li.classList.add("chua-luu"); });
      oChu.addEventListener("blur", function () {
        if (li.classList.contains("chua-luu")) luuKhoi(li);
      });
      oGiong.addEventListener("change", function () { luuKhoi(li); });

      li.querySelector(".lv-khoi-doc").addEventListener("click", function () {
        xoaLoi();
        // Luu TRUOC khi doc. Doc mot khoi voi van ban cu la tieu tien that cho
        // mot ket qua khach khong con muon.
        luuKhoi(li, function () {
          nop(goc + "/khoi/" + li.dataset.id + "/doc", csrf, {})
            .then(function (d) {
              if (!d.ok) { baoLoi(d.loi); return; }
              datTrangThai(li, "dang_tao");
              batDauTheoDoi();
            })
            .catch(function () { baoLoi(chu.khongGui); });
        });
      });

      li.querySelector(".lv-khoi-xoa").addEventListener("click", function () {
        if (!window.confirm(chu.xacNhanXoa)) return;
        nop(goc + "/khoi/" + li.dataset.id + "/xoa", csrf, {})
          .then(function (d) { if (d.ok) window.location.reload(); });
      });
    }

    if (ds) {
      var cac = [].slice.call(ds.querySelectorAll(".lv-khoi"));
      for (var i = 0; i < cac.length; i++) ganKhoi(cac[i]);
    }

    /* Theo doi ca du an bang MOT loi goi, khong mot loi goi moi khoi. */
    function batDauTheoDoi() {
      if (dongHo) return;
      var cho = 1500;
      (function vong() {
        fetch(goc + "/trang-thai")
          .then(function (r) { return r.json(); })
          .then(function (d) {
            if (!d.ok) return;
            var conChay = 0;
            for (var i = 0; i < d.khoi.length; i++) {
              var k = d.khoi[i];
              var li = ds && ds.querySelector('[data-id="' + k.id + '"]');
              if (!li) continue;
              if (li.dataset.tt !== k.trang_thai) datTrangThai(li, k.trang_thai);
              if (k.trang_thai === "dang_tao") conChay++;
              // Tep vua xong: gan trinh phat vao, khong bat tai lai trang.
              if (k.audio_url && !li.querySelector(".lv-khoi-phat")) {
                var au = document.createElement("audio");
                au.className = "lv-khoi-phat";
                au.controls = true; au.preload = "none"; au.src = k.audio_url;
                li.querySelector(".lv-khoi-chan").appendChild(au);
              }
            }
            var tk = d.tom_tat || {};
            datSo("lv-tk-khoi", tk.so_khoi);
            datSo("lv-tk-xong", tk.xong);
            datSo("lv-tk-credit", tk.credit);
            var oTd = document.getElementById("lv-mda-tiendo");
            if (oTd) oTd.textContent = (tk.xong || 0) + "/" + (tk.so_khoi || 0);

            if (conChay) {
              cho = Math.min(cho * 1.3, 8000);
              dongHo = setTimeout(vong, cho);
            } else {
              dongHo = null;   // het viec thi THOI hoi, dung dap nhip mai
            }
          })
          .catch(function () {
            cho = Math.min(cho * 2, 15000);
            dongHo = setTimeout(vong, cho);
          });
      })();
      dongHo = 1;
    }

    function datSo(id, v) {
      var o = document.getElementById(id);
      if (o && v !== undefined && v !== null) o.textContent = String(v);
    }

    // Con khoi dang doc luc mo trang thi theo doi ngay.
    if (ds && ds.querySelector('[data-tt="dang_tao"]')) batDauTheoDoi();

    /* Thanh cong cu */
    var nutTatCa = document.getElementById("lv-doc-tat-ca");
    if (nutTatCa) nutTatCa.addEventListener("click", function () {
      xoaLoi();
      nutTatCa.disabled = true;
      nop(goc + "/doc-tat-ca", csrf, {})
        .then(function (d) {
          nutTatCa.disabled = false;
          if (!d.ok) { baoLoi(d.loi); return; }
          if (!d.so_nop) { baoLoi(chu.hetKhoi); return; }
          // Bao ca so da nop LAN cho con lai neu dung giua chung — mot con so
          // "da gui 3" ma khong noi con 17 la mot nua su that.
          if (d.loi) baoLoi(chu.daNop.replace("{n}", d.so_nop) + " " + d.loi);
          batDauTheoDoi();
          window.location.reload();
        })
        .catch(function () { nutTatCa.disabled = false; baoLoi(chu.khongGui); });
    });

    var nutThem = document.getElementById("lv-them-khoi");
    if (nutThem) nutThem.addEventListener("click", function () {
      nop(goc + "/khoi/them", csrf, {text: ""})
        .then(function (d) {
          if (!d.ok) { baoLoi(d.loi); return; }
          window.location.reload();
        })
        .catch(function () { baoLoi(chu.khongGui); });
    });

    var formNhap = document.getElementById("lv-nhap");
    var nutNhap = document.getElementById("lv-nut-nhap");
    if (formNhap && nutNhap) {
      nutNhap.addEventListener("click", function () { formNhap.hidden = !formNhap.hidden; });
      document.getElementById("lv-nhap-huy").addEventListener("click", function () {
        formNhap.hidden = true;
      });
      formNhap.addEventListener("submit", function (e) {
        e.preventDefault();
        xoaLoi();
        var nut = formNhap.querySelector('button[type="submit"]');
        nut.disabled = true;
        nop(goc + "/nhap", csrf, {text: formNhap.text.value})
          .then(function (d) {
            if (!d.ok) { baoLoi(d.loi); nut.disabled = false; return; }
            window.location.reload();
          })
          .catch(function () { baoLoi(chu.khongGui); nut.disabled = false; });
      });
    }

    var formCaiDat = document.getElementById("lv-mda-caidat");
    if (formCaiDat) formCaiDat.addEventListener("submit", function (e) {
      e.preventDefault();
      var giong = (formCaiDat.querySelector('input[name="giong"]:checked') || {}).value || "";
      var nut = formCaiDat.querySelector('button[type="submit"]');
      nut.disabled = true;
      nop(goc + "/sua", csrf, {ten: formCaiDat.ten.value, giong: giong})
        .then(function () { window.location.reload(); })
        .catch(function () { nut.disabled = false; baoLoi(chu.khongGui); });
    });

    chay();
  }

  /* ── Man tao lo ────────────────────────────────────────────────────────────
   *
   * 🔴 NUT "TAO LO" KHOA TOI KHI MOI DONG HOP LE. Do la luat lon nhat cua man
   *    nay, va o day no chi la mot thuoc tinh `disabled` — nhung thuoc tinh do
   *    la thu dung giua khach va mot lo 500 dong bi giu tien roi hong o dong 47.
   *
   * ⚠️ Va no KHONG phai lop bao ve duy nhat: `POST /lo/tao` kiem lai o may chu
   *    va tu choi neu con dong hong. Mot nut bi khoa la mot tien nghi; may chu
   *    moi la cua.
   */
  function taoLo(cauHinh) {
    var form = document.getElementById("lv-lo-form");
    if (!form) return;
    var cfg = cauHinh || {}, chu = cfg.chu || {}, duong = cfg.duong || "";

    var oChu = document.getElementById("lv-lo-chu");
    var oFile = document.getElementById("lv-lo-file");
    var oXem = document.getElementById("lv-lo-xem");
    var oBody = document.getElementById("lv-lo-tbody");
    var oDem = document.getElementById("lv-lo-dem");
    var oGhi = document.getElementById("lv-lo-ghi");
    var oLoi = document.getElementById("lv-lo-loi");
    var nutTao = document.getElementById("lv-lo-nut-tao");
    var laCsv = false;

    function baoLoi(cau) {
      oLoi.textContent = cau || chu.khongGui;
      oLoi.hidden = false;
    }

    var nutNguon = document.querySelectorAll("[data-nguon]");
    for (var i = 0; i < nutNguon.length; i++) {
      (function (nut) {
        nut.addEventListener("click", function () {
          var la = nut.dataset.nguon === "tep";
          document.getElementById("lv-lo-dan").hidden = la;
          document.getElementById("lv-lo-tep").hidden = !la;
          for (var k = 0; k < nutNguon.length; k++) nutNguon[k].classList.remove("on");
          nut.classList.add("on");
          // Doi nguon thi ket qua kiem cu khong con dung nua. Khoa lai.
          nutTao.disabled = true;
          oXem.hidden = true;
        });
      })(nutNguon[i]);
    }

    function ve(d) {
      oBody.textContent = "";
      for (var i = 0; i < d.dong.length; i++) {
        var r = d.dong[i];
        var tr = document.createElement("tr");
        if (!r.hop_le) tr.className = "hong";
        function o(chuNoi, lop) {
          var td = document.createElement("td");
          if (lop) td.className = lop;
          td.textContent = chuNoi;
          return td;
        }
        tr.appendChild(o(String(r.thu_tu), "dim tnum"));
        tr.appendChild(o(r.text.slice(0, 70), "lv-mlo-chu"));
        tr.appendChild(o((r.giong || "").split(":").pop() || chu.theoLo, "mono"));
        tr.appendChild(o(r.nhan, "mono"));

        var td = document.createElement("td");
        var s = document.createElement("span");
        s.className = "badge " + (r.hop_le ? "b-ok" : "b-err");
        var cham = document.createElement("span"); cham.className = "dot";
        s.appendChild(cham);
        s.appendChild(document.createTextNode(r.hop_le ? chu.ok : (r.loi || "")));
        td.appendChild(s);
        tr.appendChild(td);
        oBody.appendChild(tr);
      }

      oDem.textContent = (chu.hopLe || "")
        .replace("{n}", d.so_hop_le).replace("{t}", d.dong.length);
      oDem.className = "badge " + (d.so_hong ? "b-err" : "b-ok");
      oGhi.textContent = d.so_hong
        ? (chu.conHong || "").replace("{n}", d.so_hong)
        : chu.tatCaHopLe;
      oXem.hidden = false;
      nutTao.disabled = d.so_hong > 0 || d.dong.length === 0;
    }

    function goiKiem() {
      oLoi.hidden = true;
      var fd = new FormData();
      fd.append("csrf_token", form.csrf_token.value);
      fd.append("noi_dung", oChu ? oChu.value : "");
      fd.append("giong", (form.querySelector('input[name="giong"]:checked') || {}).value || "");
      if (oFile && oFile.files && oFile.files[0]) {
        fd.append("tep", oFile.files[0]);
        laCsv = /\.csv$/i.test(oFile.files[0].name);
      }
      return fetch(duong + "/lo/kiem", {method: "POST", body: fd})
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (!d.ok) { baoLoi(d.loi); nutTao.disabled = true; return null; }
          ve(d);
          return d;
        })
        .catch(function () { baoLoi(chu.khongGui); return null; });
    }

    document.getElementById("lv-lo-nut-kiem").addEventListener("click", goiKiem);
    // Doi noi dung thi ket qua kiem cu het hieu luc — khoa lai ngay.
    if (oChu) oChu.addEventListener("input", function () {
      nutTao.disabled = true;
    });
    if (oFile) oFile.addEventListener("change", goiKiem);

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      oLoi.hidden = true;
      nutTao.disabled = true;
      var fd = new FormData();
      fd.append("csrf_token", form.csrf_token.value);
      fd.append("ten", document.getElementById("lv-lo-ten").value);
      fd.append("noi_dung", oChu ? oChu.value : "");
      fd.append("la_csv", laCsv ? "1" : "");
      fd.append("giong", (form.querySelector('input[name="giong"]:checked') || {}).value || "");
      fetch(duong + "/lo/tao", {method: "POST", body: fd})
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (!d.ok) { baoLoi(d.loi); if (d.dong) ve(d); return; }
          window.location.href = duong + "/lo/" + encodeURIComponent(d.id);
        })
        .catch(function () { baoLoi(chu.khongGui); nutTao.disabled = false; });
    });

    chay();
  }

  /* ── Man mot lo dang chay ─────────────────────────────────────────────── */
  function motLo(cauHinh) {
    var bang = document.querySelector(".lv-mlo-bang tbody");
    if (!bang) return;
    var cfg = cauHinh || {}, chu = cfg.chu || {};
    var goc = (cfg.duong || "") + "/lo/" + encodeURIComponent(cfg.maLo || "");
    var csrf = csrfCua(document);
    var oLoi = document.getElementById("lv-mlo-loi");
    var dongHo = null;

    var TEN = {xong: chu.daXong, dang_tao: chu.dangDoc, moi: chu.cho, loi: chu.loi};
    var LOP = {xong: "b-ok", dang_tao: "b-warn", moi: "b-warn", loi: "b-err"};

    function baoLoi(cau) { oLoi.textContent = cau || chu.khongGui; oLoi.hidden = false; }

    function datSo(id, v) {
      var o = document.getElementById(id);
      if (o && v !== undefined && v !== null) o.textContent = String(v);
    }

    function theoDoi() {
      if (dongHo) return;
      var cho = 2000;
      (function vong() {
        fetch(goc + "/trang-thai")
          .then(function (r) { return r.json(); })
          .then(function (d) {
            if (!d.ok) return;
            var conChay = 0;
            for (var i = 0; i < d.dong.length; i++) {
              var x = d.dong[i];
              var tr = bang.querySelector('[data-id="' + x.id + '"]');
              if (!tr) continue;
              if (x.trang_thai === "dang_tao" || x.trang_thai === "moi") conChay++;
              if (tr.dataset.tt === x.trang_thai && !x.audio_url) continue;
              tr.dataset.tt = x.trang_thai;

              var oTt = tr.querySelector(".lv-mlo-tt");
              oTt.textContent = "";
              var s = document.createElement("span");
              s.className = "badge " + (LOP[x.trang_thai] || "b-grey");
              var cham = document.createElement("span"); cham.className = "dot";
              s.appendChild(cham);
              s.appendChild(document.createTextNode(TEN[x.trang_thai] || x.trang_thai));
              oTt.appendChild(s);
              if (x.loi) {
                var sm = document.createElement("small");
                sm.className = "lv-mlo-cau-loi";
                sm.textContent = x.loi;
                oTt.appendChild(sm);
              }
              if (x.giay) tr.querySelector(".lv-mlo-giay").textContent = x.giay + "s";
              if (x.audio_url && !tr.querySelector("audio")) {
                var au = document.createElement("audio");
                au.controls = true; au.preload = "none"; au.src = x.audio_url;
                tr.querySelector(".lv-mlo-phat").appendChild(au);
              }
            }
            var t = d.tom_tat || {};
            datSo("lv-so-tong", t.so_khoi);
            datSo("lv-so-xong", t.xong);
            datSo("lv-so-loi", t.loi);
            datSo("lv-so-uoc", t.uoc_con_lai_s || "—");
            var tai = document.getElementById("lv-lo-tai");
            if (tai && t.xong) tai.hidden = false;

            if (conChay) {
              cho = Math.min(cho * 1.25, 10000);
              dongHo = setTimeout(vong, cho);
            } else {
              dongHo = null;   // het viec thi THOI hoi
            }
          })
          .catch(function () {
            cho = Math.min(cho * 2, 20000);
            dongHo = setTimeout(vong, cho);
          });
      })();
      dongHo = 1;
    }

    if (bang.querySelector('[data-tt="dang_tao"]')) theoDoi();

    var nutChay = document.getElementById("lv-lo-chay");
    if (nutChay) nutChay.addEventListener("click", function () {
      oLoi.hidden = true;
      nutChay.disabled = true;
      nop(goc + "/chay", csrf, {})
        .then(function (d) {
          nutChay.disabled = false;
          if (!d.ok) { baoLoi(d.loi); return; }
          if (!d.so_nop) { baoLoi(chu.hetDong); return; }
          if (d.loi) baoLoi(chu.daNop.replace("{n}", d.so_nop) + " " + d.loi);
          window.location.reload();
        })
        .catch(function () { nutChay.disabled = false; baoLoi(chu.khongGui); });
    });

    chay();
  }

  // Cho phan duoc them sau (ket qua sinh, danh sach tai them) tu gan lai.
  window.LttVoice = {
    gan: chay, luoiGiong: luoiGiong, studio: studio, lichSu: lichSu,
    duAnDanhSach: duAnDanhSach, motDuAn: motDuAn, taoLo: taoLo, motLo: motLo
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { chay(); });
  } else {
    chay();
  }
})();
