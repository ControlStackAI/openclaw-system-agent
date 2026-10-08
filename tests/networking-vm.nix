{ pkgs }:
pkgs.testers.runNixOSTest {
  name = "controlstack-networkmanager-wifi";
  nodes.machine = { pkgs, lib, ... }: {
    imports = [ ../adapters/nixos/networking.nix ];
    # QEMU defaults disable Wi-Fi even with hwsim; override only in this fixture.
    networking.wireless.enable = lib.mkOverride 0 true;
    boot.kernelPackages = pkgs.linuxPackages_latest;
    boot.kernelModules = [ "mac80211_hwsim" ];
    boot.extraModprobeConfig = "options mac80211_hwsim radios=2";
    networking.usePredictableInterfaceNames = false;
    networking.networkmanager.unmanaged = [ "interface-name:wlan0" ];
    environment.systemPackages = [ pkgs.hostapd pkgs.iw ];
    environment.etc."hostapd-fixture.conf".text = ''
      interface=wlan0
      driver=nl80211
      ssid=ControlStack-Test-WiFi
      hw_mode=g
      channel=1
      wpa=2
      wpa_passphrase=public-fixture-only
      wpa_key_mgmt=WPA-PSK
      rsn_pairwise=CCMP
      ctrl_interface=/run/hostapd
    '';
    virtualisation = { memorySize = 1024; cores = 1; };
  };
  testScript = ''
    machine.start()
    machine.wait_for_unit("NetworkManager.service")
    machine.wait_until_succeeds("ip link show wlan1")
    machine.succeed("rfkill unblock wlan; nmcli radio wifi on")
    machine.succeed("hostapd -B /etc/hostapd-fixture.conf")
    machine.wait_until_succeeds("nmcli -t -f SSID device wifi list ifname wlan1 --rescan yes | grep -Fx ControlStack-Test-WiFi")
    machine.wait_for_unit("wpa_supplicant.service")
    machine.succeed("nmcli connection add type wifi ifname wlan1 con-name fixture ssid ControlStack-Test-WiFi ipv4.method manual ipv4.addresses 192.0.2.2/24 ipv6.method disabled wifi-sec.key-mgmt wpa-psk wifi-sec.psk public-fixture-only")
    machine.succeed("nmcli --wait 30 connection up fixture")
    machine.succeed("nmcli -g GENERAL.STATE device show wlan1 | grep '^100'")
    machine.succeed("hostapd_cli -i wlan0 all_sta | grep -F '[AUTHORIZED]'")
    machine.succeed("nmcli radio wifi off")
    machine.wait_until_succeeds("rfkill --noheadings --output TYPE,SOFT | grep -E 'wlan +blocked'")
    machine.succeed("rfkill unblock wlan; nmcli radio wifi on; nmcli --wait 30 connection up fixture")
    machine.succeed("nmcli -g GENERAL.STATE device show wlan1 | grep '^100'")
    machine.succeed("test ! -e /etc/systemd/system/iwd.service; test ! -e /etc/systemd/system/dhcpcd.service")
  '';
}
