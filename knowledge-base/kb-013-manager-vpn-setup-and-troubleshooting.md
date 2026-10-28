---
id: KB-013
title: HubConnect VPN for Branch Managers - Setup and Troubleshooting
category: network
audience_roles: [staff, agent, admin]
last_updated: 2026-03-01
owner: Systems and Network Administrator
---

# HubConnect VPN for Branch Managers - Setup and Troubleshooting

HubConnect is PickleHub's VPN. It lets you reach head-office systems, such as DinkPOS Back Office reports and HubWatch, when you are away from the branch. It replaces the remote access rules from 2024 (KB-014 is superseded).

## Who can use HubConnect

Since **1 March 2026**, HubConnect is available only to:

- Branch managers
- IT staff
- Other staff with a written exception from the IT Lead (for example, finance staff during month-end closing)

Each request needs **Operations Head** approval through an access request (KB-010). Coaches and front-desk staff do not need VPN; CourtBook Admin and HubMail work over the normal internet.

## Requirements

- A company laptop. HubConnect is not allowed on personal computers.
- Your StaffID username and password, plus MFA (KB-004).
- The HubConnect client, installed by IT.

## Connecting

1. Open the **HubConnect** app.
2. Click **Connect**.
3. Sign in with your StaffID and approve the MFA prompt.
4. When the icon turns green, you are connected. All your laptop's traffic now goes through the head office (full tunnel).
5. Disconnect when you are finished. Sessions end automatically after **10 hours**.

## Troubleshooting

### "Authentication failed"

1. Check your StaffID password by signing in to HubMail in a browser.
2. If HubMail also fails, reset your password (KB-001) or wait out a lockout (KB-003).
3. If HubMail works but the VPN does not, your VPN access may not be active. Ask DinkDesk to check your access request status.

### Connects, then drops after a few minutes

1. Move closer to your Wi-Fi router, or try a phone hotspot to rule out a weak home connection.
2. Some hotel and café networks block VPNs. Try a different network.
3. Restart the HubConnect app.

### Connected, but head-office systems do not open

1. Disconnect and connect again.
2. Make sure you typed the internal address correctly (for example `backoffice.dinkpos.internal`).
3. Check the status page for **HubConnect VPN** (KB-025).

### VPN works but my home internet is slow

This is expected with a full-tunnel VPN, because all traffic travels through the head office. Disconnect HubConnect when you do not need head-office systems.

## When to raise a ticket

If the steps above do not help, ask DinkDesk to raise a ticket. Include the error message, the time and the network you were on (home, mobile data, hotel). A single manager's VPN problem is P3; VPN down for all users is P2 (KB-024).

## Security rules

- Never let family members or others use your laptop while connected.
- Do not save your StaffID password in the VPN client.
- Lost company laptop: report it the same day to `security@picklehub.example` (KB-027).
