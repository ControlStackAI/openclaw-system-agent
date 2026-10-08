# Real gateway exec + sudo + mount, using only a disposable disk inside this VM.
{ pkgs, module }:
pkgs.testers.runNixOSTest {
  name = "controlstack-live-system-access";
  nodes.machine = { ... }: {
    imports = [ module ../adapters/nixos/live-access.nix ];
    services.controlstackAgent = {
      enable = true; ephemeral = true; mutableProviderSetup = true;
      workspaceExecution = true; nixosMcp.enable = false;
      settings = {
        agents.defaults.model.primary = "fixture/fixture-model";
        models.providers.fixture = {
          baseUrl = "http://127.0.0.1:18080/v1"; api = "openai-completions";
          apiKey = "non-secret-vm-fixture";
          models = [{ id = "fixture-model"; name = "VM fixture, not a model";
            contextWindow = 32768; maxTokens = 1024; }];
        };
      };
    };
    environment.etc."agent-installer/live-image".text = "nixos";
    environment.systemPackages = [ pkgs.curl pkgs.python3 pkgs.e2fsprogs ];
    virtualisation = { memorySize = 2304; cores = 2; emptyDiskImages = [ 128 ]; };
    systemd.services.fixture-provider = {
      wantedBy = [ "multi-user.target" ];
      serviceConfig.ExecStart = "${pkgs.python3}/bin/python3 ${./fixture_provider.py}";
    };
  };
  testScript = ''
    import json
    machine.start()
    machine.wait_for_unit("controlstack-agent.service", timeout=180)
    machine.wait_until_succeeds("curl -fsS http://127.0.0.1:18789/healthz", timeout=180)
    # Format only the test driver's extra empty disk, never a host device.
    machine.succeed("mkfs.ext4 -L CS_FIXTURE_USB /dev/vdb; mkdir -p /mnt/seed; mount /dev/vdb /mnt/seed; echo usb-readable > /mnt/seed/sentinel; umount /mnt/seed")
    agent = "runuser -u controlstack-agent -- env OPENCLAW_STATE_DIR=/run/controlstack-agent OPENCLAW_CONFIG_PATH=/run/controlstack-agent/openclaw.json "
    machine.succeed(agent + "system-agent local-policy")
    machine.succeed("systemctl restart controlstack-agent")
    machine.wait_until_succeeds(agent + "system-agent health", timeout=180)
    facts = json.loads(machine.succeed(agent + "system-agent inspect"))
    assert facts['system_access'] == {'configured': 'sudo-full', 'root_command_verified': True}, facts
    machine.succeed(agent + "openclaw agent --agent main --session-key agent:main:usb-test --message live-usb-access-fixture --json", timeout=180)
    # The mount done by the REAL gateway exec tool must reach the host namespace.
    machine.succeed("findmnt -n /mnt/controlstack-usb-fixture; grep -x usb-readable /mnt/controlstack-usb-fixture/sentinel")
    request = json.loads(machine.succeed("cat /tmp/fixture-request.json"))
    results = [m for m in request['messages'] if m.get('role') == 'tool']
    assert 'usb-readable' in json.dumps(results), results
    machine.succeed("test $(stat -c %a /run/controlstack-agent) = 700; test $(stat -c %a /run/controlstack-agent/gateway-token) = 600")
    machine.fail("runuser -u nobody -- sudo -n id -u")
    machine.succeed(agent + "sudo -n umount /mnt/controlstack-usb-fixture")
    machine.fail("mountpoint /mnt/controlstack-usb-fixture")
  '';
}
