{ config, lib, pkgs, ... }:
let
  defaults = pkgs.runCommand "controlstack-desktop-defaults" { } ''
    mkdir -p $out/quickshell
    cp ${./.}/*.qml ${./.}/Theme.js $out/quickshell/
    substitute ${./hyprland.lua} $out/hyprland.lua \
      --replace-fail '@keyboard@' '${config.services.xserver.xkb.layout}'
    cp ${./hyprlock.conf} $out/hyprlock.conf
    cp ${./ghostty.conf} $out/ghostty.conf
    cp ${./hypridle.conf} $out/hypridle.conf
  '';
  # The executable basename selects UWSM's Hyprland environment plugin.
  session = pkgs.writeShellScriptBin "start-hyprland" ''
    set -eu
    cfg="''${XDG_CONFIG_HOME:-$HOME/.config}"
    mkdir -p "$cfg/hypr" "$cfg/quickshell/controlstack" "$cfg/ghostty" "$cfg/rofi"
    if [ ! -e "$cfg/ghostty/config" ]; then
      cp --no-clobber ${defaults}/ghostty.conf "$cfg/ghostty/config"
      chmod u+w "$cfg/ghostty/config"
    fi
    if [ ! -e "$cfg/rofi/config.rasi" ]; then
      cp --no-clobber ${./rofi.rasi} "$cfg/rofi/config.rasi"
      chmod u+w "$cfg/rofi/config.rasi"
    fi
    # Seed only missing files. Never overwrite the owner's custom desktop.
    for file in hyprland.lua hyprlock.conf hypridle.conf; do
      if [ ! -e "$cfg/hypr/$file" ]; then
        cp --no-clobber ${defaults}/"$file" "$cfg/hypr/$file"
        chmod u+w "$cfg/hypr/$file"
      fi
    done
    for path in ${defaults}/quickshell/*; do
      file="$(basename "$path")"
      if [ ! -e "$cfg/quickshell/controlstack/$file" ]; then
        cp --no-clobber ${defaults}/quickshell/"$file" "$cfg/quickshell/controlstack/$file"
        chmod u+w "$cfg/quickshell/controlstack/$file"
      fi
    done
    exec ${config.programs.hyprland.package}/bin/start-hyprland
  '';
  entry = pkgs.writeTextFile {
    name = "controlstack-hyprland-session";
    destination = "/share/wayland-sessions/controlstack-hyprland.desktop";
    text = ''
      [Desktop Entry]
      Name=Hyprland + Quickshell
      Comment=Customizable ControlStack desktop
      Exec=${pkgs.uwsm}/bin/uwsm start -e -D Hyprland -- ${session}/bin/start-hyprland
      Type=Application
      DesktopNames=Hyprland
    '';
    passthru.providedSessions = [ "controlstack-hyprland" ];
  };
in {
  imports = [ ../hypruse ];
  services.xserver.enable = true;
  programs.hyprland = { enable = true; withUWSM = true; };
  programs.neovim.enable = true;
  programs.hyprlock.enable = true;
  services.displayManager = {
    sddm.enable = true;
    defaultSession = "controlstack-hyprland";
    sessionPackages = [ entry ];
  };
  hardware.bluetooth.enable = true;
  hardware.bluetooth.powerOnBoot = false;
  services.blueman.enable = true;
  fonts.packages = [ pkgs.inter pkgs.noto-fonts pkgs.noto-fonts-color-emoji pkgs.nerd-fonts.jetbrains-mono ];
  environment.sessionVariables = {
    QT_QUICK_CONTROLS_STYLE = "Basic";
    NIXOS_OZONE_WL = "1";
    TERMINAL = "ghostty";
  };
  xdg.mime.defaultApplications = {
    "text/html" = "firefox.desktop";
    "image/png" = "imv.desktop";
    "image/jpeg" = "imv.desktop";
    "image/webp" = "imv.desktop";
    "x-scheme-handler/http" = "firefox.desktop";
    "x-scheme-handler/https" = "firefox.desktop";
  };
  environment.etc."xdg/mako/config".text = ''
    font=Inter 10
    background-color=#0d1b2ef0
    text-color=#e4edf8
    border-color=#29435f
    border-size=1
    border-radius=12
    padding=16
    margin=12
    width=360
    default-timeout=7000
  '';
  environment.etc."xdg/gtk-3.0/settings.ini".text = "[Settings]\ngtk-application-prefer-dark-theme=1\ngtk-icon-theme-name=Papirus-Dark\ngtk-font-name=Inter 10\n";
  security.rtkit.enable = true;
  services.pipewire = { enable = true; alsa.enable = true; pulse.enable = true; };
  services.upower.enable = true;
  services.gnome.gnome-keyring.enable = true;
  security.pam.services.sddm.enableGnomeKeyring = true;
  services.gvfs.enable = true;
  services.udisks2.enable = true;
  xdg.portal.extraPortals = [ pkgs.xdg-desktop-portal-gtk ];
  xdg.portal.config.Hyprland.default = [ "hyprland" "gtk" ];
  environment.systemPackages = with pkgs; [
    quickshell xterm thunar mousepad networkmanagerapplet pavucontrol
    brightnessctl wl-clipboard libnotify polkit_gnome mako
    papirus-icon-theme adwaita-icon-theme blueman ghostty playerctl firefox seahorse
    yazi (hyprshot.override { withFreeze = true; }) satty grim slurp cliphist rofimoji imv
    config.services.controlstackHypruse.package
    (rofi.override { plugins = [ rofi-calc ]; })
    (writeShellApplication {
      name = "controlstack-desktop-menu";
      runtimeInputs = [ ghostty rofi less systemd uwsm ];
      text = ''
        case "''${1:-}" in
          shortcuts) exec ghostty -e less ${./shortcuts.txt} ;;
          search) rofi -dmenu -i -p "Keyboard shortcuts" < ${./shortcuts.txt} >/dev/null || true ;;
          power)
            choice=$(printf '%s\n' 'Cancel' 'Lock' 'Suspend' 'Sign out' 'Restart' 'Power off' | rofi -dmenu -i -p 'Power') || exit 0
            case "$choice" in
              Lock) exec ${pkgs.hyprlock}/bin/hyprlock ;;
              Suspend) exec systemctl suspend ;;
              'Sign out') exec uwsm stop ;;
              Restart) exec systemctl reboot ;;
              'Power off') exec systemctl poweroff ;;
            esac ;;
        esac
      '';
    })
    (writeShellApplication {
      name = "controlstack-desktop-status";
      runtimeInputs = [ python3 systemd ];
      text = "exec python3 ${./desktop-status.py}";
    })
  ];
  environment.etc."controlstack-agent/desktop-defaults".source = defaults;
  systemd.user.services.controlstack-clipboard = {
    description = "Desktop clipboard history";
    wantedBy = [ "graphical-session.target" ];
    partOf = [ "graphical-session.target" ];
    after = [ "graphical-session-pre.target" ];
    serviceConfig = {
      ExecStart = "${pkgs.wl-clipboard}/bin/wl-paste --type text --watch ${pkgs.cliphist}/bin/cliphist store";
      UMask = "0077";
      Restart = "on-failure";
    };
  };
  systemd.user.services.controlstack-shell = {
    description = "ControlStack Quickshell desktop";
    enableDefaultPath = false;
    wantedBy = [ "graphical-session.target" ];
    partOf = [ "graphical-session.target" ];
    after = [ "graphical-session-pre.target" ];
    serviceConfig = {
      ExecStart = "${pkgs.quickshell}/bin/quickshell -c controlstack";
      Restart = "on-failure";
      RestartSec = 2;
    };
  };
  systemd.user.services.controlstack-polkit = {
    description = "Desktop authorization prompts";
    wantedBy = [ "graphical-session.target" ];
    partOf = [ "graphical-session.target" ];
    after = [ "graphical-session-pre.target" ];
    serviceConfig.ExecStart = "${pkgs.polkit_gnome}/libexec/polkit-gnome-authentication-agent-1";
  };
  systemd.user.services.controlstack-notifications = {
    description = "Desktop notifications";
    wantedBy = [ "graphical-session.target" ];
    partOf = [ "graphical-session.target" ];
    after = [ "graphical-session-pre.target" ];
    serviceConfig.ExecStart = "${pkgs.mako}/bin/mako";
  };
}
