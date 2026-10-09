"""NixOS UEFI/ZFS installation, invoked only by the local root setup screen.

All destructive work is restricted to the one reviewed whole disk. No host disk
is used by project tests. Target builds finish before approval or partitioning.
"""
import getpass
import hashlib
import json
import os
import re
import secrets
import stat
import subprocess
import uuid
from pathlib import Path
from zoneinfo import available_timezones
from system_agent.profile import DESKTOPS, LAYOUTS, LOCALES, validate_choices
from system_agent.facts import discover
from system_agent.handoff import validate as validate_handoff
from system_agent.state import create_private, private_dir

AREA = Path("/run/controlstack-install")
TARGET = Path("/mnt/controlstack-target")
INPUTS = Path("/etc/controlstack-agent/install-inputs.json")


from system_agent.install_common import (run, output, descendants, eligible, disks, disk_identity,
                                         secret_twice, timezone_choice, describe_choices, confirm_disk_erasure, export_installed_pool)


def check_context():
    facts = discover()
    if os.geteuid() != 0 or facts["distro_id"] != "nixos" or facts["phase"] != "live":
        raise ValueError("Disk installation is available only from the NixOS live image.")
    if not Path("/sys/firmware/efi").is_dir():
        raise ValueError("Restart the USB in UEFI mode. Legacy BIOS installation is not implemented.")
    if output(["findmnt", "-n", "-o", "FSTYPE", "/run"]) != "tmpfs":
        raise ValueError("Setup needs private RAM storage.")
    return facts


def nix_string(value):
    return json.dumps(value).replace("${", "\\${")


def render_target(plan, inputs):
    c = validate_choices(plan["choices"])
    q = nix_string
    terminal_exec = ('${pkgs.ghostty}/bin/ghostty --title="System Assistant" -e'
                     if c["desktop"] == "hyprland" else
                     '${pkgs.xterm}/bin/xterm -T "System Assistant" -fa Monospace -fs 12 -bg "#0b1626" -fg "#dce7f7" -geometry 100x30 -e')
    return f'''import {q(inputs["nixpkgs"] + "/nixos")} {{
  system = "x86_64-linux";
  configuration = {{ config, pkgs, lib, ... }}: {{
    imports = [ {q(inputs["source"] + "/adapters/nixos/module.nix")}
      {q(inputs["source"] + "/adapters/nixos/networking.nix")}
      (import {q(inputs["source"] + "/adapters/nixos/owner-policy.nix")} {{
        owner = {q(c["username"])}; core = builtins.storePath {q(inputs["core"])};
        powerPolicy = {q(c.get("power_policy", "standard"))}; loginPolicy = {q(c.get("login_policy", "password"))}; }})
      (import {q(inputs["source"] + "/adapters/nixos/desktop.nix")} {{ desktop = {q(c["desktop"])}; aiTools = {"builtins.storePath " + q(inputs["ai_tools"]) if "ai_tools" in inputs else "null"}; }}) ];
    services.controlstackAgent = {{
      enable = true; mutableProviderSetup = true; workspaceExecution = true; zfs.enable = true;
      desktopOwner = {q(c["username"]) if c["desktop"] == "hyprland" else "null"};
      package = builtins.storePath {q(inputs["runtime"])};
      corePackage = builtins.storePath {q(inputs["core"])};
    }};
    hardware.enableRedistributableFirmware = true;
    environment.etc."controlstack-agent/build-inputs.json".text = builtins.toJSON {{
      nixpkgs = builtins.storePath {q(inputs["nixpkgs"])};
      source = builtins.storePath {q(inputs["source"])};
    }};
    boot.initrd.availableKernelModules = [ "xhci_pci" "ahci" "nvme" "usb_storage" "sd_mod" "virtio_pci" "virtio_blk" "virtio_scsi" ];
    boot.kernelParams = [ "console=ttyS0,115200" "console=tty0" ];
    boot.loader.systemd-boot.enable = true;
    boot.loader.efi.canTouchEfiVariables = false;
    boot.zfs.requestEncryptionCredentials = true;
    networking.hostName = {q(c["hostname"])};
    networking.hostId = {q(plan["host_id"])};
    services.timesyncd.enable = true;
    services.openssh.enable = false;
    time.timeZone = {q(c["timezone"])};
    i18n.defaultLocale = {q(c["locale"])};
    services.xserver.xkb.layout = {q(c["keyboard"])};
    console.useXkbConfig = true;
    console.earlySetup = true;
    users.mutableUsers = true;
    users.users.{c["username"]} = {{
      isNormalUser = true; extraGroups = [ "wheel" "networkmanager" "kvm" ];
      hashedPasswordFile = "/var/lib/controlstack-owner.password";
    }};
    security.sudo.extraRules = [ {{ users = [ {q(c["username"])} ]; commands = [
      {{ command = "${{pkgs.lib.getBin (builtins.storePath {q(inputs["core"])})}}/bin/system-agent-setup"; options = [ "NOPASSWD" ]; }}
    ]; }} ];
    fileSystems."/" = {{ device = {q(plan["pool"] + "/ROOT/system")}; fsType = "zfs"; }};
    fileSystems."/home" = {{ device = {q(plan["pool"] + "/home")}; fsType = "zfs"; }};
    fileSystems."/var/lib/controlstack-agent" = {{ device = {q(plan["pool"] + "/agent")}; fsType = "zfs"; }};
    fileSystems."/boot" = {{ device = {q("/dev/disk/by-partuuid/" + plan["efi_uuid"])}; fsType = "vfat"; options = [ "umask=0077" ]; }};
    environment.systemPackages = [ pkgs.xterm pkgs.curl pkgs.whois pkgs.python3
      (pkgs.writeTextDir "share/applications/controlstack-agent.desktop"
        config.environment.etc."xdg/autostart/controlstack-agent.desktop".text) ];
    environment.interactiveShellInit = \'\'
      if [ "$(id -un)" = {c["username"]} ] && [ -t 0 ] && [ "$(tty)" = /dev/tty1 ] &&
         [ "\'\'${{CONTROLSTACK_SETUP_OPENED:-}}" != 1 ]; then
        export CONTROLSTACK_SETUP_OPENED=1
        sudo {inputs["core"]}/bin/system-agent-setup
      fi
    \'\';
    environment.etc."xdg/autostart/controlstack-agent.desktop".text = \'\'
      [Desktop Entry]
      Type=Application
      Name=System Assistant
      Comment=Talk to your resident computer assistant
      Icon=computer
      Categories=System;
      Exec={terminal_exec} sudo {inputs["core"]}/bin/system-agent-setup
      Terminal=false
    \'\';
    nix.settings.experimental-features = [ "nix-command" "flakes" ];
    system.stateVersion = "26.05";
  }};
}}
'''


