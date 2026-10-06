# Friendly first-run flow

The intended flow asks one concrete question at a time and does the inspection on
the device. The owner should never need to copy inventories into another chat.

1. Explain the local assistant's role: “I can help you look after this computer.”
2. Detect Ethernet. If unavailable, ask “Would you like to connect to Wi-Fi?” and
   use the image's NetworkManager flow. Keep a troubleshooting shell available.
3. Check internet, then secure connections and synchronized time. A disconnect
   after a menu selection must return to this same flow and block sign-in.
4. Ask for the desired provider route. Use a supported official browser/device
   flow or masked interactive secret input. Never reuse the installer’s credentials.
5. Verify a real provider response, then explain the concrete access plan. Reading
   system status is the default. Enabling more access is a separate owner choice.
6. Open the local conversation and retain a clear reopen command.

Implemented: readiness gates before mutable CLI onboarding; isolated runtime
context; official interactive onboarding invocation; declarative Nix service;
identity language and reopen via `system-agent chat`.
Not implemented: a complete continuous novice UI, Wi-Fi menu integration, a
NixOS secret/provider setup UI, and verified subscription login in this image.
Readiness to the project/package endpoints does not prove a provider is reachable;
the native onboarding live inference check must establish that separately.

On Arch, the official interactive wizard owns masked input. No wrapper accepts
API keys as argv. On NixOS, the wrapper refuses mutable onboarding and points to
declarative provider configuration rather than pretending the wizard can rewrite
a store-managed config. A future UI should stage non-secret declarative choices
and write secrets directly to private runtime storage through an approved helper.
