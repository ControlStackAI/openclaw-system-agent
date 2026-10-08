#!/usr/bin/env bash
set -euo pipefail
cd /repo
python scripts/inputs.py --check
mapfile -t values < <(python - <<'PY'
import json
l=json.load(open('inputs.lock.json'))
for v in [l['arch']['iso']['name'], l['arch']['signer'], l['arch']['snapshot'], l['arch']['kernel_release'], l['arch']['kernel_package_version'], l['codex']['version'], l['codex']['package']['name'], l['zfs']['signer']]: print(v)
PY
)
downloads="/downloads"
iso="$downloads/${values[0]}"
snapshot="${values[2]}"
kernel="${values[3]}"
codex_version="${values[5]}"
workspace="/repo/.build/remaster"
# A subsequent build replaces only the previous disposable build tree.
if mountpoint -q "$workspace/root/proc"; then
    echo 'Previous chroot is still mounted; clean it up before rebuilding.' >&2
    exit 1
fi
rm -rf "$workspace"
mkdir -p "$workspace/gnupg" /repo/dist
chmod 700 "$workspace/gnupg"
gpg --homedir "$workspace/gnupg" --import config/arch-iso-signing-key.asc config/archzfs-signing-key.asc
gpg --homedir "$workspace/gnupg" --status-fd 1 --verify "$iso.sig" "$iso" > "$workspace/iso-signature.txt"
grep -Eq "^\[GNUPG:\] VALIDSIG [0-9A-F]+ .*${values[1]}$|^\[GNUPG:\] VALIDSIG ${values[1]} " "$workspace/iso-signature.txt"

xorriso -osirrox on -indev "$iso" -extract / "$workspace/iso" -extract_boot_images "$workspace/boot-images"
chmod -R u+w "$workspace/iso"
unsquashfs -processors "${BUILD_JOBS:-2}" -d "$workspace/root" "$workspace/iso/arch/x86_64/airootfs.sfs"
root="$workspace/root"
# pacman's space checks require the chroot itself to be a mount point.
mount --bind "$root" "$root"
trap 'umount -R "$root" || true' EXIT
rm -f "$root/etc/resolv.conf"
cp /etc/resolv.conf "$root/etc/resolv.conf"
cp /repo/inputs.lock.json "$root/root/agent-inputs.json"
mkdir -p "$root/root/agent-downloads"
cp "$downloads/"*.db "$downloads/"zfs-*.pkg.tar.zst* "$downloads/${values[6]}" "$root/root/agent-downloads/"
# Persist only public package archives; pacman checks their signatures on use.
package_cache="/repo/.build/pacman-cache/${snapshot//\//-}"
mkdir -p "$package_cache" "$root/var/cache/pacman/pkg"
cp "$downloads/"linux-*.pkg.tar.zst "$package_cache/"
mount --bind "$package_cache" "$root/var/cache/pacman/pkg"
cp /repo/config/archzfs-signing-key.asc "$root/root/archzfs-signing-key.asc"
cp /repo/scripts/configure-root.sh "$root/root/agent-build.sh"
arch-chroot "$root" /bin/bash /root/agent-build.sh

bash /repo/scripts/build-target.sh "$root" "$workspace/target" "$kernel"

cp -a /runtime/nix "$root/nix"
# Staging was copied by the builder user; installed runtime files belong to root.
chown -Rh 0:0 "$root/nix"
chmod 0755 "$root/nix" "$root/nix/store"
cp /repo/runtime-path "$root/root/controlstack-runtime-path"
cp /repo/scripts/openclaw-overlay.py "$root/root/openclaw-overlay.py"
arch-chroot "$root" python /root/openclaw-overlay.py
arch-chroot "$root" systemctl disable systemd-networkd.service systemd-networkd.socket systemd-networkd-wait-online.service iwd.service systemd-resolved.service
arch-chroot "$root" systemctl enable NetworkManager.service systemd-timesyncd.service controlstack-agent.service
rm -f "$root/etc/resolv.conf"
ln -s /run/NetworkManager/resolv.conf "$root/etc/resolv.conf"
arch-chroot "$root" pacman -Q > "$workspace/iso/arch/pkglist.x86_64.txt"
arch-chroot "$root" /opt/codex/bin/codex --version | grep -Fx "codex-cli $codex_version"
arch-chroot "$root" modinfo -k "$kernel" -F vermagic zfs | grep -F "$kernel "
test -f "$root/usr/lib/modules/$kernel/vmlinuz"
# Regenerate the live initramfs against the matching new kernel, never the host kernel.
arch-chroot "$root" depmod "$kernel"
# Do not pass -c: it disables the ArchISO live-boot configuration drop-in.
arch-chroot "$root" mkinitcpio -k "$kernel" -g /root/agent-initramfs.img
arch-chroot "$root" lsinitcpio /root/agent-initramfs.img | grep -Fx 'hooks/archiso'
cp "$root/usr/lib/modules/$kernel/vmlinuz" "$workspace/iso/arch/boot/x86_64/vmlinuz-linux"
cp "$root/root/agent-initramfs.img" "$workspace/iso/arch/boot/x86_64/initramfs-linux.img"

