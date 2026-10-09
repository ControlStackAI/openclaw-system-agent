import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('arch_boot_config', Path(__file__).resolve().parents[1] / 'adapters/arch/image/scripts/boot-config.py')
boot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(boot)


class ArchBootConfiguration(unittest.TestCase):
    def test_all_live_entry_types_keep_payload_mounted_and_memtest_is_unchanged(self):
        samples = {
            'loader/entries/live.conf': 'linux /arch/boot/x86_64/vmlinuz-linux\noptions archisobasedir=arch archisosearchuuid=old copytoram=y console=ttyS1\n',
            'boot/syslinux/live.cfg': 'APPEND archisobasedir=arch archisosearchuuid=old copytoram cms_verify=y\n',
            'boot/grub/loopback.cfg': ' linux /arch/boot/x86_64/vmlinuz-linux archisobasedir=arch img_loop="${iso_path}"\n linux /boot/memtest86+/memtest\n',
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, text in samples.items():
                p = root / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text)
            boot.configure(root, 'old', 'new')
            for name in samples:
                contents = (root / name).read_text()
                for line in contents.splitlines():
                    if 'archisobasedir=' in line:
                        self.assertEqual(line.split().count('copytoram=n'), 1)
                        self.assertNotIn('copytoram=y', line)
                        self.assertNotIn('console=ttyS1', line)
                        self.assertIn('console=tty0', line)
                self.assertNotIn('archisosearchuuid=old', contents)
            self.assertIn('linux /arch/boot/x86_64/vmlinuz-linux\n', (root / 'loader/entries/live.conf').read_text())
            self.assertIn(' linux /boot/memtest86+/memtest\n', (root / 'boot/grub/loopback.cfg').read_text())
            self.assertIn('img_loop="${iso_path}"', (root / 'boot/grub/loopback.cfg').read_text())

    def test_missing_live_entries_stop_the_build(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'No Arch live boot entries'):
                boot.configure(directory, 'old', 'new')
