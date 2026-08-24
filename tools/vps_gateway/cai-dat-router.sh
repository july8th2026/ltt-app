#!/usr/bin/env bash
#
# Cai dat VM router (10.51.0.1) cho app VPS: DHCP theo MAC + tuong lua + MSS clamp.
#
# Chay lai duoc. Chay tren chinh VM router:
#     sudo bash cai-dat-router.sh
#
# ---------------------------------------------------------------------------
# VI SAO CAN DHCP
#
# May khach TU CAI Windows. Trinh cai dat Windows khong doc duoc cloud-init, nen
# khong con duong nao khac de may co mang ma khach khong phai tu go dia chi. DHCP
# cap theo MAC: MAC suy ra tu instance_id (apps/vps/services/dinh_danh.py) va
# KHONG doi qua cac lan chay lai job, nen dat cho la ben.
#
# 'dhcp-range=...,static' = CHI cap cho MAC da khai. May la khong duoc gi ca.
#
# ---------------------------------------------------------------------------
# VI SAO CAN TUONG LUA (day la phan quan trong hon)
#
# Truoc ban nay, viec chan may khach sang LAN nha (192.168.2.0/24) KHONG do
# tuong lua nao lam ca -- 'nft' chua tung duoc cai. No chi la HE QUA PHU cua
# bang dinh tuyen 100: bang do khong co tuyen nao cho 192.168.2.0/24 nen goi roi
# vao 'default dev wg0', ra ham, roi bi thuong nguon vut di.
#
# Do la mot bien phap tinh co, va no vo hieu ngay khi:
#   * 'wg-quick@wg0' hong (thieu khoa, gateway chet luc khoi dong) => khong co
#     'ip rule' => goi cua khach dung BANG CHINH => '192.168.2.0/24 dev eth0' =>
#     may khach nam THANG trong LAN nha, cung mang voi may A va Proxmox;
#   * hoac ai do them mot tuyen vao bang 100.
#
# Ca hai deu im lang. Nen tu day co mot lop chan THAT, khong phu thuoc dinh tuyen.
#
# MSS clamp: duong di qua WireGuard MTU 1420. Windows BO QUA option 26 cua DHCP,
# nen khong clamp thi RDP bat tay duoc nhung moi lan truyen goi lon la treo --
# dung kieu loi khien nguoi ta do mang ca buoi ma khong thay gi.
set -euo pipefail

MANG_KHACH="10.51.0.0/24"
# Toc do con lai sau khi vuot han muc bang thong: 1 MB/s ~ 8 Mbps. Du de dung
# may va vao RDP, cham ro rang khi tai file -- dung y do cua "giam toc".
TOC_GIAM="1048576"
CUA_KHACH="10.51.0.1"
NIC_KHACH="eth1"
NIC_NHA="eth0"
THU_MUC="/etc/ltt-vps"
TEP_MAC="${THU_MUC}/dhcp-hosts"

if [ "$(id -u)" != "0" ]; then echo "Phai chay bang root"; exit 1; fi
if ! ip -br link show "$NIC_KHACH" >/dev/null 2>&1; then
  echo "Khong thay $NIC_KHACH -- day co phai VM router khong?"; exit 1
fi

echo "== 1/5 Cai goi =="
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
# dnsmasq-utils cho 'dhcp_release': tra lai lease khi xoa may. Thieu no
# thi dia chi vua tra lai bi ket toi 'dhcp-range' het han, va khach
# TIEP THEO nhan dung dia chi do se bi 'no address available'.
apt-get install -y -qq dnsmasq dnsmasq-utils nftables >/dev/null

echo "== 2/5 Cho de khai MAC =="
mkdir -p "$THU_MUC"
touch "$TEP_MAC"
# Nen tang ghi tep nay qua SSH bang tai khoan 'ltt'.
chown ltt:ltt "$THU_MUC" "$TEP_MAC" 2>/dev/null || true
chmod 755 "$THU_MUC"; chmod 644 "$TEP_MAC"