# Separate our live-medium identity from the stock ISO on the same Ventoy disk.
mapfile -t identity < <(python - <<'PY'
from datetime import datetime, timezone
import os
# ISO9660 UUIDs encode a timestamp. Derive a stable, image-specific timestamp
# from the full lock, rather than using the builder clock or colliding variants.
identity=int(os.environ["IMAGE_ID"][:16],16)
now=datetime.fromtimestamp(946684800 + (identity // 100) % 2524608000,timezone.utc)
hundredths=f'{identity % 100:02d}'
print(now.strftime('%Y%m%d%H%M%S')+hundredths)
print(now.strftime('%Y-%m-%d-%H-%M-%S-')+hundredths)
PY
)
uuid="${identity[1]}"
printf '%s\n' "${identity[0]}" > "$workspace/iso-modification-date"
old_uuid=$(basename "$(find "$workspace/iso/boot" -maxdepth 1 -name '*.uuid' -print -quit)" .uuid)
test -n "$old_uuid"
find "$workspace/iso/boot" -maxdepth 1 -name '*.uuid' -delete
touch "$workspace/iso/boot/$uuid.uuid"
python - "$workspace/iso" "$old_uuid" "$uuid" <<'PY'
from pathlib import Path
import sys
root=Path(sys.argv[1])
for pattern in ('*.conf','*.cfg'):
    for path in root.rglob(pattern):
        text=path.read_text().replace(sys.argv[2],sys.argv[3]).replace('Arch Linux install medium','ControlStackAI Arch OpenClaw System Assistant')
        # The stock CMS signature cannot authenticate our changed squashfs.
        text=text.replace('cms_verify=y','cms_verify=n')
        text='\n'.join(line + ' console=ttyS0,115200 console=tty0' if line.lstrip().startswith(('options ', 'APPEND ')) else line for line in text.splitlines()) + '\n'
        path.write_text(text)
PY

# Rebuild the appended FAT image as well: UEFI boots its copy of these files.
mkdir -p "$workspace/efi-tree"
mcopy -s -i "$workspace/boot-images/eltorito_img2_uefi.img" '::*' "$workspace/efi-tree/"
cp "$workspace/iso/arch/boot/x86_64/"* "$workspace/efi-tree/arch/boot/x86_64/"
cp -a "$workspace/iso/loader/." "$workspace/efi-tree/loader/"
find "$workspace/efi-tree" -exec touch -h -d "@$SOURCE_DATE_EPOCH" {} +
truncate -s 512M "$workspace/efi.img"
mkfs.fat --invariant -F 32 -n AGENT_EFI "$workspace/efi.img"
mcopy -s -i "$workspace/efi.img" "$workspace/efi-tree/"* ::/

# Detach the shared public cache before scrubbing the sealed live filesystem.
umount "$root/var/cache/pacman/pkg"
# Scrub disposable build inputs, caches and generated IDs before sealing the root.
rm -rf "$root/root/agent-downloads" "$root/root/agent-inputs.json" "$root/root/agent-build.sh" "$root/root/archzfs-signing-key.asc" "$root/root/agent-initramfs.img" "$root/var/cache/pacman/pkg/"* "$root/var/log/"*
: > "$root/etc/machine-id"
rm -f "$root/var/lib/dbus/machine-id"
rm -f "$root/root/controlstack-runtime-path" "$root/root/openclaw-overlay.py"
rm -rf "$root/etc/pacman.d/gnupg"
find "$root" -xdev -exec touch -h -d "@$SOURCE_DATE_EPOCH" {} +
find "$workspace/efi-tree" -exec touch -h -d "@$SOURCE_DATE_EPOCH" {} +
test ! -e "$root/root/.codex/auth.json"
umount "$root"
trap - EXIT
bash /repo/scripts/seal-image.sh
