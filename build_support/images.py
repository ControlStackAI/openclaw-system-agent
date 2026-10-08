"""Explicit source selection, immutable build locks, and artifact receipts.

Resolution may use moving upstream names. Building never resolves them again.
A lock proves input selection, not that two output ISOs are byte-identical.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRS = ("adapters", "system_agent", "runtimes", "identity", "contracts", "build_support")
SOURCE_FILES = ("flake.nix", "flake.lock", "LICENSE", "scripts/image.py")
HEX = r"[0-9a-f]{64}"


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def source_manifest(root=ROOT):
    # Only reviewed Git-tracked public sources enter staging. An operator's
    # untracked .env, caches or credentials beside the checkout are excluded.
    names = subprocess.check_output(["git", "ls-files", "-z", "--", *SOURCE_FILES, *SOURCE_DIRS],
                                    cwd=root).decode().split("\0")
    paths = [root / name for name in names if name]
    if not all((root / name) in paths for name in SOURCE_FILES):
        raise ValueError("Required build sources must be tracked in Git before resolving.")
    result = {}
    for path in sorted(paths):
        if path.is_symlink():
            raise ValueError("Build source must not contain symlinks: " + str(path))
        result[str(path.relative_to(root))] = digest(path)
    return result


def stage_source(destination, manifest, root=ROOT):
    if source_manifest(root) != manifest:
        raise ValueError("Build source changed since resolution. Resolve a new lock explicitly.")
    for name, expected in manifest.items():
        source, target = root / name, destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        if digest(target) != expected:
            raise ValueError("Source changed while staging: " + name)
        target.chmod(0o644)


def fetch_json(url):
    return json.loads(fetch(url))


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "ControlStackAI-system-agent-build"})
    with urllib.request.urlopen(request, timeout=120) as stream:
        return stream.read()


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def root_nixpkgs(flake_lock):
    nodes = flake_lock["nodes"]
    name = nodes[flake_lock.get("root", "root")]["inputs"]["nixpkgs"]
    if not isinstance(name, str):
        raise ValueError("Root nixpkgs must refer to one locked node.")
    return nodes[name]


def validate(lock):
    if type(lock.get("schema")) is not int or lock.get("schema") != 1 or lock.get("distro") not in ("arch", "nixos"):
        raise ValueError("Only schema 1 Arch/NixOS image locks are supported.")
    if lock.get("architecture") != "x86_64-linux":
        raise ValueError("Only x86_64 Linux is supported.")
    epoch = lock.get("source_date_epoch")
    if type(epoch) is not int or not 315532800 <= epoch <= 4354819199:
        raise ValueError("A fixed SOURCE_DATE_EPOCH between 1980 and 2107 is required.")
    manifest = lock.get("source", {})
    if not manifest or not all(isinstance(k, str) and not k.startswith("/") and
                              ".." not in Path(k).parts and isinstance(v, str) and re.fullmatch(HEX, v)
                              for k, v in manifest.items()):
        raise ValueError("Invalid build source manifest.")
    if lock.get("source_sha256") != hashlib.sha256(canonical(manifest)).hexdigest():
        raise ValueError("Build source manifest digest mismatch.")
    nodes = lock["flake_lock"]["nodes"]
    for name, node in nodes.items():
        if name == lock["flake_lock"].get("root", "root"):
            continue
        pinned = node.get("locked", {})
        if not pinned.get("narHash") or (pinned.get("type") == "github" and
                                          not re.fullmatch(r"[0-9a-f]{40}", pinned.get("rev", ""))):
            raise ValueError("Unpinned flake dependency: " + name)
    if lock["distro"] == "arch":
        from .arch import validate_inputs
        validate_inputs(lock["arch"])
    return lock


def resolve(distro, *, nixpkgs=None, arch_version=None, snapshot=None, epoch=None):
    if distro == "nixos" and (arch_version or snapshot):
        raise ValueError("NixOS uses a nixpkgs revision, not an Arch ISO or package snapshot.")
    if distro == "arch" and nixpkgs:
        raise ValueError("Arch uses its ISO/package snapshot; the runtime flake pins remain unchanged.")
    manifest = source_manifest()
    flake_lock = json.loads((ROOT / "flake.lock").read_text())
    if nixpkgs:
        if not re.fullmatch(r"[A-Za-z0-9._-]+", nixpkgs):
            raise ValueError("Use a nixpkgs release, branch or commit, not an arbitrary URL.")
        # 'latest' has a documented meaning; it is never passed into build.
        ref = "nixos-unstable" if nixpkgs == "latest" else nixpkgs
        with tempfile.TemporaryDirectory(prefix="controlstack-resolve-") as temp:
            stage = Path(temp)
            stage_source(stage, manifest)
            subprocess.run(["nix", "flake", "lock", str(stage), "--override-input", "nixpkgs",
                            "github:NixOS/nixpkgs/" + ref], check=True)
            flake_lock = json.loads((stage / "flake.lock").read_text())
    if epoch is None:
        epoch = int(subprocess.check_output(["git", "show", "-s", "--format=%ct", "HEAD"], cwd=ROOT, text=True))
    lock = {"schema": 1, "distro": distro, "architecture": "x86_64-linux",
            "source_date_epoch": epoch, "source": manifest,
            "source_sha256": hashlib.sha256(canonical(manifest)).hexdigest(),
            "flake_lock": flake_lock, "selection": {"nixpkgs": nixpkgs or "repository-pin"},
            "reproducibility": "locked-inputs; independent-output-comparison-required"}
    if distro == "arch":
        from .arch import resolve_inputs
        lock["arch"] = resolve_inputs(arch_version, snapshot)
        lock["selection"] = {"arch_iso": arch_version or "repository-pin", "snapshot": snapshot or "repository-pin"}
    return validate(lock)


def prepare_flake(stage, lock):
    (stage / "flake.lock").write_text(json.dumps(lock["flake_lock"], indent=2) + "\n")
    # The input declaration must agree with the chosen pin; otherwise Nix may
    # try to resolve the old declaration. All transitive locks stay recorded.
    pinned = root_nixpkgs(lock["flake_lock"])["locked"]["rev"]
    path = stage / "flake.nix"
    text = path.read_text()
    text, count = re.subn(r'nixpkgs.url = "github:NixOS/nixpkgs/[^"]+";',
                         'nixpkgs.url = "github:NixOS/nixpkgs/' + pinned + '";', text)
    if count != 1:
        raise ValueError("Cannot identify the root nixpkgs input declaration.")
    path.write_text(text)
    lock_data = json.loads((stage / "flake.lock").read_text())
    root_nixpkgs(lock_data)["original"] = {
        "owner": "NixOS", "repo": "nixpkgs", "rev": pinned, "type": "github"}
    (stage / "flake.lock").write_text(json.dumps(lock_data, indent=2) + "\n")


def plan(lock):
    validate(lock)
    return {"distro": lock["distro"], "source_sha256": lock["source_sha256"],
            "nixpkgs": root_nixpkgs(lock["flake_lock"])["locked"]["rev"],
            "base": lock.get("arch", {}).get("arch", {}).get("iso"),
            "desktop_selection": "after USB boot",
            "qualified": False, "note": "A new lock requires fresh VM qualification; a build alone is not qualification."}


def build(lock, destination, jobs, iso=None):
    validate(lock)
    if jobs < 1:
        raise ValueError("Jobs must be positive.")
    if iso and lock["distro"] != "arch":
        raise ValueError("--iso supplies cached Arch input bytes. NixOS is built from nixpkgs source.")
    destination = Path(destination).absolute()
    if destination.exists():
        raise ValueError("Output directory exists; choose a fresh path to preserve previous evidence.")
    # Build failure never leaves a release-looking output directory.
    area = ROOT / ".build/images"
    area.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=lock["distro"] + "-", dir=area) as temp:
        work = Path(temp)
        source = work / "source"
        stage_source(source, lock["source"])
        prepare_flake(source, lock)
        environment = dict(os.environ, SOURCE_DATE_EPOCH=str(lock["source_date_epoch"]), TZ="UTC")
        if lock["distro"] == "nixos":
            link = work / "result"
            subprocess.run(["nix", "build", "path:" + str(source) + "#live-iso",
                            "--no-update-lock-file", "--no-write-lock-file", "--max-jobs", str(jobs),
                            "--cores", str(jobs), "--out-link", str(link), "-L"], check=True, env=environment)
            images = list((link / "iso").glob("*.iso"))
        else:
            from .arch import build_image
            images = [build_image(source, work, lock, jobs, iso)]
        if len(images) != 1:
            raise ValueError("Expected exactly one completed ISO.")
        staged = work / "release"
        staged.mkdir()
        artifact = staged / images[0].name
        shutil.copyfile(images[0], artifact)
        receipt = {"schema": 1, "distro": lock["distro"], "image": artifact.name,
                   "sha256": digest(artifact), "bytes": artifact.stat().st_size,
                   "lock_sha256": hashlib.sha256(canonical(lock)).hexdigest(),
                   "source_sha256": lock["source_sha256"], "source_date_epoch": lock["source_date_epoch"],
                   "qualification": {"vm_boot": False, "disk_install": False, "physical_hardware": False},
                   "byte_identical_rebuild_verified": False}
        write_new(staged / "build-receipt.json", receipt)
        write_new(staged / "image.lock.json", lock)
        (staged / "SHA256SUMS").write_text(receipt["sha256"] + "  " + artifact.name + "\n")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise ValueError("Output appeared during the build; preserving it without replacement.")
        shutil.move(str(staged), destination)
    return receipt


def compare(left, right):
    receipts = []
    for directory in (Path(left), Path(right)):
        receipt = json.loads((directory / "build-receipt.json").read_text())
        name = receipt["image"]
        if Path(name).name != name:
            raise ValueError("Unsafe receipt image name.")
        if digest(directory / name) != receipt["sha256"]:
            raise ValueError("Artifact no longer matches its receipt.")
        lock = validate(json.loads((directory / "image.lock.json").read_text()))
        if hashlib.sha256(canonical(lock)).hexdigest() != receipt["lock_sha256"]:
            raise ValueError("Lock no longer matches its receipt.")
        receipts.append(receipt)
    if receipts[0]["lock_sha256"] != receipts[1]["lock_sha256"]:
        raise ValueError("Different locks: this is not a reproducibility comparison.")
    same = receipts[0]["sha256"] == receipts[1]["sha256"]
    return {"same_locked_inputs": True, "byte_identical": same,
            "independent_builds_proven": False,
            "note": "Run on separate clean builders; comparing two copies or cache hits is not independent-build evidence."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    resolver = subs.add_parser("resolve", help="Explicitly select and freeze sources; never overwrites a lock")
    resolver.add_argument("--distro", choices=("arch", "nixos"), required=True)
    resolver.add_argument("--nixpkgs", help="Commit, release branch, or latest (= nixos-unstable)")
    resolver.add_argument("--arch-iso-version", dest="arch_version", help="YYYY.MM.DD or latest")
    resolver.add_argument("--snapshot", help="Arch package archive YYYY/MM/DD; explicit for a changed ISO")
    resolver.add_argument("--epoch", type=int)
    resolver.add_argument("--output", required=True)
    for command in ("plan", "build"):
        sub = subs.add_parser(command)
        sub.add_argument("--lock", required=True)
        if command == "build":
            sub.add_argument("--output", required=True)
            sub.add_argument("--jobs", type=int, default=2)
            sub.add_argument("--iso", type=Path, help="Local Arch ISO with the exact locked checksum")
    comparison = subs.add_parser("compare")
    comparison.add_argument("left")
    comparison.add_argument("right")
    args = vars(parser.parse_args())
    command = args.pop("command")
    try:
        if command == "resolve":
            target = args.pop("output")
            if Path(target).exists():
                raise ValueError("Lock already exists; choose a new path.")
            lock = resolve(**args)
            write_new(target, lock)
            result = plan(lock)
        elif command == "compare":
            result = compare(**args)
        else:
            lock = validate(json.loads(Path(args.pop("lock")).read_text()))
            result = plan(lock) if command == "plan" else build(lock, args.pop("output"), **args)
        print(json.dumps(result, indent=2))
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        parser.exit(1, str(error) + "\n")
