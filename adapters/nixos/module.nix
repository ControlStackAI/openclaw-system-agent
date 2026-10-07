{ config, lib, pkgs, ... }:
let
  cfg = config.services.controlstackAgent;
  state = if cfg.ephemeral then "/run/controlstack-agent" else "/var/lib/controlstack-agent";
  configPath = if cfg.mutableProviderSetup then "${state}/openclaw.json" else "/etc/controlstack-agent/openclaw.json";
  defaults = {
    gateway = {
      mode = "local";
      bind = "loopback";
      port = cfg.port;
      auth = { mode = "token"; token = { source = "file"; provider = "gateway"; id = "value"; }; };
    };
    secrets.providers.gateway = { source = "file"; path = "${state}/gateway-token"; mode = "singleValue"; };
    agents.defaults = { workspace = "${state}/workspace"; skipBootstrap = true; };
    tools = {
      profile = "full";
      allow = [ "read" "session_status" ] ++ lib.optionals cfg.workspaceExecution [ "exec" "process" "write" "edit" ];
      elevated.enabled = false;
    };
    discovery.mdns.mode = "off";
  };
  settings = lib.recursiveUpdate defaults cfg.settings;
  configFile = pkgs.writeText "controlstack-openclaw.json" (builtins.toJSON settings);
in {
  options.services.controlstackAgent = {
    enable = lib.mkEnableOption "the resident ControlStackAI OpenClaw agent";
    package = lib.mkOption { type = lib.types.package; description = "Pinned complete OpenClaw runtime package."; };
    corePackage = lib.mkOption { type = lib.types.package; default = pkgs.callPackage ./package.nix {}; };
    port = lib.mkOption { type = lib.types.port; default = 18789; };
    workspaceExecution = lib.mkOption {
      type = lib.types.bool; default = false;
      description = "Permit shell and edits as the service user inside systemd restrictions. This can modify agent state.";
    };
    settings = lib.mkOption {
      type = lib.types.attrs; default = {};
      description = "Declarative OpenClaw settings; use runtime SecretRefs, never literal secrets in the Nix store.";
    };
    capabilities = lib.mkOption {
      type = lib.types.attrsOf (lib.types.listOf lib.types.str);
      default = { datasets = []; pools = []; services = []; };
      description = "Exact targets for the owner-run maintenance broker. No resident sudo grant is created.";
    };
    zfs.enable = lib.mkEnableOption "released ZFS and the newest supported kernel available in the pinned package set";
    ephemeral = lib.mkEnableOption "private RAM state on the live image";
    mutableProviderSetup = lib.mkEnableOption "official interactive onboarding into private mutable runtime config";
    installInputs = lib.mkOption { type = lib.types.attrsOf lib.types.str; default = {}; internal = true; };
  };
  config = lib.mkIf cfg.enable {
    users.groups.controlstack-agent = {};
    users.users.controlstack-agent = {
      isSystemUser = true; group = "controlstack-agent";
      home = state; createHome = false;
    };
    environment.systemPackages = [ cfg.corePackage cfg.package ];
    environment.etc."controlstack-agent/openclaw.json".source = configFile;
    environment.etc."controlstack-agent/capabilities.json".text = builtins.toJSON cfg.capabilities;
    environment.etc."controlstack-agent/install-inputs.json" = lib.mkIf (cfg.installInputs != {}) {
      text = builtins.toJSON cfg.installInputs;
    };
    systemd.services.controlstack-agent = {
      description = "ControlStackAI resident system agent";
      wantedBy = [ "multi-user.target" ];
      after = [ "network.target" ];
      path = [ cfg.package cfg.corePackage pkgs.util-linux pkgs.systemd pkgs.coreutils ];
      environment = {
        HOME = state;
        OPENCLAW_HOME = state;
        OPENCLAW_STATE_DIR = state;
        OPENCLAW_CONFIG_PATH = configPath;
        OPENCLAW_NIX_MODE = if cfg.mutableProviderSetup then "0" else "1";
        OPENCLAW_DISABLE_BONJOUR = "1";
        XDG_CACHE_HOME = "${state}/cache";
        XDG_CONFIG_HOME = "${state}/config";
        XDG_DATA_HOME = "${state}/data";
      };
      serviceConfig = {
        User = "controlstack-agent";
        Group = "controlstack-agent";
        StateDirectory = lib.mkIf (!cfg.ephemeral) "controlstack-agent";
        StateDirectoryMode = "0700";
        RuntimeDirectory = lib.mkIf cfg.ephemeral "controlstack-agent";
        RuntimeDirectoryMode = "0700";
        RuntimeDirectoryPreserve = lib.mkIf cfg.ephemeral "yes";
        UMask = "0077";
        ExecStartPre = [ "${cfg.corePackage}/bin/system-agent initialize --seed-config ${configFile}" "${cfg.corePackage}/bin/system-agent refresh" ];
        ExecStart = "${cfg.package}/bin/openclaw gateway run";
        CPUAccounting = true;
        MemoryAccounting = true;
        Restart = "on-failure";
        RestartSec = 5;
        TimeoutStopSec = 120;
        NoNewPrivileges = true;
        CapabilityBoundingSet = "";
        ProtectSystem = "strict";
        ProtectHome = true;
        PrivateTmp = true;
        PrivateDevices = true;
        ProtectKernelTunables = true;
        ProtectKernelModules = true;
        ProtectControlGroups = true;
        # This filter returns ENOSYS for openat2, required by OpenClaw's secure lock.
        # NoNewPrivileges and the empty capability set still prevent privilege gains.
        RestrictSUIDSGID = false;
        RestrictAddressFamilies = [ "AF_UNIX" "AF_INET" "AF_INET6" ];
        LockPersonality = true;
        ReadWritePaths = [ state ];
      };
    };
    systemd.services.controlstack-agent-boot-check = lib.mkIf (!cfg.ephemeral) {
      description = "Verify the installed root independently of model access";
      wantedBy = [ "multi-user.target" ];
      after = [ "controlstack-agent.service" ];
      unitConfig.ConditionPathExists = "${state}/lifecycle/installation.json";
      path = [ pkgs.util-linux pkgs.systemd ];
      serviceConfig = {
        Type = "oneshot";
        User = "controlstack-agent";
        ExecStart = "${cfg.corePackage}/bin/system-agent verify-boot";
        RemainAfterExit = true;
      };
    };
    # A build-time module alone cannot prove installed-root bootability.
    boot.supportedFilesystems = lib.mkIf cfg.zfs.enable [ "zfs" ];
    boot.zfs.package = lib.mkIf cfg.zfs.enable pkgs.zfs_2_4;
    boot.kernelPackages = lib.mkIf cfg.zfs.enable pkgs.linuxPackages_latest;
    boot.zfs.forceImportRoot = lib.mkIf cfg.zfs.enable false;
    assertions = lib.optionals cfg.zfs.enable [{
      assertion = !config.boot.zfs.modulePackage.meta.broken;
      message = "The pinned latest kernel is unsupported by released OpenZFS. Review the pins; do not disable this guard.";
    }];
  };
}