echo "== 3/5 dnsmasq =="
cat > /etc/dnsmasq.d/ltt-vps.conf <<EOF
# Sinh boi tools/vps_gateway/cai-dat-router.sh -- dung sua tay.

# KHONG lam DNS. May khach nhan thang 1.1.1.1/8.8.8.8. Mot bo giai ten mo tren
# mang khach la mot bo khuech dai san cho nguoi khac dung -- va ta khong can no.
port=0

# CHI $NIC_KHACH. Day la dong quan trong nhat trong tep: $NIC_NHA la LAN NHA
# (192.168.2.0/24) va mot may chu DHCP thu hai tren do se phat dia chi cho may
# that cua chu nha, danh nhau voi router nha. 'bind-interfaces' bat buoc, vi
# socket DHCP mac dinh nghe MOI card bat ke 'interface='.
interface=$NIC_KHACH
bind-interfaces
except-interface=$NIC_NHA
except-interface=wg0
except-interface=lo
no-dhcp-interface=$NIC_NHA
no-dhcp-interface=wg0

# 'static' = chi cap cho MAC da khai trong $TEP_MAC. May la khong duoc gi.
# O che do nay dia chi dau la DIA CHI MANG (10.51.0.0), khong phai dau mot
# dai. Viet thanh mot dai nhu che do thuong thi dnsmasq TU CHOI KHOI DONG
# ('bad dhcp-range'), va 'dnsmasq --test' KHONG bat duoc loi nay.
# Thoi han lease NGAN co chu y: 1 gio, khong phai 12.
#
# Khi mot may bi xoa, nen tang goi 'dhcp_release' de tra lease ngay. Nhung neu
# lenh do that bai -- router ban, mat mang, goi chua cai -- thi lease cu con
# giu dia chi, va khach TIEP THEO nhan dung dia chi do se bi 'no address
# available': may len nhung khong co mang, va khong loi nao chi vao day.
#
# Lease 1 gio la cai luoi do: te nhat thi no tu lanh sau mot gio.
dhcp-range=10.51.0.0,static,255.255.255.0,1h
dhcp-option=option:router,$CUA_KHACH
dhcp-option=option:dns-server,1.1.1.1,8.8.8.8
# Windows bo qua option nay; no o day cho khach Linux. Duong bao that la MSS
# clamp trong nftables ben duoi.
dhcp-option=option:mtu,1420
dhcp-authoritative
dhcp-hostsfile=$TEP_MAC
log-dhcp
EOF
systemctl enable dnsmasq >/dev/null 2>&1 || true
systemctl restart dnsmasq

echo "== 4/5 Tuong lua =="
cat > /etc/nftables.conf <<EOF
#!/usr/sbin/nft -f
# Sinh boi tools/vps_gateway/cai-dat-router.sh -- dung sua tay.
#
# 'delete table' roi 'table' thay vi 'flush ruleset': 'flush ruleset' xoa ca
# ruleset cua NGUOI KHAC. Tren cong vao Vultr no da tat UFW mot lan roi.
table inet ltt_rt
delete table inet ltt_rt

