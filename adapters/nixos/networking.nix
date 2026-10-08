{ lib, ... }:
{
  networking.networkmanager.enable = true;
  networking.networkmanager.wifi.backend = "wpa_supplicant";
  # NetworkManager needs the DBus-controlled supplicant. Forcing wireless.enable
  # to false removes that backend, even while Ethernet keeps working.
  networking.wireless.enable = true;
  networking.wireless.autoDetectInterfaces = false;
  networking.wireless.dbusControlled = true;
  networking.useNetworkd = lib.mkForce false;
  networking.dhcpcd.enable = lib.mkForce false;
  networking.wireless.iwd.enable = lib.mkForce false;
  services.resolved.enable = lib.mkForce false;
  hardware.enableRedistributableFirmware = true;
}
