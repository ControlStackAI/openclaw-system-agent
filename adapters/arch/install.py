"""Arch UEFI/ZFS installation, invoked only by the local root setup screen.

All destructive work is restricted to the one reviewed whole disk. No host disk
is used by project tests. Target payloads are built in isolation and verified before approval or partitioning.
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
INPUTS = Path("/etc/controlstack-agent/arch-target.json")


from system_agent.install_common import (run, output, descendants, eligible, disks, disk_identity,
                                         secret_twice, timezone_choice, describe_choices, confirm_disk_erasure, export_installed_pool,
                                         payload_issue)


def check_context():
    facts = discover()
    if os.geteuid() != 0 or facts["distro_id"] != "arch" or facts["phase"] != "live":
        raise ValueError("Disk installation is available only from the Arch live image.")
    if not Path("/sys/firmware/efi").is_dir():
        raise ValueError("Restart the USB in UEFI mode. Legacy BIOS installation is not implemented.")
    if output(["findmnt", "-n", "-o", "FSTYPE", "/run"]) != "tmpfs":
        raise ValueError("Setup needs private RAM storage.")
    return facts


def prepare(node, choices, enrollment=None):
    facts = check_context()
    choices = validate_choices(choices)
    if choices['desktop'] not in ('none', 'hyprland'):
        raise ValueError('This Arch image supports Hyprland or no desktop.')
    inputs = json.loads(INPUTS.read_text())
    payload = Path(inputs['payload'])
    try:
        if not stat.S_ISREG(payload.stat().st_mode):
            raise payload_issue(payload, 'integrity')
        print('Checking the prepared Arch system before changing any disk...', flush=True)
        with payload.open('rb') as stream:
            actual = hashlib.file_digest(stream, 'sha256').hexdigest()
    except FileNotFoundError as error:
        raise payload_issue(payload, 'missing') from error
    except OSError as error:
        raise payload_issue(payload, 'unreadable') from error
    if actual != inputs['sha256']:
        raise payload_issue(payload, 'integrity')
    if output(['uname', '-r']) != inputs['kernel_release']:
        raise ValueError('The live kernel differs from the pinned target kernel.')
    if not Path('/usr/share/zfs/compatibility.d/openzfs-2.2').is_file():
        raise ValueError('The portable ZFS profile is missing.')
    if output(['modinfo', '-F', 'vermagic', 'zfs']).split()[0] != inputs['kernel_release']:
        raise ValueError('The live ZFS module does not match the target kernel.')
    from runtimes.openclaw.release_policy import resolve
    release = resolve("arch", choices.get("openclaw_release", "default"))
    actual_release = output([inputs["runtime"] + "/bin/openclaw", "--version"])
    if not re.search(r"(?<![0-9.])" + re.escape(release["version"]) + r"(?![0-9.-])", actual_release):
        raise ValueError("The prepared OpenClaw runtime differs from the selected release. No disk was changed.")
    print("Installed OpenClaw release: " + release["version"] + " (" + release["policy"] + ")", flush=True)
    area = private_dir(AREA)
    if choices.get('login_policy') == 'yubikey':
        from system_agent.security_key import validate_enrollment
        validate_enrollment(enrollment, choices['username'])
    plan = {'schema': 1, 'id': secrets.token_hex(8), 'boot_id': facts['boot_id'],
            'disk': disk_identity(node), 'choices': choices,
            'pool': 'csa' + secrets.token_hex(4), 'host_id': secrets.token_hex(4),
            'efi_uuid': str(uuid.uuid4()), 'zfs_uuid': str(uuid.uuid4()),
            'machine_id': uuid.uuid4().hex, 'installer_revision': inputs['installer_revision'],
            'payload': str(payload), 'sha256': actual, 'runtime': inputs['runtime'],
            'kernel_release': inputs['kernel_release'], 'openclaw_release': release}
    if enrollment is not None:
        plan['key_enrollment'] = enrollment
    create_private(area / (plan['id'] + '.json'), json.dumps(plan, indent=2))
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
    # Explicit legacy properties make mount(8),
    # initrd and systemd use the same dataset/mountpoint contract.
    run(["zfs", "create", "-o", "mountpoint=legacy", pool + "/ROOT/system"])
    run(["mount", "-t", "zfs", pool + "/ROOT/system", str(TARGET)])
    for dataset, directory in (("home", "home"), ("agent", "var/lib/controlstack-agent")):
        run(["zfs", "create", "-o", "mountpoint=legacy", pool + "/" + dataset])
        (TARGET / directory).mkdir(parents=True)
        run(["mount", "-t", "zfs", pool + "/" + dataset, str(TARGET / directory)])
    run(["zpool", "set", "bootfs=" + pool + "/ROOT/system", pool])
    (TARGET / "boot").mkdir()
    run(["mount", "-o", "umask=0077", efi, str(TARGET / "boot")])
    run(['unsquashfs', '-f', '-no-progress', '-d', str(TARGET), plan['payload']])
    # Copy only the immutable public runtime closure, never the live root or state.
    (TARGET / 'nix').mkdir(exist_ok=True)
    run(['cp', '-a', '/nix/.', str(TARGET / 'nix')])
    (TARGET / 'opt').mkdir(exist_ok=True)
    run(['cp', '-a', '/opt/codex', str(TARGET / 'opt')])
    from adapters.arch.target import configure, write
    from adapters.arch.owner_policy import POWER
    configure(TARGET, plan['runtime'], plan['choices'])
    write(TARGET, 'etc/machine-id', plan['machine_id'] + '\n')
    write(TARGET, 'etc/fstab',
          pool + '/ROOT/system / zfs defaults 0 0\n' +
          pool + '/home /home zfs defaults 0 0\n' +
          pool + '/agent /var/lib/controlstack-agent zfs defaults 0 0\n' +
          'PARTUUID=' + plan['efi_uuid'] + ' /boot vfat umask=0077 0 2\n')
    def chroot(*args, **kwargs):
        return run(['arch-chroot', str(TARGET), *args], **kwargs)
    chroot('zgenhostid', '-f', plan['host_id'])
    chroot('locale-gen')
    chroot('groupadd', '--system', 'controlstack-agent')
    chroot('useradd', '--system', '--gid', 'controlstack-agent', '--home-dir', '/var/lib/controlstack-agent', '--shell', '/usr/bin/nologin', 'controlstack-agent')
    owner = plan['choices']['username']
    chroot('useradd', '--create-home', '--groups', 'wheel,kvm', '--shell', '/bin/bash', owner)
    chroot('chpasswd', '-e', input=owner + ':' + password_hash + '\n')
    chroot('passwd', '-l', 'root')
    services = ['NetworkManager', 'systemd-timesyncd', 'controlstack-agent', 'controlstack-agent-boot-check']
    if plan['choices']['desktop'] == 'hyprland':
        chroot('groupadd', '--system', 'controlstack-desktop')
        for account in (owner, 'controlstack-agent'):
            chroot('usermod', '-aG', 'controlstack-desktop', account)
        services += ['sddm', 'bluetooth']
        chroot('systemctl', '--global', 'enable', 'pipewire.socket', 'pipewire-pulse.socket', 'wireplumber.service')
    if plan['choices'].get('power_policy') == 'always-on':
        services.append('controlstack-performance')
    if plan['choices'].get('login_policy') == 'yubikey':
        services.append('controlstack-key-watch')
        from system_agent.security_key import install_enrollment
        install_enrollment(TARGET, plan['key_enrollment'], plan['choices']['username'])
    chroot('systemctl', 'enable', *services)
    # Native busybox ZFS hook reads fstab for a legacy root and loads its key.
    write(TARGET, 'etc/mkinitcpio.conf',
          'MODULES=(zfs xhci_pci ahci nvme usb_storage sd_mod virtio_pci virtio_blk virtio_scsi)\n'
          'BINARIES=()\nFILES=(/etc/hostid /etc/fstab)\n'
          'HOOKS=(base udev microcode modconf kms keyboard keymap consolefont block zfs filesystems)\n'
          'COMPRESSION="zstd"\nCOMPRESSION_OPTIONS=(-T2 -3)\n')
    chroot('depmod', plan['kernel_release'])
    run(['cp', str(TARGET / 'usr/lib/modules' / plan['kernel_release'] / 'vmlinuz'), str(TARGET / 'boot/vmlinuz-linux')])
    chroot('mkinitcpio', '-k', plan['kernel_release'], '-g', '/boot/initramfs-linux.img')
    chroot('bootctl', '--esp-path=/boot', '--no-variables', 'install')
    write(TARGET, 'boot/loader/loader.conf', 'default controlstack.conf\ntimeout 4\neditor no\n')
    write(TARGET, 'boot/loader/entries/controlstack.conf',
          'title ControlStack Arch Linux\nlinux /vmlinuz-linux\ninitrd /initramfs-linux.img\n'
          'options zfs=' + pool + '/ROOT/system rw zfs_boot_only=1 console=ttyS0,115200 console=tty0' + (' ' + ' '.join(POWER['kernelParams']) if plan['choices'].get('power_policy') == 'always-on' else '') + '\n')
    # Preserve public provenance and a clean shutdown export; no forced imports.
    write(TARGET, 'etc/controlstack-agent/installed-image.json', json.dumps({k: plan[k] for k in ('sha256', 'runtime', 'kernel_release', 'installer_revision', 'openclaw_release')}, indent=2) + '\n')
    # Create fresh resident state. No live workspace, transcript, config or token is copied.
    account_line = next(line for line in (TARGET / "etc/passwd").read_text().splitlines() if line.startswith("controlstack-agent:"))
    _, _, uid, gid, *_ = account_line.split(":")
    state = private_dir(TARGET / "var/lib/controlstack-agent")
    lifecycle = private_dir(state / "lifecycle")
    handoff = validate_handoff({"schema": 1, "target_distro": "arch", "installation_boot_id": plan["boot_id"],
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
    print("\nFirst we will choose your setup, then review where to install it. This version installs Arch Linux onto one entire disk; it does not preserve that disk or set up dual boot.")
    from system_agent.choices import validate_partial
    choices = dict(validate_partial(suggestions or {}))
    if choices:
        print("\nSaved setup choices (still subject to your review):")
        describe_choices(choices)
        if choose("Use these choices and ask about anything missing?", ["Use these choices", "Choose again"]) == 2:
            choices = {}
    from system_agent.interview import interview
    choices = interview(choices, choose, timezone_choice, describe_choices, desktops=("hyprland", "none"))
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
    keymap = {'us': 'us', 'gb': 'uk', 'de': 'de-latin1', 'fr': 'fr', 'es': 'es'}[choices['keyboard']]
    run(['loadkeys', '-C', '/dev/tty0', '--quiet', keymap])
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
