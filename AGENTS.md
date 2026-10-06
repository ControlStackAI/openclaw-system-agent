# Contributor instructions
Keep portable lifecycle code in system_agent/, OpenClaw integration in runtimes/,
and distribution packaging in adapters/. Do not modify the installer repository.
Do not use host credentials, private state, operator home mounts, host block
 devices, Docker sockets, or production services in builds or tests.
Run python3 -m unittest discover -s tests -v and the relevant VM checks.
Keep input pins and kernel/ZFS guards. Do not equate fixtures with model access,
or a gateway health check with an installed boot or recovery qualification.
Only reviewed generic source belongs in public history. The experimental NixOS disk executor must be tested only on disposable VM disks.
Development authorization never authorizes erasing host disks.
