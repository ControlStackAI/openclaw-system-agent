"""Live Linux virtual-console fonts, with an independent rollback watchdog."""
import fcntl
import json
import os
from pathlib import Path
import re
import select
import shutil
import subprocess
import sys
import tempfile

SIZES = [('Small', 14), ('Standard', 16), ('Large', 20), ('Extra large', 24)]
FONT_DIR = Path(__file__).resolve().parent.parent / 'consolefonts'
STATE_DIR = Path('/run/controlstack-console')
PREVIEW_SECONDS = 15


def console_device():
    try:
        name = os.ttyname(0)
        if not re.fullmatch(r'/dev/tty[1-9][0-9]*', name):
            return None
        fcntl.ioctl(0, 0x4B33, bytearray(1))  # KDGKBTYPE: reject PTYs/serial consoles.
        return name
    except OSError:
        return None


def setfont(device, *args):
    binary = os.environ.get('CONTROLSTACK_SETFONT') or shutil.which('setfont')
    if not binary:
        raise FileNotFoundError('Console font support is missing from this image')
    subprocess.run([binary, '-C', device, *map(str, args)], check=True,
                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def state_file(device):
    return STATE_DIR / (Path(device).name + '.json')


def saved_size(device):
    try:
        size = json.loads(state_file(device).read_text())['size']
        return size if size in [s for _, s in SIZES] else 16
    except (OSError, ValueError, KeyError):
        return 16


def initialize():
    device = console_device()
    if device:
        setfont(device, FONT_DIR / f'ter-u{saved_size(device)}n.psf.gz')


def watchdog(device, size):
    """Own apply/restore so EOF, UI failure, or parent death cannot keep a preview."""
    if not re.fullmatch(r'/dev/tty[1-9][0-9]*', device) or size not in [s for _, s in SIZES]:
        raise ValueError('Unsupported console or text size')
    STATE_DIR.mkdir(mode=0o700, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='preview-', dir=STATE_DIR) as tmp:
        backup = Path(tmp) / 'previous.psf'
        setfont(device, '-O', backup)
        keep = False
        try:
            setfont(device, FONT_DIR / f'ter-u{size}n.psf.gz')
            print('ready', flush=True)
            readable, _, _ = select.select([sys.stdin], [], [], PREVIEW_SECONDS)
            if readable and sys.stdin.readline().strip() == 'keep':
                # Persist only confirmed choices, in RAM and per virtual console.
                state_file(device).write_text(json.dumps({'size': size}) + '\n')
                keep = True
        finally:
            if not keep:
                setfont(device, backup)
        print("kept" if keep else "restored", flush=True)


def choose_size(ui):
    device = console_device()
    if not device:
        ui.info('Text size', 'Text size is available on the USB computer’s local text console.')
        return
    current = saved_size(device)
    answer = ui.choose('Text size for this USB session', [
        f'{name} — {size} pixels' + (' · current' if size == current else '')
        for name, size in SIZES] + ['Back'])
    if answer == 5:
        return
    size = SIZES[answer - 1][1]
    child = subprocess.Popen([sys.executable, '-m', 'system_agent.console_font', device, str(size)],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, text=True, start_new_session=True)
    keep = False
    try:
        if not select.select([child.stdout], [], [], 5)[0] or child.stdout.readline().strip() != 'ready':
            raise OSError('The console could not preview this size')
        columns, rows = os.get_terminal_size(0)
        if columns < 60 or rows < 18:
            message = 'That size leaves too little room for setup on this display. The previous size was restored.'
        else:
            from .tui import Cancelled
            try:
                keep = ui.request({'kind': 'choose', 'title': 'Keep this text size?',
                    'text': f'{SIZES[answer - 1][0]} text · {columns} columns × {rows} rows\n'
                            'The quick brown fox jumps over the lazy dog.\n'
                            'OpenClaw • Wi-Fi • 0123456789\n'
                            'Automatically restores the previous size after 15 seconds.',
                    'options': ['Keep this size', 'Restore previous size'],
                    'timeout_seconds': PREVIEW_SECONDS}) == 1
            except Cancelled:
                pass
            message = 'Text size saved for this USB session.' if keep else 'Previous text size restored.'
        if child.poll() is None:
            try:
                child.stdin.write('keep\n' if keep else 'restore\n')
                child.stdin.flush()
            except BrokenPipeError:
                keep = False
                message = 'Preview expired. Previous text size restored.'
    finally:
        child.stdin.close()
        child.wait(timeout=20)
        outcome = child.stdout.read().strip()
        child.stdout.close()
    if keep and outcome != 'kept':
        message = 'Preview expired. Previous text size restored.'
    if child.returncode:
        raise OSError('The console font change did not finish successfully')
    ui.info('Text size', message)


if __name__ == '__main__':
    watchdog(sys.argv[1], int(sys.argv[2]))
