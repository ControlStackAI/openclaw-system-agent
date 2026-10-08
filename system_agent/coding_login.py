"""Owner-side Codex sign-in. Never reads tokens or runs as the resident account."""
import os
import pwd
import subprocess
from .setup import choose


def login_command(method):
    if method == 'browser':
        return ['codex', 'login']
    if method == 'device':
        return ['codex', 'login', '--device-auth']
    raise ValueError('Choose browser or device sign-in.')


def main():
    if os.geteuid() == 0 or pwd.getpwuid(os.geteuid()).pw_name == 'controlstack-agent':
        print('Open Coding Assistant Sign-in from your own desktop account.')
        return 1
    print('Codex sign-in belongs to your account. It is separate from the resident OpenClaw assistant.\n'
          'If your sign-in provider offers your registered security key or passkey, select it in the browser.\n'
          'You may need to touch the key or enter its PIN. Plugging in a key alone does not sign you in.')
    status = subprocess.run(['codex', 'login', 'status'], capture_output=True, text=True)
    if status.returncode == 0:
        print('Codex already has a saved sign-in. It normally reuses and refreshes that session.')
        if choose('What would you like to do?', ['Keep this sign-in', 'Open sign-in options']) == 1:
            return 0
    graphical = bool(os.environ.get('WAYLAND_DISPLAY') or os.environ.get('DISPLAY'))
    options = (['Sign in in this computer’s browser', 'Use another device', 'Back'] if graphical else
               ['Use another device', 'Back'])
    answer = choose('How would you like to sign in to Codex?', options)
    if answer == len(options):
        return 0
    method = 'browser' if graphical and answer == 1 else 'device'
    if method == 'device':
        print('Open the official link and enter the code on your other device.\n'
              'A security key must be usable by that device’s browser; a key on this console is not forwarded.\n'
              'Device-code login must be enabled in your ChatGPT account or workspace.')
    # Let the vendor own the entire OAuth flow, input handling and credential storage.
    # Do not capture the login output, parse browser URLs, or import another account's cache.
    return subprocess.run(login_command(method)).returncode


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (EOFError, KeyboardInterrupt):
        print('\nSign-in cancelled.')
        raise SystemExit(1)
