@echo off
setlocal

rem Set IP address, subnet mask, and default gateway
netsh interface ipv4 set address name="Ethernet" static 192.168.3.8 255.255.255.0 192.168.3.243

rem Set DNS servers
netsh interface ipv4 add dns name="Ethernet" addr=192.168.3.245 index=11
netsh interface ipv4 add dns name="Ethernet" addr=80.85.0.33 index=11

echo Manual IP configuration complete.
