{ lib, python3Packages, fetchFromGitHub, makeWrapper, hyprland, grim, wtype, systemd, imagemagick, wl-clipboard, libnotify }:
python3Packages.buildPythonApplication {
  pname = "hypruse";
  version = "0.11.0";
  pyproject = true;
  src = fetchFromGitHub {
    owner = "IlyasKhallouki";
    repo = "hypruse";
    rev = "253f6892bf0ba738b60046e64d0442fa48c454fc";
    hash = "sha256-aTP+RHFnslS54s8uozH+U0WJ6RhvK8GLpGWptIdSv/w=";
  };
  build-system = [ python3Packages.hatchling ];
  dependencies = [ python3Packages.mcp ];
  nativeBuildInputs = [ makeWrapper ];
  nativeCheckInputs = [ python3Packages.pytestCheckHook ];
  # Upstream marks real-compositor tests e2e; the project desktop VM covers those.
  # These two assert a checkout-relative skill path; Nix tests the installed wheel.
  disabledTests = [ "test_the_checkout_carries_the_skill_and_it_is_well_formed" "test_main_path_prints_the_packaged_directory" ];
  postCheck = ''
    test -s $out/${python3Packages.python.sitePackages}/hypruse/skill/SKILL.md
  '';
  pythonImportsCheck = [ "hypruse" ];
  postFixup = ''
    wrapProgram $out/bin/hypruse --prefix PATH : ${lib.makeBinPath [ hyprland grim wtype systemd imagemagick wl-clipboard libnotify ]}
  '';
  meta = { description = "Native Hyprland desktop control over MCP"; license = lib.licenses.mit; platforms = lib.platforms.linux; };
}