def prepare(node, choices, enrollment=None):
    facts = check_context()
    choices = validate_choices(choices)
    memory_kib = int(next(line.split()[1] for line in Path("/proc/meminfo").read_text().splitlines() if line.startswith("MemTotal:")))
    if choices["desktop"] != "none" and memory_kib < 7 * 1024 * 1024:
        raise ValueError("Desktop preparation needs at least 8 GB of usable RAM in this development image. Choose no desktop or use a computer with more memory. No disk was changed.")
    inputs = json.loads(INPUTS.read_text())
    if not Path(inputs["zfs_compatibility"]).is_file():
        raise ValueError("The pinned portable ZFS feature profile is missing from this image.")
    if choices.get('login_policy') == 'yubikey':
        from system_agent.security_key import validate_enrollment
        validate_enrollment(enrollment, choices['username'])
    from runtimes.openclaw.release_policy import resolve
    release = resolve("nixos", choices.get("openclaw_release", "default"))
    print("Installed OpenClaw release: " + release["version"] + " (image-pinned)", flush=True)
    area = private_dir(AREA)
    plan = {"schema": 1, "id": secrets.token_hex(8), "boot_id": facts["boot_id"],
            "disk": disk_identity(node), "choices": validate_choices(choices),
            "pool": "csa" + secrets.token_hex(4), "host_id": secrets.token_hex(4),
            "efi_uuid": str(uuid.uuid4()), "zfs_uuid": str(uuid.uuid4()),
            "machine_id": uuid.uuid4().hex, "installer_revision": inputs["installer_revision"],
            "openclaw_release": release}
    if enrollment is not None:
        plan['key_enrollment'] = enrollment
    expression = area / (plan["id"] + ".nix")
    create_private(expression, render_target(plan, inputs))
    print("\nPreparing your chosen system before changing any disk. This may take a while.", flush=True)
    log_path = area / (plan["id"] + ".build.log")
    create_private(log_path, "")
    with log_path.open("a") as log:
        with subprocess.Popen(["nix-build", str(expression), "-A", "config.system.build.toplevel", "--no-out-link"],
                              stdout=subprocess.PIPE, stderr=log, text=True) as build:
            while True:
                try:
                    stdout, _ = build.communicate(timeout=30)
                    break
                except subprocess.TimeoutExpired:
                    print("Still preparing your system. Your disk has not been changed.", flush=True)
                except BaseException:
                    build.terminate()
                    try:
                        build.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        build.kill()
                    raise
            if build.returncode:
                raise ValueError("I could not prepare this system. No disk was changed. Technical details are saved in the private setup log.")
    plan["system"] = stdout.strip()
    if not re.fullmatch(r"/nix/store/[a-z0-9]{32}-nixos-system-[^/\s]+", plan["system"]):
        raise ValueError("The prepared system did not produce one expected Nix store path.")
    plan["expression"] = str(expression)
    # Root-owned file; agent account cannot rewrite the prepared plan or approval.
    create_private(area / (plan["id"] + ".json"), json.dumps(plan, indent=2))
    return plan


