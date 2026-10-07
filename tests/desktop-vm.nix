# Desktop-only iteration, with synthetic audio devices and no account credentials.
{ pkgs, aiTools }:
pkgs.testers.runNixOSTest {
  name = "controlstack-desktop";
  enableOCR = true;
  nodes.machine = { pkgs, lib, ... }: {
    imports = [ (import ../adapters/nixos/desktop.nix { desktop = "hyprland"; inherit aiTools; }) ];
    networking.networkmanager.enable = true;
    users.users.owner = { isNormalUser = true; extraGroups = [ "wheel" "networkmanager" ]; password = "vm-only"; };
    services.displayManager.autoLogin = { enable = true; user = "owner"; };
    virtualisation = { memorySize = 3072; cores = 2; qemu.options = [ "-vga virtio" ]; };
    environment.systemPackages = [ pkgs.python3 pkgs.pulseaudio ];
    services.pipewire.extraConfig.pipewire."99-test-devices"."context.objects" = map (device: {
      factory = "adapter";
      args = { "factory.name" = "support.null-audio-sink"; "node.name" = device.name; "node.description" = device.description;
        "media.class" = device.class; "audio.position" = "FL,FR"; };
    }) [
      { name = "test-speakers"; description = "Studio speakers"; class = "Audio/Sink"; }
      { name = "test-headphones"; description = "USB headphones"; class = "Audio/Sink"; }
      { name = "test-microphone"; description = "Desk microphone"; class = "Audio/Source"; }
      { name = "test-headset"; description = "Headset microphone"; class = "Audio/Source"; }
    ];
  };
  testScript = ''
    import time, json, csv, io, struct, subprocess
    def click_label(label, occurrence=None):
        machine.screenshot("interaction")
        shot = machine.out_dir / "interaction.png"
        width, height = struct.unpack(">II", shot.read_bytes()[16:24])
        tsv = subprocess.check_output(["${pkgs.tesseract}/bin/tesseract", str(shot), "stdout", "tsv"], text=True)
        lines = {}
        for word in csv.DictReader(io.StringIO(tsv), delimiter="\t", quoting=csv.QUOTE_NONE):
            if word["text"].strip():
                key = tuple(word[k] for k in ("page_num", "block_num", "par_num", "line_num"))
                lines.setdefault(key, []).append(word)
        matches = []
        for line in lines.values():
            for start in range(len(line)):
                for end in range(start + 1, len(line) + 1):
                    if " ".join(w["text"].strip(".,:;\"\'") for w in line[start:end]).lower() == label.lower():
                        matches.append(line[start:end])
        assert matches and (occurrence is not None or len(matches) == 1), (label, [" ".join(w["text"] for w in words) for words in lines.values()])
        matches.sort(key=lambda words: int(words[0]["top"]))
        words = matches[0 if occurrence is None else occurrence]
        x = (min(int(w["left"]) for w in words) + max(int(w["left"]) + int(w["width"]) for w in words)) / 2
        y = (min(int(w["top"]) for w in words) + max(int(w["top"]) + int(w["height"]) for w in words)) / 2
        events = [{"type": "abs", "data": {"axis": "x", "value": int(x * 32767 / width)}},
                  {"type": "abs", "data": {"axis": "y", "value": int(y * 32767 / height)}}]
        assert machine.qmp_client is not None
        machine.qmp_client.send("input-send-event", json.loads(json.dumps({"events": events})))
        for down in (True, False):
            machine.qmp_client.send("input-send-event", json.loads(json.dumps({"events": [{"type": "btn", "data": {"button": "left", "down": down}}]})))
        machine.qmp_client.send("input-send-event", json.loads(json.dumps({"events": [
            {"type": "abs", "data": {"axis": "x", "value": 16384}},
            {"type": "abs", "data": {"axis": "y", "value": 30000}}]})))
        time.sleep(1)
        return events

    machine.start()
    machine.wait_for_unit("display-manager.service")
    owner = "runuser -u owner -- env XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus "
    gui = owner + "systemd-run --user --quiet --wait --pipe "
    machine.wait_until_succeeds(owner + "systemctl --user is-active controlstack-shell")
    machine.wait_until_succeeds(gui + "quickshell -c controlstack ipc show", timeout=90)
    time.sleep(3)
    errors = json.loads(machine.succeed(gui + "hyprctl -j configerrors"))
    assert not any(str(error).strip() for error in errors), errors
    print(machine.succeed("journalctl -b _SYSTEMD_USER_UNIT=controlstack-shell.service --no-pager"))
    machine.succeed("! journalctl -b _SYSTEMD_USER_UNIT=controlstack-shell.service --no-pager | grep -E 'Failed to load configuration|ReferenceError|TypeError|Could not load icon'")
    machine.screenshot("desktop")
    machine.succeed(gui + "quickshell -c controlstack ipc call shell launcher")
    time.sleep(2)
    machine.screenshot("launcher")
    machine.send_chars("mousepad")
    machine.send_key("ret")
    machine.wait_until_succeeds("pgrep -u owner -f '[m]ousepad'")
    machine.succeed(gui + "quickshell -c controlstack ipc call shell controls")
    time.sleep(2)
    machine.screenshot("controls")
    print(machine.succeed(gui + "wpctl status"))
    click_label("USB headphones")
    machine.wait_until_succeeds(gui + "wpctl inspect @DEFAULT_AUDIO_SINK@ | grep test-headphones")
    click_label("Headset microphone")
    machine.wait_until_succeeds(gui + "wpctl inspect @DEFAULT_AUDIO_SOURCE@ | grep test-headset")
    machine.screenshot("audio-selected")
    mute_position = click_label("Mute", occurrence=1)
    machine.wait_until_succeeds(gui + "wpctl get-volume @DEFAULT_AUDIO_SOURCE@ | grep MUTED")
    # Click the same visible toggle again; selected outlines confuse OCR segmentation.
    assert machine.qmp_client is not None
    machine.qmp_client.send("input-send-event", json.loads(json.dumps({"events": mute_position})))
    for down in (True, False):
        machine.qmp_client.send("input-send-event", json.loads(json.dumps({"events": [{"type": "btn", "data": {"button": "left", "down": down}}]})))
    time.sleep(1)
    machine.succeed(gui + "wpctl get-volume @DEFAULT_AUDIO_SOURCE@ | grep -v MUTED")
    machine.succeed(gui + "quickshell -c controlstack ipc call shell network")
    time.sleep(2)
    machine.screenshot("network")
    machine.send_key("esc")
    machine.succeed(owner + "codex --version")
    machine.succeed(owner + "claude --version")
    machine.succeed("test -x $(dirname $(readlink -f $(command -v codex)))/codex-code-mode-host")
    machine.succeed("test -x $(dirname $(readlink -f $(command -v codex)))/logs_client")
    machine.succeed(owner + "nvim --headless '+lua assert(vim.o.number)' +qall")
    machine.succeed("pkill -u owner mousepad")
    # Autologin deliberately skips PAM authentication; unlock a disposable fixture keyring.
    machine.succeed("printf vm-only | " + gui + "gnome-keyring-daemon --unlock")
    for app, match in [("chatgpt", "chatgpt"), ("claude-desktop", "claude")]:
        machine.succeed(owner + "systemd-run --user --quiet --unit=app-test " + app + (" codex://" if app == "chatgpt" else ""))
        machine.wait_until_succeeds(gui + "hyprctl -j clients | grep -i " + match, timeout=120)
        try:
            machine.wait_for_text("Sign in|Log in|Welcome|Get started", timeout=90)
        finally:
            machine.screenshot(app)
            print(machine.succeed(owner + "journalctl --user -u app-test --no-pager -n 80"))
        machine.succeed("! journalctl -b --no-pager | grep -E 'GLIBC_[0-9.]+.*not found'")
        machine.succeed(owner + "systemctl --user stop app-test")
    machine.succeed("! journalctl -b _SYSTEMD_USER_UNIT=controlstack-shell.service --no-pager | grep -E 'Failed to load configuration|ReferenceError|TypeError|Could not load icon'")
  '';
}
