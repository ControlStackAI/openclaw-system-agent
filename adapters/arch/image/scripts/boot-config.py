"""Keep the separate installation payload mounted in every Arch boot entry."""
from pathlib import Path
import re
import sys


def configure(root, old_uuid, new_uuid):
    changed = 0
    for pattern in ('*.conf', '*.cfg'):
        for path in Path(root).rglob(pattern):
            text = path.read_text().replace(old_uuid, new_uuid).replace(
                'Arch Linux install medium', 'ControlStackAI Arch OpenClaw System Assistant')
            text = text.replace('cms_verify=y', 'cms_verify=n')
            lines = []
            for line in text.splitlines():
                # Include GRUB loopback entries used by Ventoy, but not the
                # systemd-boot kernel-path directive or Memtest entries.
                if line.lstrip().startswith(('options ', 'APPEND ', 'linux ', 'linuxefi ')) and 'archisobasedir=' in line:
                    line = re.sub(r'(?<!\S)(?:copytoram(?:=[^\s]+)?|console=[^\s]+)(?=\s|$)', '', line).rstrip()
                    # Arch's automatic RAM mode copies only airootfs, then
                    # unmounts bootmnt. target.sfs must stay available there.
                    line += ' copytoram=n console=ttyS0,115200 console=tty0'
                    changed += 1
                lines.append(line)
            path.write_text('\n'.join(lines) + '\n')
    if not changed:
        raise ValueError('No Arch live boot entries found; refusing an image without its payload mount policy.')


if __name__ == '__main__':
    configure(*sys.argv[1:])