def recheck(plan):
    facts = check_context()
    if facts["boot_id"] != plan["boot_id"]:
        raise ValueError("This plan belongs to an earlier boot. Prepare a new plan.")
    matches = [n for n in disks() if disk_identity(n) == plan["disk"]]
    if len(matches) != 1:
        raise ValueError("The disk changed or is now in use. Nothing further will be erased.")
    disk = Path(plan["disk"]["name"])
    if not stat.S_ISBLK(disk.stat().st_mode):
        raise ValueError("The selected target is not a whole block device.")
    return str(disk)


def install(plan, confirmation, password, encryption_key=None):
    expected = "ERASE " + str(plan["disk"]["serial"] or plan["disk"]["wwn"])
    if confirmation != expected:
        raise ValueError("Disk erasure was not confirmed.")
    if not password or (plan["choices"]["encrypt"] and not encryption_key):
        raise ValueError("Account password and requested encryption key must be supplied through protected input.")
    if plan["choices"]["encrypt"] and (not 8 <= len(encryption_key.encode("utf-8")) <= 512 or any(c in encryption_key for c in "\n\r\x00")):
        raise ValueError("Use an unlock passphrase of 8 to 512 UTF-8 bytes on one line.")
    stored = json.loads((AREA / (plan["id"] + ".json")).read_text())
    if stored != plan:
        raise ValueError("The prepared plan changed.")
    disk = recheck(plan)
    if TARGET.is_symlink() or (TARGET.exists() and any(TARGET.iterdir())) or os.path.ismount(TARGET):
        raise ValueError("The installation mount point is already occupied.")
    TARGET.mkdir(parents=True, exist_ok=True)
    if plan['choices'].get('login_policy') == 'yubikey':
        from system_agent.security_key import validate_enrollment
        validate_enrollment(plan.get('key_enrollment'), plan['choices']['username'])
    # Consume approval before the first destructive operation, even if it fails.
    create_private(AREA / (plan["id"] + ".started"), "approved locally\n")
    password_hash = run(["mkpasswd", "--method=yescrypt", "--stdin"], input=password + "\n", capture_output=True).stdout.strip()
    print("\nInstalling to the reviewed disk. Keep the computer powered on.", flush=True)
    run(["sgdisk", "--zap-all", "--new=1:0:+1G", "--typecode=1:EF00",
         "--partition-guid=1:" + plan["efi_uuid"], "--new=2:0:0", "--typecode=2:BF01",
         "--partition-guid=2:" + plan["zfs_uuid"], disk])
    run(["partprobe", disk])
    run(["udevadm", "settle"])
    efi = "/dev/disk/by-partuuid/" + plan["efi_uuid"]
    zfs = "/dev/disk/by-partuuid/" + plan["zfs_uuid"]
    run(["mkfs.fat", "-F", "32", efi])
    pool = plan["pool"]
    command = ["zpool", "create", "-f", "-o", "ashift=12", "-o", "compatibility=openzfs-2.2",
               "-O", "compression=lz4", "-O", "atime=off", "-O", "mountpoint=none", "-R", str(TARGET)]
    if plan["choices"]["encrypt"]:
        command += ["-O", "encryption=aes-256-gcm", "-O", "keyformat=passphrase", "-O", "keylocation=prompt"]
    run(command + [pool, zfs], input=(encryption_key + "\n") if encryption_key else None)
    run(["zfs", "create", "-o", "mountpoint=none", pool + "/ROOT"])
    # NixOS fileSystems owns these mounts. Use legacy properties so mount(8),
    # initrd and systemd all use the same explicit dataset/mountpoint contract.
    run(["zfs", "create", "-o", "mountpoint=legacy", pool + "/ROOT/system"])
    run(["mount", "-t", "zfs", pool + "/ROOT/system", str(TARGET)])
    for dataset, directory in (("home", "home"), ("agent", "var/lib/controlstack-agent")):
        run(["zfs", "create", "-o", "mountpoint=legacy", pool + "/" + dataset])
        (TARGET / directory).mkdir(parents=True)
        run(["mount", "-t", "zfs", pool + "/" + dataset, str(TARGET / directory)])
    run(["zpool", "set", "bootfs=" + pool + "/ROOT/system", pool])
    (TARGET / "boot").mkdir()
    run(["mount", "-o", "umask=0077", efi, str(TARGET / "boot")])
    (TARGET / "etc/nixos").mkdir(parents=True)
    create_private(TARGET / "etc/machine-id", plan["machine_id"] + "\n")
    # Machine identity is public system metadata, read by unprivileged services.
    (TARGET / "etc/machine-id").chmod(0o644)
    create_private(TARGET / "var/lib/controlstack-owner.password", password_hash + "\n")
    # Keep the exact reproducible expression and its source references on target.
    create_private(TARGET / "etc/nixos/target.nix", Path(plan["expression"]).read_text())
    create_private(TARGET / "etc/nixos/README", "Build with nix-build target.nix -A config.system.build.toplevel.\nThis records the original pinned system; review changes before rebuilding.\n")
    run(["nixos-install", "--root", str(TARGET), "--system", plan["system"], "--no-root-passwd", "--no-channel-copy"])
    # Create fresh resident state. No live workspace, transcript, config or token is copied.
    account_line = next(line for line in (TARGET / "etc/passwd").read_text().splitlines() if line.startswith("controlstack-agent:"))
    _, _, uid, gid, *_ = account_line.split(":")
    state = private_dir(TARGET / "var/lib/controlstack-agent")
    lifecycle = private_dir(state / "lifecycle")
    create_private(lifecycle / "openclaw-release.json", json.dumps(plan["openclaw_release"], indent=2))
    if plan['choices'].get('login_policy') == 'yubikey':
        from system_agent.security_key import install_enrollment
        install_enrollment(TARGET, plan['key_enrollment'], plan['choices']['username'])
    handoff = validate_handoff({"schema": 1, "target_distro": "nixos", "installation_boot_id": plan["boot_id"],
        "target_machine_id": plan["machine_id"], "root_fstype": "zfs", "root_identity": pool + "/ROOT/system",
        "installer_revision": plan["installer_revision"]})
    create_private(lifecycle / "installation.json", json.dumps(handoff, indent=2))
    create_private(lifecycle / "choices.json", json.dumps(plan["choices"], indent=2))
    workspace = private_dir(state / "workspace")
    create_private(workspace / "USER.md", "# Owner's chosen system\n\nThese choices were reviewed on the local setup screen; they do not authorize future changes.\n\n" +
                   "\n".join(f"- {key}: {value}" for key, value in plan["choices"].items()) +
                   "\n- Purpose: maintain this installed system; do not repeat installation.\n- Filesystem: ZFS with portable snapshots and independent backups to arrange.\n")
    if "agent_name" in plan["choices"]:
        from system_agent.profile import initialize_agent_name
        initialize_agent_name(state, plan["choices"]["agent_name"])
    for path in [state, *state.rglob("*")]:
        os.chown(path, int(uid), int(gid))
    # Rebuild sources are references of the installed system closure, copied by nixos-install.
    run(["sync"])
    run(["umount", str(TARGET / "boot")])
    for directory in ("var/lib/controlstack-agent", "home", ""):
        run(["umount", str(TARGET / directory)])
    export_installed_pool(pool)
    print("\nInstallation files are ready. Shut down before removing the USB, then turn the computer on again.\n"
          "Sign in with your new local account. System Assistant will open and help you sign in to OpenClaw again.\n"
          "The installed boot still needs to be verified after that restart.", flush=True)


