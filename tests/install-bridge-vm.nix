{ pkgs, core }:
let
  chat = pkgs.writeShellScriptBin "openclaw" ''
    echo "FIXTURE CHAT READY"
    ${pkgs.coreutils}/bin/sleep 600
  '';
in pkgs.testers.runNixOSTest {
  name = "controlstack-install-bridge";
  nodes.machine = { ... }: {
    virtualisation.memorySize = 1536;
    services.getty.autologinUser = "root";
    environment.etc."agent-installer/live-image".text = "nixos";
    users.groups.controlstack-agent = {};
    users.users.controlstack-agent = { isSystemUser = true; group = "controlstack-agent"; home = "/run/controlstack-agent"; };
    environment.systemPackages = [ core chat pkgs.python3 ];
    systemd.tmpfiles.rules = [ "d /run/controlstack-agent 0700 controlstack-agent controlstack-agent -" ];
    environment.loginShellInit = ''
      if [ "$(tty)" = /dev/tty1 ]; then
        export PYTHONPATH=${core}/lib/system-agent
        export CONTROLSTACK_TUI=${core.tui}/bin/controlstack-tui
        ${pkgs.python3}/bin/python3 ${./install-bridge-demo.py}
      fi
    '';
  };
  testScript = ''
    import json
    machine.start()
    machine.wait_for_unit("getty@tty1.service")
    machine.wait_until_succeeds("test -S /run/controlstack-install-bridge/console.sock")
    agent = "runuser -u controlstack-agent -- env OPENCLAW_STATE_DIR=/run/controlstack-agent system-agent "
    status = json.loads(machine.succeed(agent + "install-status"))
    assert status["checked_by"] == "root-local-console"
    machine.fail("runuser -u nobody -- system-agent install-status")
    machine.succeed(agent + "setup-choice hostname bridge-fixture")
    machine.succeed(agent + "request-install")
    machine.wait_until_succeeds("test -e /run/review-reached")
    machine.wait_until_succeeds("grep -q 'Approve the disposable' /dev/vcs1")
    machine.screenshot("agent-request-local-review")
    machine.succeed("test ! -e /run/fixture-approved")
    machine.send_key("1"); machine.send_key("ret")
    machine.wait_until_succeeds(agent + "install-status | grep cancelled")
    machine.succeed("test ! -e /run/fixture-approved")
    machine.wait_until_succeeds("grep -q 'FIXTURE CHAT READY' /dev/vcs1")
    machine.succeed(agent + "request-install --retry")
    machine.wait_until_succeeds("grep -q 'Approve the disposable' /dev/vcs1")
    machine.send_key("2"); machine.send_key("ret")
    machine.wait_until_succeeds(agent + "install-status | grep installed-awaiting-reboot")
    machine.succeed("test -e /run/fixture-approved")
    machine.wait_until_succeeds("grep -q 'FIXTURE CHAT READY' /dev/vcs1")
    machine.screenshot("same-chat-resumed")
    # A late failure preserves its stage and diagnostic in the same conversation.
    machine.succeed("touch /run/fixture-export-failure")
    machine.succeed(agent + "request-install --retry")
    machine.wait_until_succeeds("grep -q 'Approve the disposable' /dev/vcs1")
    machine.send_key("2"); machine.send_key("ret")
    machine.wait_until_succeeds(agent + "install-status | grep needs-cleanup")
    failed = json.loads(machine.succeed(agent + "install-status"))["request"]
    assert failed["disk_changes"] == "system-written"
    assert failed["disk_erasure_approved"] is True
    assert failed["diagnostic"] == "pool is busy: synthetic namespace holder"
    assert failed["installed_boot_verified"] is False
    machine.wait_until_succeeds("grep -q 'FIXTURE CHAT READY' /dev/vcs1")
    machine.succeed("rm /run/review-reached")
    machine.succeed(agent + "setup-choice hostname changed-after-failure")
    retry_result = json.loads(machine.succeed(agent + "request-install --retry"))
    assert retry_result["id"] == failed["id"] and retry_result["state"] == "needs-cleanup"
    machine.sleep(3)
    machine.succeed("test ! -e /run/review-reached")
    machine.succeed("grep -q 'FIXTURE CHAT READY' /dev/vcs1")
    machine.screenshot("cleanup-failure-preserved-in-chat")

  '';
}
