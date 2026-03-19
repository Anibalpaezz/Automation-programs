@echo off
setlocal

rem Configure network interface
netsh interface ipv4 set address name="Ethernet" source=dhcp
netsh interface ipv4 set dnsservers "Ethernet" dhcp

rem Renew DHCP lease
rem ipconfig /release
rem ipconfig /renew

echo DHCP network configuration complete.
