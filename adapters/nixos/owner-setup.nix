# Reusable owner interface for preset and custom deployments; no desktop/greeter selection.
{ owner, graphical ? true, useGhostty ? true }:
{ config, lib, pkgs, ... }:
let
  core = config.services.controlstackAgent.corePackage;
  setup = "${lib.getBin core}/bin/system-agent-setup";
  launcher = pkgs.writeShellScriptBin "controlstack-assistant" ''
    set -eu
    [ "$(${pkgs.coreutils}/bin/id -un)" = ${lib.escapeShellArg owner} ] || exit 1
    exec /run/wrappers/bin/sudo -n ${setup}
  '';
  terminal = if useGhostty then pkgs.ghostty else pkgs.xterm;
  terminalCommand = if useGhostty then "${terminal}/bin/ghostty --title=\"System Assistant\" -e"
    else "${terminal}/bin/xterm -T \"System Assistant\" -fa Monospace -fs 12 -bg \"#0b1626\" -fg \"#dce7f7\" -geometry 100x30 -e";
  entry = ''
    [Desktop Entry]
    Type=Application
    Name=System Assistant
    Comment=Talk to your resident computer assistant
    Icon=computer
    Categories=System;
    Exec=${terminalCommand} ${launcher}/bin/controlstack-assistant
    Terminal=false
  '';
in {
  assertions = [ {
    assertion = config.services.controlstackAgent.enable &&
      config.services.controlstackAgent.mutableProviderSetup &&
      !config.services.controlstackAgent.ephemeral && config.users.users.${owner}.isNormalUser;
    message = "Owner setup requires an installed mutable-provider agent and a normal owner account.";
  } ];
  security.sudo.extraRules = [ {
    users = [ owner ];
    commands = [ { command = ''${setup} ""''; options = [ "NOPASSWD" ]; } ];
  } ];
  environment.systemPackages = [ launcher ] ++ lib.optionals graphical [ terminal
    (pkgs.writeTextDir "share/applications/controlstack-agent.desktop" entry) ];
  environment.etc = lib.optionalAttrs graphical {
    "xdg/autostart/controlstack-agent.desktop".text = entry;
  };
  environment.interactiveShellInit = ''
    if [ "$(id -un)" = ${lib.escapeShellArg owner} ] && [ -t 0 ] && [ "$(tty)" = /dev/tty1 ] &&
       [ "''${CONTROLSTACK_SETUP_OPENED:-}" != 1 ]; then
      export CONTROLSTACK_SETUP_OPENED=1
      ${launcher}/bin/controlstack-assistant
    fi
  '';
}
