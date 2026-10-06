{ lib, stdenvNoCC, python3, makeWrapper }:
stdenvNoCC.mkDerivation {
  pname = "controlstack-system-agent";
  version = "0.1.0";
  src = lib.fileset.toSource {
    root = ../..;
    fileset = lib.fileset.unions [ ../../system_agent ../../runtimes ../../identity ../../LICENSE ];
  };
  nativeBuildInputs = [ makeWrapper ];
  installPhase = ''
    mkdir -p $out/lib/system-agent $out/bin
    cp -r system_agent runtimes identity $out/lib/system-agent/
    mkdir -p $out/share/licenses/controlstack-system-agent
    cp LICENSE $out/share/licenses/controlstack-system-agent/
    makeWrapper ${python3}/bin/python3 $out/bin/system-agent \
      --add-flags "-m system_agent" --set PYTHONPATH $out/lib/system-agent
    makeWrapper ${python3}/bin/python3 $out/bin/system-agent-admin \
      --add-flags "-m system_agent.admin" --set PYTHONPATH $out/lib/system-agent
  '';
  meta = { license = lib.licenses.mit; mainProgram = "system-agent"; platforms = lib.platforms.linux; };
}
