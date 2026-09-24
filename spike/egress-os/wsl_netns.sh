#!/bin/bash
# Do huong 3: namespace mang cua WSL2. Chay BEN TRONG distro Ubuntu.
# Khong sua gi cua distro: chi tao namespace tam bang `unshare`, het lenh la mat.
# Chay tu Windows:
#   wsl -u root -- bash -c "tr -d '\r' < /mnt/d/.../wsl_netns.sh > /tmp/w.sh; bash /tmp/w.sh"

IP4="${IP4:-172.66.147.243}"
CURL_W="--max-time 8 -s -o /dev/null -w %{http_code}"

thu() {
  local nhan="$1"; shift
  local ma
  ma=$("$@" 2>/dev/null)
  local rc=$?
  if [ "$ma" = "200" ] || [ "$ma" = "UDP_OK" ]; then
    echo "$nhan -> REACHED ($ma)"
  else
    echo "$nhan -> BLOCKED (ma=${ma:-none} rc=$rc)"
  fi
}

echo "== DOI CHUNG (khong namespace) =="
thu "W0a doi_chung tcp_host    " curl $CURL_W https://example.com/
thu "W0b doi_chung tcp_rawip   " curl $CURL_W -H "Host: example.com" "http://$IP4/"
thu "W0c doi_chung udp         " bash -c 'timeout 6 bash -c "exec 3<>/dev/udp/1.1.1.1/53" && echo UDP_OK'
thu "W0d doi_chung interop_win " /mnt/c/Windows/System32/curl.exe --max-time 8 -s -o NUL -w '%{http_code}' https://example.com/

echo
echo "== TRONG NAMESPACE MANG RIENG (unshare --net) =="
thu "W1a netns truc_tiep       " unshare --net -- curl $CURL_W https://example.com/
thu "W1b netns tcp_rawip       " unshare --net -- curl $CURL_W -H "Host: example.com" "http://$IP4/"
thu "W1c netns udp             " unshare --net -- bash -c 'timeout 6 bash -c "exec 3<>/dev/udp/1.1.1.1/53" && echo UDP_OK'
thu "W1d netns SPAWN con (bash)" unshare --net -- bash -c "bash -c 'curl --max-time 8 -s -o /dev/null -w %{http_code} https://example.com/'"
thu "W1e netns SPAWN chau      " unshare --net -- bash -c "bash -c \"sh -c 'curl --max-time 8 -s -o /dev/null -w %{http_code} https://example.com/'\""

echo
echo "== LO THOAT: goi nhi phan WINDOWS tu trong namespace (WSL interop) =="
thu "W2a netns interop_win_curl" unshare --net -- /mnt/c/Windows/System32/curl.exe --max-time 8 -s -o NUL -w '%{http_code}' https://example.com/
thu "W2b netns+mntns, da umount binfmt" unshare --net --mount -- bash -c "umount /proc/sys/fs/binfmt_misc 2>/dev/null; /mnt/c/Windows/System32/curl.exe --max-time 8 -s -o NUL -w '%{http_code}' https://example.com/"
