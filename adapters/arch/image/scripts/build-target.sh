#!/usr/bin/env bash
# Separate native target payload: never cloned from the live session/root.
set -euo pipefail
live="$1"
target="$2"
kernel="$3"
mkdir -p "$target"
mount --bind "$target" "$target"
trap 'umount -R "$target" || true' EXIT
mapfile -t packages < /repo/config/target-packages.txt
# The installer and target use the same immutable archive and signature policy.
for attempt in 1 2 3; do
    if pacstrap -G -M -c -C "$live/etc/pacman.conf" "$target" "${packages[@]}"; then break; fi
    if [[ "$attempt" == 3 ]]; then exit 1; fi
    echo "Retrying the signed target package transaction using the public archive cache ($attempt/3)." >&2
    sleep 5
done
python - "$target" <<'CHECK_DB'
import sys
from pathlib import Path
for repo in ('core', 'extra'):
    assert (Path(sys.argv[1]) / 'var/lib/pacman/sync' / (repo + '.db')).read_bytes() == (Path('/downloads') / (repo + '.db')).read_bytes(), 'Frozen repository changed: ' + repo
CHECK_DB
mkdir -p "$target/root/agent-downloads"
cp /downloads/zfs-*.pkg.tar.zst* "$target/root/agent-downloads/"
mkdir -p "$target/etc/pacman.d/gnupg"
cp -a "$live/etc/pacman.d/gnupg/." "$target/etc/pacman.d/gnupg/"
cp "$live/etc/pacman.conf" "$target/etc/pacman.conf"
# Kernel/module/utilities are one locked transaction; upgrades require a new reviewed lock.
arch-chroot "$target" /bin/bash -c 'pacman -U --noconfirm /root/agent-downloads/*.pkg.tar.zst'
arch-chroot "$target" modinfo -k "$kernel" -F vermagic zfs | grep -F "$kernel "
arch-chroot "$target" pacman -Q > /repo/.build/target-packages.txt
# A stable kernel cannot be updated independently from its external ZFS module.
sed -i '/^\[options\]/a IgnorePkg = linux linux-headers zfs-linux zfs-utils' "$target/etc/pacman.conf"
rm -rf "$target/root/agent-downloads" "$target/etc/pacman.d/gnupg" "$target/var/cache/pacman/pkg/"* "$target/var/log/"*
rm -f "$target/etc/machine-id" "$target/var/lib/dbus/machine-id"
# Reinitialize a target-local keyring at first boot (no builder private keys).
cat > "$target/etc/systemd/system/controlstack-pacman-keyring.service" <<'UNIT'
[Unit]
Description=Initialize local package signature keyring
ConditionPathExists=!/etc/pacman.d/gnupg/pubring.gpg
After=local-fs.target
[Service]
Type=oneshot
ExecStart=/usr/bin/pacman-key --init
ExecStart=/usr/bin/pacman-key --populate archlinux
[Install]
WantedBy=multi-user.target
UNIT
arch-chroot "$target" systemctl enable controlstack-pacman-keyring.service
find "$target" -xdev -exec touch -h -d "@$SOURCE_DATE_EPOCH" {} +
mkdir -p /repo/.build/remaster/iso/arch/controlstack
env -u SOURCE_DATE_EPOCH mksquashfs "$target" /repo/.build/remaster/iso/arch/controlstack/target.sfs -noappend -comp zstd -Xcompression-level 6 -processors "${BUILD_JOBS:-2}" -mkfs-time "$SOURCE_DATE_EPOCH" -all-time "$SOURCE_DATE_EPOCH"
python - "$live" "$kernel" <<'PY'
import hashlib,json,sys
from pathlib import Path
payload=Path('/repo/.build/remaster/iso/arch/controlstack/target.sfs')
with payload.open('rb') as stream: digest=hashlib.file_digest(stream,'sha256').hexdigest()
conf=Path(sys.argv[1])/'etc/controlstack-agent'
conf.mkdir(parents=True,exist_ok=True)
(conf/'image-inputs.json').write_text(Path('/repo/inputs.lock.json').read_text())
(conf/'arch-target.json').write_text(json.dumps({
 'payload':'/run/archiso/bootmnt/arch/controlstack/target.sfs','sha256':digest,
 'kernel_release':sys.argv[2], 'runtime':Path('/repo/runtime-path').read_text().strip(),
 'installer_revision':'6d02675cd8ce3323589ec9d7f44e99fcf50487a2'},indent=2)+'\n')
PY