table inet ltt_rt {
    # Dia chi rieng ma may khach KHONG duoc cham toi. 192.168.2.0/24 la LAN nha:
    # may A (nen tang), Proxmox :8006, cong render may B.
    set rieng {
        type ipv4_addr
        flags interval
        elements = { 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16,
                     169.254.0.0/16, 100.64.0.0/10 }
    }

    # ── Do bang thong tung may ───────────────────────────────────────────
    #
    # 'counter' trong khai bao set = MOI PHAN TU co bo dem rieng. Nho vay do
    # duoc tung khach ma khong can mot luat cho moi nguoi -- dung ly do da
    # chon 'map' cho NAT ben cong vao: ruleset dai lam CHAM MOI ket noi.
    #
    # Bo dem la TICH LUY TU LUC NAP RULESET, va no ve 0 khi router khoi dong
    # lai. Nen tang vi vay luu MOC lan doc truoc va cong phan CHENH LECH; doc
    # thang gia tri nay nhu "da dung bao nhieu thang nay" la sai sau moi lan
    # khoi dong lai. Xem 'bang_thong.cong_don' trong apps/vps.
    set bw_len {
        type ipv4_addr
        counter
    }
    set bw_xuong {
        type ipv4_addr
        counter
    }

    # May dang bi giam toc vi vuot han muc. Nen tang them/bot phan tu luc chay.
    set giam_toc {
        type ipv4_addr
    }

    chain forward {
        type filter hook forward priority filter; policy accept;

        # MSS clamp TRUOC moi luat drop: duong qua WireGuard MTU 1420.
        tcp flags syn tcp option maxseg size set rt mtu

        # Khach ra Internet: chan het dia chi rieng.
        #
        # Khach <-> khach cung nam trong 10.0.0.0/8 nhung KHONG di qua day: hai
        # may cung $MANG_KHACH noi voi nhau o tang 2 tren bridge, khong qua
        # router. Nen luat nay khong cat lien lac giua hai may cua cung mot khach.
        iifname "$NIC_KHACH" ip daddr @rieng counter drop

        # ── Chan thu ra ──────────────────────────────────────────────────
        #
        # Mot may khach gui thu rac la IP cua TA vao danh sach den, va Vultr
        # khoa ca tai khoan -- tuc moi khach mat may cung luc vi mot nguoi.
        # Moi nha cung cap VPS deu chan 25 mac dinh; ta chan ca 465 va 587 vi
        # ba cong nay la ba duong gui, khong phai ba muc do tin cay.
        #
        # Khach can gui thu that thi dung API cua dich vu thu (Resend,
        # SendGrid...) qua HTTPS -- van chay binh thuong qua luat nay.
        iifname "$NIC_KHACH" tcp dport { 25, 465, 587 } counter reject

        # ── Do bang thong ────────────────────────────────────────────────
        #
        # Dat SAU cac luat chan: khong tinh vao han muc cua khach nhung goi
        # ma chinh ta vut di.
        ip saddr @bw_len counter
        ip daddr @bw_xuong counter

        # ── Giam toc khi vuot han muc ────────────────────────────────────
        #
        # 'limit rate over ... drop' chu khong phai cat han: trang ban hua
        # "giam toc, khong tinh them tien". TCP tu lui toc khi mat goi, nen
        # thuc te no hoat dong nhu mot cai phanh chu khong phai mot buc tuong.
        ip saddr @giam_toc limit rate over ${TOC_GIAM} bytes/second drop
        ip daddr @giam_toc limit rate over ${TOC_GIAM} bytes/second drop

        # Chieu nguoc: khong ai tu LAN nha lot vao mang khach ngoai duong ham.
        iifname "$NIC_NHA" oifname "$NIC_KHACH" counter drop
    }

    chain input {
        type filter hook input priority filter; policy accept;

        # Tu mang khach, router chi tra loi DHCP va ping. SSH cua router
        # (10.51.0.1:22) khong phai viec cua khach.
        iifname "$NIC_KHACH" udp dport { 67, 68 } accept
        iifname "$NIC_KHACH" icmp type { echo-request, echo-reply } accept
        iifname "$NIC_KHACH" ct state established,related accept
        iifname "$NIC_KHACH" counter drop
    }
}
EOF
nft -f /etc/nftables.conf
systemctl enable nftables >/dev/null 2>&1 || true

echo "== 5/5 Kiem =="
echo "-- dnsmasq: $(systemctl is-active dnsmasq)"
echo "-- nftables: $(systemctl is-enabled nftables 2>/dev/null)"
nft list chain inet ltt_rt forward | sed 's/^/   /'
echo
echo "So MAC da khai: $(grep -c . "$TEP_MAC" || echo 0)"
echo "XONG."
