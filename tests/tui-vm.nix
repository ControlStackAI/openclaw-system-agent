{ pkgs, core }:
pkgs.testers.runNixOSTest {
 name = "controlstack-ratatui";
 nodes.machine = { pkgs, ... }: {
  virtualisation.memorySize = 2048;
  services.getty.autologinUser = "root";
  environment.systemPackages = [ core ];
  environment.loginShellInit = ''
    if [ "$(tty)" = /dev/tty1 ]; then
      export PYTHONPATH=${core}/lib/system-agent
      export CONTROLSTACK_TUI=${core.tui}/bin/controlstack-tui
      ${pkgs.python3}/bin/python3 ${./tui-demo.py}
    fi
  '';
 };
 testScript = ''
  import os, subprocess
  machine.start()
  machine.wait_for_unit("getty@tty1.service")
  machine.wait_until_succeeds("pgrep -f '[c]ontrolstack-tui'")
  machine.sleep(3)
  machine.screenshot("welcome")
  machine.send_key("1"); machine.send_key("ret")
  machine.sleep(2)
  machine.succeed("cat /dev/vcs1 | grep TEST-CODE")
  machine.screenshot("provider-device-code")
  decoded = subprocess.check_output(["${pkgs.zbar}/bin/zbarimg", "--quiet", "--raw", os.path.join(os.environ["out"], "provider-device-code.png")], text=True)
  assert decoded.strip() == "https://auth.openai.com/codex/device", decoded
  machine.send_key("esc"); machine.sleep(1)
  machine.send_key("2"); machine.send_key("ret"); machine.sleep(1)
  machine.screenshot("desktop-choice")
  machine.send_key("esc"); machine.sleep(1)
  machine.send_key("3"); machine.send_key("ret"); machine.sleep(1)
  machine.send_chars("fixturepassword")
  machine.fail("cat /dev/vcs1 | grep fixturepassword")
  machine.screenshot("protected-input")
  machine.send_key("ret"); machine.sleep(1)
  machine.succeed("cat /dev/vcs1 | grep 'Protected input accepted'")
  machine.send_key("ret"); machine.sleep(1)
  machine.send_key("4"); machine.send_key("ret"); machine.sleep(1)
  machine.succeed("cat /dev/vcs1 | grep 'All contents'")
  machine.screenshot("disk-review")
  machine.send_key("esc"); machine.sleep(1)
  machine.send_key("5"); machine.send_key("ret")
  machine.wait_until_fails("pgrep -f '[c]ontrolstack-tui'")
 '';
}
