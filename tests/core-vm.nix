# Isolated lifecycle/broker test. OpenClaw is deliberately NOT started here.
{ pkgs, module }:
pkgs.testers.runNixOSTest {
  name = "controlstack-core-maintenance";
  nodes.machine = { pkgs, lib, ... }: {
    imports = [ module ];
    services.controlstackAgent = {
      enable = true;
      package = lib.mkForce pkgs.coreutils; # No runtime dependency in this independent test.
      zfs.enable = true;
      capabilities.datasets = [ "poola/data" ];
    };
    systemd.services.controlstack-agent.enable = false;
    networking.hostId = "c05a0002";
    virtualisation = { memorySize = 1024; cores = 1; };
    environment.systemPackages = [ pkgs.python3 ];
  };
  testScript = ''
    import json
    machine.start()
    machine.wait_for_unit("multi-user.target")
    machine.succeed("install -d -o controlstack-agent -g controlstack-agent -m 700 /var/lib/controlstack-agent")
    machine.succeed("su -s /bin/sh controlstack-agent -c 'OPENCLAW_CONFIG_PATH=/etc/controlstack-agent/openclaw.json system-agent initialize'")
    machine.succeed("test $(stat -c %a /var/lib/controlstack-agent/gateway-token) = 600")
    machine.fail("su -s /bin/sh nobody -c 'cat /var/lib/controlstack-agent/gateway-token'")
    machine.succeed("echo preserved > /var/lib/controlstack-agent/workspace/sentinel")
    old_boot = machine.succeed("cat /proc/sys/kernel/random/boot_id").strip()
    machine.reboot()
    machine.wait_for_unit("multi-user.target")
    machine.succeed("su -s /bin/sh controlstack-agent -c 'system-agent refresh'")
    facts = json.loads(machine.succeed("cat /var/lib/controlstack-agent/lifecycle/facts.json"))
    assert facts['boot_id'] != old_boot
    machine.succeed("grep -x preserved /var/lib/controlstack-agent/workspace/sentinel")
    machine.fail("system-agent verify-boot")
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
    machine.succeed("echo bad > /pool-a/data/value; zfs rollback poola/data@two; grep -x two /pool-a/data/value")
    machine.succeed("zpool export poolb; zpool import -d /tmp poolb; grep -x two /pool-b/data/value")
    machine.succeed("zpool destroy poola; zpool destroy poolb")
  '';
}
