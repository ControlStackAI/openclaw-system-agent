{ pkgs, module }:
pkgs.testers.runNixOSTest {
  name = "controlstack-agent-lifecycle";
  nodes.machine = { pkgs, ... }: {
    imports = [ module ];
    services.controlstackAgent = {
      enable = true; zfs.enable = true;
      capabilities.datasets = [ "poola/data" ];
      settings = {
        agents.defaults.model.primary = "fixture/fixture-model";
        models.providers.fixture = {
          baseUrl = "http://127.0.0.1:18080/v1";
          api = "openai-completions";
          apiKey = "non-secret-vm-fixture";
          models = [{ id = "fixture-model"; name = "VM fixture, not a model";
            contextWindow = 32768; maxTokens = 1024; }];
        };
      };
    };
    systemd.services.fixture-provider = {
      wantedBy = [ "multi-user.target" ];
      serviceConfig.ExecStart = "${pkgs.python3}/bin/python3 ${./fixture_provider.py}";
    };
    networking.hostId = "c05a0001";
    virtualisation = { memorySize = 2304; cores = 2; };
    boot.zfs.devNodes = "/dev/disk/by-id";
    environment.systemPackages = [ pkgs.curl pkgs.sqlite pkgs.python3 ];
  };
  testScript = ''
    import json
    machine.start(allow_reboot=True)
    machine.wait_for_unit("controlstack-agent.service", timeout=180)
    machine.wait_until_succeeds("curl -fsS http://127.0.0.1:18789/healthz", timeout=180)
    machine.succeed("systemctl show controlstack-agent -p User --value | grep -x controlstack-agent")
    machine.succeed("test $(stat -c %a /var/lib/controlstack-agent) = 700")
    machine.succeed("test $(stat -c %a /var/lib/controlstack-agent/gateway-token) = 600")
    machine.succeed("test -s /var/lib/controlstack-agent/workspace/AGENTS.md")
    machine.succeed("test -s /var/lib/controlstack-agent/lifecycle/facts.json")
    # Authenticated CLI health must succeed independently of anonymous HTTP liveness.
    command = "su -s /bin/sh controlstack-agent -c 'OPENCLAW_NIX_MODE=1 OPENCLAW_CONFIG_PATH=/etc/controlstack-agent/openclaw.json system-agent health'"
    machine.succeed(command)
    agent_command = "su -s /bin/sh controlstack-agent -c 'OPENCLAW_NIX_MODE=1 OPENCLAW_STATE_DIR=/var/lib/controlstack-agent OPENCLAW_CONFIG_PATH=/etc/controlstack-agent/openclaw.json openclaw agent --agent main --session-key agent:main:resident-vm --message persistence-sentinel --json'"
    machine.succeed(agent_command, timeout=120)
    machine.succeed("grep -q 'ControlStackAI resident system agent' /tmp/fixture-request.json")
    machine.fail("su -s /bin/sh nobody -c 'cat /var/lib/controlstack-agent/gateway-token'")
    machine.succeed("echo preserved > /var/lib/controlstack-agent/workspace/sentinel")
    first_boot = machine.succeed("cat /proc/sys/kernel/random/boot_id").strip()
    machine.reboot()
    machine.wait_for_unit("controlstack-agent.service", timeout=180)
    machine.wait_until_succeeds("curl -fsS http://127.0.0.1:18789/healthz", timeout=180)
    machine.succeed(command)
    machine.succeed(agent_command.replace("persistence-sentinel", "second-turn"), timeout=120)
    machine.succeed("grep -q persistence-sentinel /tmp/fixture-request.json")
    machine.succeed("grep -x preserved /var/lib/controlstack-agent/workspace/sentinel")
    facts = json.loads(machine.succeed("cat /var/lib/controlstack-agent/lifecycle/facts.json"))
    assert facts['boot_id'] != first_boot
    assert facts['boot_id'] == machine.succeed("cat /proc/sys/kernel/random/boot_id").strip()
    # No installation handoff means no installed-boot claim.
    machine.fail("system-agent verify-boot")
    # Real ZFS operations exclusively on regular files inside this VM.
    machine.succeed("modprobe zfs; truncate -s 256M /tmp/vdev-a; truncate -s 256M /tmp/vdev-b")
    machine.succeed("zpool create -m /pool-a poola /tmp/vdev-a; zpool create -m /pool-b poolb /tmp/vdev-b")
    machine.succeed("zfs create poola/data; echo one > /pool-a/data/value; zfs snapshot poola/data@one")
    maintenance = json.loads(machine.succeed("system-agent-admin plan snapshot poola/data"))
    machine.fail("su -s /bin/sh controlstack-agent -c 'system-agent-admin plan snapshot poola/data'")
    machine.fail("system-agent-admin apply " + maintenance['id'] + " --approve wrong")
    approved = "system-agent-admin apply " + maintenance['id'] + " --approve " + maintenance['digest']
    machine.succeed(approved)
    machine.fail(approved)
    machine.succeed("zfs list -H -t snapshot poola/data@" + maintenance['snapshot_name'])
    machine.succeed("zfs send poola/data@one | zfs receive poolb/data")
    machine.succeed("echo two > /pool-a/data/value; zfs snapshot poola/data@two")
    machine.succeed("zfs send -i poola/data@one poola/data@two | zfs receive poolb/data")
    machine.succeed("grep -x two /pool-b/data/value; zfs rollback poola/data@two; echo bad > /pool-a/data/value; zfs rollback poola/data@two; grep -x two /pool-a/data/value")
    machine.succeed("zpool export poolb; zpool import -d /tmp poolb; grep -x two /pool-b/data/value")
    machine.succeed("zpool destroy poola; zpool destroy poolb")
    machine.succeed("install -d -o controlstack-agent -g controlstack-agent -m 700 /var/lib/agent-backups")
    machine.succeed("su -s /bin/sh controlstack-agent -c 'OPENCLAW_NIX_MODE=1 OPENCLAW_CONFIG_PATH=/etc/controlstack-agent/openclaw.json system-agent backup --destination /var/lib/agent-backups'")
    machine.succeed("find /var/lib/agent-backups -name '*.tar.gz' | grep .")
    archive = machine.succeed("find /var/lib/agent-backups -name '*.tar.gz' | head -1").strip()
    machine.succeed("su -s /bin/sh controlstack-agent -c 'OPENCLAW_NIX_MODE=1 OPENCLAW_STATE_DIR=/var/lib/controlstack-agent OPENCLAW_CONFIG_PATH=/etc/controlstack-agent/openclaw.json openclaw backup restore " + archive + " --target /var/lib/agent-backups/restored --json'", timeout=120)
    machine.succeed("find /var/lib/agent-backups/restored -name sentinel -exec grep -x preserved {} \\; | grep preserved")
  '';
}
