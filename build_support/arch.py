"""Arch live image adapter: reviewed ISO + frozen repositories + Nix runtime closure."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import urllib.request
from .images import ROOT, canonical, digest, fetch

IMAGE = ROOT / "adapters/arch/image"


def inputs_module():
    spec = importlib.util.spec_from_file_location("controlstack_arch_inputs", IMAGE / "scripts/inputs.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_inputs(lock):
    inputs_module().validate(lock)
    for repo in ("core", "extra"):
        item = lock.get("databases", {}).get(repo, {})
        if not re.fullmatch(r"[0-9a-f]{64}", item.get("sha256", "")):
            raise ValueError("Arch repository database hashes must be frozen at resolution.")
        expected = f'https://archive.archlinux.org/repos/{lock["arch"]["snapshot"]}/{repo}/os/x86_64/{repo}.db'
        if item.get("url") != expected:
            raise ValueError("Repository database does not match the selected snapshot.")


def resolve_inputs(version, snapshot):
    original = json.loads((IMAGE / "inputs.lock.json").read_text())
    if version or snapshot:
        if not version or not snapshot:
            raise ValueError("Changing Arch sources requires both --arch-iso-version and --snapshot.")
        if version != "latest" and not re.fullmatch(r"\d{4}\.\d{2}\.\d{2}", version):
            raise ValueError("Use an ISO release YYYY.MM.DD or latest.")
        # Reviewed upstream resolver retains signer and kernel/ZFS guards.
        lock = inputs_module().resolve(version, original["codex"]["version"], snapshot)
    else:
        lock = original
    lock["databases"] = {}
    for repo in ("core", "extra"):
        url = f'https://archive.archlinux.org/repos/{lock["arch"]["snapshot"]}/{repo}/os/x86_64/{repo}.db'
        lock["databases"][repo] = {"url": url, "sha256": hashlib.sha256(fetch(url)).hexdigest(), "name": repo + ".db"}
    validate_inputs(lock)
    return lock


def download(item, cache):
    directory = cache / item["sha256"]
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / item["name"]
    if not path.exists():
        temporary = directory / (item["name"] + ".part")
        request = urllib.request.Request(item["url"], headers={"User-Agent": "ControlStackAI-system-agent-build"})
        with urllib.request.urlopen(request, timeout=180) as stream, temporary.open("wb") as output:
            shutil.copyfileobj(stream, output)
        if digest(temporary) != item["sha256"]:
            temporary.unlink()
            raise ValueError("Downloaded input hash mismatch: " + item["name"])
        temporary.replace(path)
    if digest(path) != item["sha256"]:
        raise ValueError("Cached input hash mismatch: " + item["name"])
    return path


def build_image(source, work, lock, jobs, iso):
    inputs = lock["arch"]
    cache = ROOT / ".build/image-downloads"
    downloaded = work / "downloads"
    downloaded.mkdir()
    items = [inputs["arch"]["iso"], inputs["arch"]["iso"]["signature"], inputs["arch"]["linux"], inputs["codex"]["package"]]
    for package in inputs["zfs"]["packages"]:
        items.extend([package, package["signature"]])
    items += list(inputs["databases"].values())
    for item in items:
        if iso and item == inputs["arch"]["iso"]:
            if not iso.is_file() or digest(iso) != item["sha256"]:
                raise ValueError("Supplied Arch ISO differs from the resolved lock.")
            original = iso
        else:
            original = download(item, cache)
        shutil.copyfile(original, downloaded / item["name"])
    runtime = work / "runtime"
    subprocess.run(["nix", "build", "path:" + str(source) + "#arch-runtime", "--no-update-lock-file",
                    "--no-write-lock-file", "--max-jobs", str(jobs), "--cores", str(jobs),
                    "--out-link", str(runtime), "-L"], check=True)
    paths = subprocess.check_output(["nix-store", "--query", "--requisites", str(runtime.resolve())], text=True).splitlines()
    # Only this public derivation's closure is copied; never expose host /nix or a home.
    closure = work / "closure/nix/store"
    closure.mkdir(parents=True)
    for path in paths:
        p = Path(path)
        if p.parent != Path("/nix/store"):
            raise ValueError("Unexpected runtime closure path.")
        if p.is_dir():
            shutil.copytree(p, closure / p.name, symlinks=True)
        else:
            shutil.copy2(p, closure / p.name, follow_symlinks=False)
    staging = work / "arch"
    shutil.copytree(source / "adapters/arch/image", staging)
    (staging / "inputs.lock.json").write_text(json.dumps(inputs, indent=2) + "\n")
    (staging / "runtime-path").write_text(str(runtime.resolve()) + "\n")
    (staging / ".build").mkdir()
    (staging / "dist").mkdir()
    for repo in ("core", "extra"):
        shutil.copyfile(downloaded / (repo + ".db"), staging / "build" / (repo + ".db"))
    tag = "controlstack-arch-builder:" + hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()[:16]
    subprocess.run(["docker", "build", "--build-arg", "BASE_IMAGE=" + inputs["builder_image"],
                    "--build-arg", "ARCH_SNAPSHOT=" + inputs["arch"]["snapshot"], "-t", tag,
                    str(staging / "build")], check=True)
    args = ["docker", "run", "--rm", "--cap-add=SYS_ADMIN", "--security-opt=apparmor=unconfined",
            "--network=bridge", "--mount", f"type=bind,src={staging},dst=/repo",
            "--mount", f"type=bind,src={downloaded},dst=/downloads,readonly",
            "--mount", f"type=bind,src={work / 'closure'},dst=/runtime,readonly",
            "-e", "BUILD_JOBS=" + str(jobs), "-e", "SOURCE_DATE_EPOCH=" + str(lock["source_date_epoch"]),
            "-e", "IMAGE_ID=" + hashlib.sha256(canonical(lock)).hexdigest(),
            "-e", "OUTPUT_UID=" + str(os.getuid()), "-e", "OUTPUT_GID=" + str(os.getgid()),
            tag, "bash", "/repo/scripts/remaster.sh"]
    try:
        subprocess.run(args, check=True)
        images = list((staging / "dist").glob("*.iso"))
        if len(images) != 1:
            raise ValueError("Arch build did not produce exactly one ISO.")
        result = work / images[0].name
        shutil.copyfile(images[0], result)
        return result
    finally:
        # Container root owns extracted files. Clean only its disposable staging
        # using the same isolated mount; never recurse through host mounts.
        subprocess.run(["docker", "run", "--rm", "--network=none", "--mount",
                        f"type=bind,src={staging},dst=/repo", tag,
                        "bash", "-c", "chmod -R ugo+rwX /repo/.build /repo/dist"], check=True)
