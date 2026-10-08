{ pkgs, core }:
pkgs.testers.runNixOSTest {
  name = "controlstack-owner-policy";
  nodes.machine = { lib, ... }: {
    imports = [ (import ../adapters/nixos/owner-policy.nix {
      owner = "owner"; inherit core; powerPolicy = "always-on"; loginPolicy = "yubikey";
    }) ];
    virtualisation.memorySize = 1536;
    users.users.owner = { isNormalUser = true; password = "fixture-password"; };
    environment.systemPackages = [ core pkgs.pamtester pkgs.util-linux ];
    systemd.tmpfiles.rules = [
      "d /var/lib/controlstack-security 0755 root root -"
      "f /var/lib/controlstack-security/password-unlock.json 0644 root root - {\"enabled\":true}"
      "f /var/lib/controlstack-security/key-device.json 0644 root root - {\"serial\":\"fixture\"}"
      "f /var/lib/controlstack-security/u2f-keys 0644 root root - owner:AA,AA,es256,+presence"
    ];
  };
  testScript = ''
    machine.start()
    machine.wait_for_unit("multi-user.target")
    machine.succeed("grep -q usbcore.autosuspend=-1 /proc/cmdline")
    machine.succeed("test $(cat /sys/module/usbcore/parameters/autosuspend) = -1")
    for unit in ["sleep", "suspend", "hibernate", "hybrid-sleep", "suspend-then-hibernate"]:
        machine.succeed("test $(systemctl show -p LoadState --value " + unit + ".target) = masked")
    machine.fail("systemctl suspend")
    machine.succeed("systemd-analyze cat-config systemd/logind.conf | grep HandleLidSwitch=ignore")
    machine.succeed("systemd-analyze cat-config systemd/sleep.conf | grep AllowHibernation=false")
    machine.succeed("systemctl is-active controlstack-key-watch")
    machine.succeed("runuser -u owner -- sh -c 'printf fixture-password | pamtester hyprlock owner authenticate'")
    machine.fail("runuser -u owner -- sh -c 'printf wrong-password | pamtester hyprlock owner authenticate'")
    # Correct passwords cannot replace the key at initial sign-in.
    machine.fail("printf fixture-password | pamtester sddm owner authenticate")
    machine.fail("printf fixture-password | pamtester login owner authenticate")
    machine.fail("runuser -u owner -- sh -c 'echo true > /var/lib/controlstack-security/password-unlock.json'")
    machine.succeed("printf '{\"enabled\":false}' > /var/lib/controlstack-security/password-unlock.json")
    machine.fail("runuser -u owner -- sh -c 'printf fixture-password | pamtester hyprlock owner authenticate'")
    machine.fail("system-agent-key password-check")
    # No active unlocked desktop and no enrolled key: changing policy is denied.
    machine.fail("SUDO_USER=owner system-agent-key password on")
    # Verify ctypes/PAM plumbing with explicit permit/deny fixture modules. This
    # is not a successful physical FIDO assertion.
    python = "${pkgs.python3}/bin/python3"
    env = "PYTHONPATH=${core}/lib/system-agent CONTROLSTACK_PAM_LIBRARY=${pkgs.pam}/lib/libpam.so.0 "
    for module, succeeds in [("pam_permit", True), ("pam_deny", False)]:
        command = env + "CONTROLSTACK_U2F_MODULE=${pkgs.pam}/lib/security/" + module + ".so " + python + " -m system_agent.security_key verify /var/lib/controlstack-security/u2f-keys owner"
        (machine.succeed if succeeds else machine.fail)(command)
    machine.fail("system-agent-key verify /var/lib/controlstack-security/u2f-keys owner")
    machine.succeed("rm /var/lib/controlstack-security/password-unlock.json")
    machine.fail("runuser -u owner -- sh -c 'printf fixture-password | pamtester hyprlock owner authenticate'")
  '';
}
