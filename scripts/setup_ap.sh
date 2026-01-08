#!/bin/bash
# Minimal Raspberry Pi AP setup script (example). Run as root.
# Installs and configures hostapd + dnsmasq for a basic access point on wlan0.

set -e

SSID=${1:-PiHotspot}
PASSPHRASE=${2:-raspberry}
INTERFACE=${3:-wlan0}
AP_IP=${4:-192.168.4.1}
NETMASK=${5:-255.255.255.0}

echo "Setting up AP: SSID=${SSID} INTERFACE=${INTERFACE} AP_IP=${AP_IP}"

apt-get update
apt-get install -y hostapd dnsmasq

systemctl stop hostapd
systemctl stop dnsmasq

# Configure a static IP on the interface
cat >/etc/dhcpcd.conf <<EOF
interface ${INTERFACE}
static ip_address=${AP_IP}/24
nohook wpa_supplicant
EOF

ip addr add ${AP_IP}/24 dev ${INTERFACE} || true
ip link set ${INTERFACE} up

# dnsmasq configuration
cat >/etc/dnsmasq.conf <<EOF
interface=${INTERFACE}
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
EOF

# hostapd configuration
cat >/etc/hostapd/hostapd.conf <<EOF
interface=${INTERFACE}
driver=nl80211
ssid=${SSID}
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=${PASSPHRASE}
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
EOF

sed -i "s|#DAEMON_CONF=|DAEMON_CONF=\"/etc/hostapd/hostapd.conf\"|" /etc/default/hostapd || true

systemctl unmask hostapd
systemctl enable hostapd
systemctl enable dnsmasq
systemctl restart dhcpcd
systemctl restart dnsmasq
systemctl restart hostapd

echo "AP should be running. SSID=${SSID} Password=${PASSPHRASE}" 
