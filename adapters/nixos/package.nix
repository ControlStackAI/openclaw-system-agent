{ lib, stdenvNoCC, python3, makeWrapper, installer-source ? null }:
stdenvNoCC.mkDerivation {
  pname = "controlstack-system-agent";
  version = "0.1.0";
  src = lib.fileset.toSource {
    root = ../..;
    fileset = lib.fileset.unions [ ../../system_agent ../../runtimes ../../identity ../../adapters ../../LICENSE ];
  };
  nativeBuildInputs = [ makeWrapper ];
  installPhase = ''
    mkdir -p $out/lib/system-agent $out/bin
    cp -r system_agent runtimes identity adapters $out/lib/system-agent/
    ${lib.optionalString (installer-source != null) "cp -r ${installer-source}/core $out/lib/system-agent/core; cp -r ${installer-source}/profiles $out/lib/system-agent/profiles"}
    mkdir -p $out/share/licenses/controlstack-system-agent
    cp LICENSE $out/share/licenses/controlstack-system-agent/
    makeWrapper ${python3}/bin/python3 $out/bin/system-agent \
      --add-flags "-P -s -m system_agent" --set PYTHONPATH $out/lib/system-agent
    makeWrapper ${python3}/bin/python3 $out/bin/system-agent-setup \
      --add-flags "-P -s -m system_agent.setup" --set PYTHONPATH $out/lib/system-agent
    makeWrapper ${python3}/bin/python3 $out/bin/system-agent-codex-login \
      --add-flags "-P -s -m system_agent.coding_login" --set PYTHONPATH $out/lib/system-agent
    makeWrapper ${python3}/bin/python3 $out/bin/system-agent-admin \
      --add-flags "-P -s -m system_agent.admin" --set PYTHONPATH $out/lib/system-agent
  '';
  meta = { license = lib.licenses.mit; mainProgram = "system-agent"; platforms = lib.platforms.linux; };
}
