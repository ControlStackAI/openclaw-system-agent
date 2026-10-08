# Contributor instructions

Read README.md for the user journey and docs/agent-guide.md for the build,
qualification and handoff workflow. The instructions in identity/ are for the
shipped live/resident agent, not authority to administer this development host.

Keep portable lifecycle code in system_agent/, OpenClaw integration in runtimes/,
and distribution packaging in adapters/. Do not modify the installer repository.
Do not use host credentials, private state, operator home mounts, host block
devices or production services in builds or tests. Never mount Docker sockets
inside build/test containers; the Arch builder may use the host Docker daemon
to launch its isolated build container.
Run python3 -m unittest discover -s tests -v and the relevant VM checks.
Keep input pins and kernel/ZFS guards. Do not equate fixtures with model access,
or a gateway health check with an installed boot or recovery qualification.
Only reviewed generic source belongs in public history. Both distribution disk
executors must be tested only on disposable VM disks.
Development authorization never authorizes erasing host disks.
