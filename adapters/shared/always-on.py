"""Apply supported performance controls without disabling thermal protection."""
from pathlib import Path

CONTROLS = {
    '/sys/devices/system/cpu/cpufreq/policy*/scaling_governor': 'performance',
    '/sys/devices/system/cpu/cpufreq/policy*/energy_performance_preference': 'performance',
    '/sys/devices/system/cpu/cpu*/power/energy_perf_bias': '0',
    '/sys/class/scsi_host/host*/link_power_management_policy': 'max_performance',
    '/sys/bus/usb/devices/*/power/control': 'on',
    '/sys/bus/pci/devices/*/power/control': 'on',
    '/sys/firmware/acpi/platform_profile': 'performance',
}
for pattern, value in CONTROLS.items():
    for path in Path('/').glob(pattern.lstrip('/')):
        try:
            path.write_text(value + '\n')
        except OSError:
            # Unsupported governors/profiles are hardware dependent.
            pass
