# Security keys and assistant sign-in

The installed desktop includes FIDO device permissions and a **Coding Assistant
Sign-in** application. It runs as the desktop owner, checks whether Codex already
has a saved login, and offers the official browser or device-code flow. This wrapper does not read or print credential values. It does not import
credentials from the build machine or copy them between OpenClaw and Codex.

A plugged-in YubiKey is not itself a Codex login. The official Codex authentication
interface documents browser OAuth and device-code authentication, not a direct
security-key token exchange. If the account's browser sign-in provider offers a
registered security key/passkey, use it there. The browser/provider may require
user presence, a touch, PIN, account selection or consent. Account/provider support
and a real physical key still need hardware qualification.

On a text-only live USB, use the official device-code flow on a phone or another
computer. A key must be available to **that browser**. A key attached to the live
console is not forwarded to the phone. Local browser login from the live image
requires a graphical live session; that experience is not implemented yet.

Codex normally retains and refreshes an installed account's login. This can avoid
repeated sign-in after initial authorization, but it does not mean tokens are
stored on the YubiKey or bound to its continued presence. Removing the key does
not revoke an existing OAuth session. This project does not silently enroll a
key, alter account MFA, configure PAM/disk unlock, or provision credentials onto
a key.

The resident OpenClaw assistant has separate provider onboarding and separate
private state. Signing in to the owner’s Codex CLI does not sign in OpenClaw.
Live OpenClaw credentials stay in RAM; installation still creates fresh resident
state and asks for fresh provider authorization.

Official source checked 2026-10-07:
[Codex authentication](https://learn.chatgpt.com/docs/auth), including browser
login, device-code availability, login caching and credential storage.
