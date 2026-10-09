{ pkgs, core }:
pkgs.testers.runNixOSTest {
 name = "controlstack-ratatui";
 nodes.machine = { pkgs, ... }: {
  virtualisation.memorySize = 2048;
  services.getty.autologinUser = "root";
  environment.systemPackages = [ core pkgs.kbd ];
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
  machine.send_chars("ERASE DEMO12X"); machine.send_key("ret")
  machine.wait_until_succeeds("cat /dev/vcs1 | grep 'Nothing has been erased'")
  machine.screenshot("disk-confirmation-typo")
  machine.send_key("ret")
  machine.wait_until_succeeds("cat /dev/vcs1 | grep 'Type ERASE DEMO123'")
  machine.send_chars("ERASE DEMO123"); machine.send_key("ret")
  machine.wait_until_succeeds("cat /dev/vcs1 | grep 'Review complete'")
  machine.send_key("ret"); machine.sleep(1)
  machine.send_key("4"); machine.send_key("ret"); machine.sleep(1)
  machine.send_key("esc")
  machine.wait_until_succeeds("cat /dev/vcs1 | grep 'Review cancelled'")
  machine.send_key("ret"); machine.sleep(1)
  machine.send_key("4"); machine.send_key("ret"); machine.sleep(1)
  machine.send_chars("wrong"); machine.send_key("ret")
  machine.wait_until_succeeds("cat /dev/vcs1 | grep 'Try the disk confirmation again'")
  machine.send_key("2"); machine.send_key("ret")
  machine.wait_until_succeeds("cat /dev/vcs1 | grep 'Review cancelled'")
  machine.send_key("ret"); machine.sleep(1)
  # Confirm every offered font and check the QR or its complete-code fallback.
  for index, pixels in [(1, 14), (2, 16), (3, 20), (4, 24)]:
      machine.send_key("5"); machine.send_key("ret")
      machine.wait_until_succeeds("cat /dev/vcs1 | grep 'Text size for this USB session'", timeout=10)
      machine.send_key(str(index)); machine.send_key("ret")
      machine.wait_until_succeeds("cat /dev/vcs1 | grep 'Keep this text size'", timeout=10)
      machine.screenshot("text-size-" + str(pixels))
      machine.send_key("ret")
      machine.wait_until_succeeds("cat /dev/vcs1 | grep 'Text size saved'", timeout=10)
      machine.succeed("grep -q '" + str(pixels) + "' /run/controlstack-console/tty1.json")
      machine.send_key("ret")
      machine.wait_until_succeeds("cat /dev/vcs1 | grep 'Welcome to your OpenClaw'", timeout=10)
      machine.send_key("1"); machine.send_key("ret")
      machine.wait_until_succeeds("cat /dev/vcs1 | grep TEST-CODE", timeout=10)
      machine.screenshot("qr-size-" + str(pixels))
      if "Enlarge the terminal" not in machine.succeed("cat /dev/vcs1"):
          value = subprocess.check_output(["${pkgs.zbar}/bin/zbarimg", "--quiet", "--raw", os.path.join(os.environ["out"], "qr-size-" + str(pixels) + ".png")], text=True)
          assert value.strip() == "https://auth.openai.com/codex/device"
      machine.send_key("esc")
      machine.wait_until_succeeds("cat /dev/vcs1 | grep 'Welcome to your OpenClaw'", timeout=10)
  # Exercise real Linux font ioctls on the guest virtual console, not a mock.
  standard = machine.succeed("stty -F /dev/tty1 size").strip()
  machine.send_key("5"); machine.send_key("ret"); machine.sleep(1)
  machine.send_key("3"); machine.send_key("ret")
  machine.wait_until_succeeds("cat /dev/vcs1 | grep 'Keep this text size'", timeout=10)
  large = machine.succeed("stty -F /dev/tty1 size").strip()
  assert large != standard, (standard, large)
  machine.screenshot("text-size-large-preview")
  machine.send_key("ret")
  machine.wait_until_succeeds("grep -q '20' /run/controlstack-console/tty1.json")
  machine.wait_until_succeeds("cat /dev/vcs1 | grep 'Text size saved'")
  machine.send_key("ret"); machine.sleep(1)
  # An unanswered preview automatically restores the last confirmed size.
  machine.send_key("5"); machine.send_key("ret"); machine.sleep(1)
  machine.send_key("1"); machine.send_key("ret")
  machine.wait_until_succeeds("cat /dev/vcs1 | grep 'Keep this text size'", timeout=10)
  machine.sleep(16)
  assert machine.succeed("stty -F /dev/tty1 size").strip() == large
  machine.succeed("cat /dev/vcs1 | grep -i 'restored'")
  machine.screenshot("text-size-auto-restored")
  machine.send_key("ret"); machine.sleep(1)
  # Escape also rolls back without replacing the saved preference.
  machine.send_key("5"); machine.send_key("ret"); machine.sleep(1)
  machine.send_key("2"); machine.send_key("ret")
  machine.wait_until_succeeds("cat /dev/vcs1 | grep 'Keep this text size'", timeout=10)
  machine.send_key("esc")
  machine.wait_until_succeeds("cat /dev/vcs1 | grep 'Previous text size restored'")
  assert machine.succeed("stty -F /dev/tty1 size").strip() == large
  machine.succeed("grep -q '20' /run/controlstack-console/tty1.json")
  machine.send_key("ret"); machine.sleep(1)
  # Reinitializing setup restores the saved preference on this same live boot.
  machine.succeed("setfont -C /dev/tty1 ${core}/lib/system-agent/consolefonts/ter-u14n.psf.gz")
  machine.succeed("PYTHONPATH=${core}/lib/system-agent ${pkgs.python3}/bin/python3 -c 'from system_agent.console_font import initialize; initialize()' < /dev/tty1")
  assert machine.succeed("stty -F /dev/tty1 size").strip() == large
  # An abruptly closed frontend must not leave an unconfirmed font behind.
  machine.send_key("5"); machine.send_key("ret"); machine.sleep(1)
  machine.send_key("1"); machine.send_key("ret")
  machine.wait_until_succeeds("cat /dev/vcs1 | grep 'Keep this text size'", timeout=10)
  machine.succeed("pkill -KILL -f '[c]ontrolstack-tui'")
  machine.sleep(2)
  assert machine.succeed("stty -F /dev/tty1 size").strip() == large
  machine.wait_until_fails("pgrep -f '[c]ontrolstack-tui'")
 '';
}
