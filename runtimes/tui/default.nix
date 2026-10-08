{ rustPlatform }:
rustPlatform.buildRustPackage {
  pname = "controlstack-tui";
  version = "0.2.0";
  src = ./.;
  cargoLock.lockFile = ./Cargo.lock;
  meta.mainProgram = "controlstack-tui";
}