def interactive(state, suggestions=None):
    from system_agent.setup import choose
    check_context()
    print("\nFirst we will choose your setup, then review where to install it. This version installs NixOS onto one entire disk; it does not preserve that disk or set up dual boot.")
    from system_agent.choices import validate_partial
    choices = dict(validate_partial(suggestions or {}))
    if choices:
        print("\nSaved setup choices (still subject to your review):")
        describe_choices(choices)
        if choose("Use these choices and ask about anything missing?", ["Use these choices", "Choose again"]) == 2:
            choices = {}
    from system_agent.interview import interview
    choices = interview(choices, choose, timezone_choice, describe_choices)
    if choose("Do you have a disk whose contents can all be replaced?", ["Go back and preserve my existing setup", "Yes, show eligible disks"]) != 2:
        return
    available = disks()
    if not available:
        raise ValueError("No unused internal disk with a stable identity and at least 32 GiB is available. Mounted, USB and removable disks are protected.")
    labels = [f"{json.dumps(n['model'] or 'Disk')} — {int(n['size']) // 1024**3} GiB — serial {n['serial'] or n['wwn']} ({n['name']})" for n in available]
    index = choose("Which disk should hold the new system?", labels + ["Cancel"])
    if index > len(available):
        return
    node = available[index - 1]
    enrollment = None
    if choices.get('login_policy') == 'yubikey':
        print('Your YubiKey will be required at sign-in, and removing it will lock the desktop.\n'
              'Password screen unlock starts enabled; the unlocked desktop can change it with a key touch.\n'
              'Disk encryption keeps its separate passphrase. Keep the enrolled key available after reboot.')
    if choices.get('login_policy') == 'yubikey':
        from system_agent.security_key import enroll
        enrollment = enroll(choices['username'])
    plan = prepare(node, choices, enrollment)
    print("\nPlease review your installation:")
    if choices["desktop"] == "hyprland":
        print("OpenClaw will have full control of your logged-in Hyprland desktop: apps, windows, screenshots, mouse, keyboard and clipboard. The center island can stop desktop access.")
    print("  Disk: " + labels[index - 1])
    describe_choices(choices)
    print("All contents of that disk will be lost. Other disks are excluded.\n"
          "Layout: 1 GiB startup partition, remaining space ZFS; separate system, home and agent-state datasets.\n"
          "OpenClaw runs as its own account with no administrator access. Your account can approve administration.\n"
          "No remote login or automatic updates. ZFS compatibility is limited to the OpenZFS 2.2 feature set.\n"
          "Snapshots are not independent backups. Keep the USB for recovery and arrange an external backup.\n"
          "Before proceeding, separately back up anything on the selected disk that you need to keep.")
    confirmation = confirm_disk_erasure(plan["disk"])
    if confirmation is None:
        print("Cancelled. No disk changes were made.")
        return
    # Use exactly the target console map before secrets are typed. Otherwise a
    # non-US keyboard can produce a different password after reboot.
    console_config = (Path(plan["system"]) / "etc/vconsole.conf").read_text()
    keymap = next(line.removeprefix("KEYMAP=") for line in console_config.splitlines() if line.startswith("KEYMAP="))
    if not keymap.startswith("/nix/store/") or not Path(keymap).is_file():
        raise ValueError("The prepared keyboard map is unavailable. No disk was changed.")
    run(["loadkeys", "-C", "/dev/tty0", "--quiet", keymap])
    print("Your selected keyboard layout is now active for password entry and for the installed system.")
    password = secret_twice("Password for your local account (hidden): ")
    encryption_key = secret_twice("Disk unlock passphrase (hidden; keep a safe copy elsewhere): ") if choices["encrypt"] else None
    try:
        install(plan, confirmation, password, encryption_key)
    finally:
        password = encryption_key = None
    if choose("Ready to shut down and start your installed system?", ["Shut down, then remove the USB", "Stay in this USB session"]) == 1:
        run(["systemctl", "poweroff"])
    return {"state": "installed-awaiting-reboot", "disk_erasure_approved": True,
            "message": "Installation completed. An independent boot with the USB removed is still required."}
