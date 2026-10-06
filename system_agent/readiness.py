"""Non-mutating readiness gates. Connectivity comes before clock readiness."""
import subprocess


def readiness(run=subprocess.run):
    for url in ('https://docs.openclaw.ai/', 'https://registry.npmjs.org/openclaw'):
        result = run(['curl', '--silent', '--output', '/dev/null', '--write-out', '%{http_code}',
                      '--connect-timeout', '5', '--max-time', '12', url], capture_output=True, text=True)
        if result.returncode == 60:
            return False, 'A secure connection failed. The clock or this network’s sign-in page may need attention.'
        if result.returncode or not result.stdout.isdigit() or not 200 <= int(result.stdout) < 400:
            return False, 'I could not reach the internet. Connect an Ethernet cable or open Wi-Fi setup, then retry.'
    result = run(['timedatectl', 'show', '-p', 'NTPSynchronized', '--value'], capture_output=True, text=True)
    if result.returncode or result.stdout.strip() != 'yes':
        return False, 'Internet works, but the clock is not synchronized yet. Wait a moment, then retry.'
    return True, 'Internet and clock checks passed. You can sign in now.'
