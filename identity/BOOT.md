# Startup checklist
The service refreshes facts through ExecStartPre independently of this file.
Read fresh lifecycle/facts.json. Check installed-boot evidence and gateway health
separately. Do not announce success or trigger outbound messages automatically.
This file is guidance; the upstream boot-md hook is not enabled by this project.
