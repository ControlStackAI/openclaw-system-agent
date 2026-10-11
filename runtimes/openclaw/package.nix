# The official Nix recipe currently trails the stable npm release. Reuse its
# runtime staging and wrapper with a separately locked complete
# npm dependency tree, including the matching ACPX runtime plugin.
{ upstream, lib, fetchNpmDeps }:
upstream.overrideAttrs (old: {
  version = "2026.10.1";
  src = ./npm;
  npmDeps = fetchNpmDeps { src = ./npm; hash = "sha256-NQUn/hm89atobrHBAhmLr8Q/D7cArmEKw9uUiY9wbMI="; };
  env = old.env // {
    OPENCLAW_NPM_WRAPPER_DIR = "npm";
    OPENCLAW_PATCH_NPM_DIST_SCRIPT = "${./check-package.mjs}";
  };
  installPhase = ''
    export OPENCLAW_BUNDLED_ACPX="$out/lib/node_modules/@openclaw/acpx"
    ${old.installPhase}
  '';
})
