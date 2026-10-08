# The official Nix recipe currently trails the stable npm release. Reuse its
# runtime staging and wrapper with a separately locked complete
# npm dependency tree, including the matching ACPX runtime plugin.
{ upstream, lib, fetchNpmDeps }:
upstream.overrideAttrs (old: {
  version = "2026.9.9";
  src = ./npm;
  npmDeps = fetchNpmDeps { src = ./npm; hash = "sha256-7iMNpLb+pCScn1OI+Ex0OhKhoySdtD3MyOd6Gu+zld4="; };
  env = old.env // {
    OPENCLAW_NPM_WRAPPER_DIR = "npm";
    OPENCLAW_PATCH_NPM_DIST_SCRIPT = "${./check-package.mjs}";
  };
  installPhase = ''
    export OPENCLAW_BUNDLED_ACPX="$out/lib/node_modules/@openclaw/acpx"
    ${old.installPhase}
  '';
})
