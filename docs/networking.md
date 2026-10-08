# Network setup

NetworkManager owns live and installed networking. It uses its DBus-controlled
wpa_supplicant for Wi-Fi; iwd, networkd, dhcpcd and resolved are not competing
owners. Ethernet is automatic. Wi-Fi setup turns on the software radio and opens
NetworkManager's protected connection menu when an adapter is available.

A hardware airplane-mode switch cannot be cleared in software. Setup explains
that case separately. If only loopback (`lo`) exists, it explains that no network
adapter is available and suggests Ethernet or phone USB tethering rather than
opening an empty connection menu. These are possible fallbacks, not proof of a
specific adapter's driver support.

Choosing sign-in before connecting is valid. The network check runs first and
returns to setup without changing credentials or disabling networking. Secure
connection and clock failures remain separate from disconnected networking.

## First-image regression

The first Ventoy NixOS image forced `networking.wireless.enable = false`. In the
pinned NixOS module this also removes the supplicant needed by NetworkManager.
The corrected live and generated target profiles share `networking.nix` so this
setting cannot drift between the USB and installed system.

The regression test uses Linux 7.2.9, two simulated wireless radios and a local
WPA2 access point. It verifies discovery, authentication, connection state,
software radio blocking and reconnection. Its public fixture password is not a
real account or network credential. A separate actual-ISO test follows failed
offline sign-in with network setup and checks the no-adapter explanation.

The reported HP ZBook Firefly G11 uses Intel AX211 (8086:7e40), with iwlwifi.
The image contains the driver's required `iwlwifi-ma-b0-gf-a0-89.ucode` and PNVM
firmware. Presence of those files does not prove successful initialization on
physical hardware. That hardware retest remains separate from simulated Wi-Fi.
