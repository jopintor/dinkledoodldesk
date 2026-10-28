---
id: KB-011
title: Staff Wi-Fi (PickleHub-Staff) Troubleshooting
category: network
audience_roles: [staff, agent, admin]
last_updated: 2026-08-25
owner: Systems and Network Administrator
---

# Staff Wi-Fi (PickleHub-Staff) Troubleshooting

## The three club networks

| Network name (SSID) | For | How to join |
|---|---|---|
| `PickleHub-Staff` | Employees' work phones and laptops | StaffID username and password |
| `PickleHub-Members` | Members and walk-in guests | Captive portal sign-in (see KB-012) |
| `PickleHub-Devices` | POS tablets, card terminals, printers, cameras | Hidden; set up by IT only |

Staff should use `PickleHub-Staff` for work. Do not connect personal devices or guests to `PickleHub-Devices`, and never share its password if you happen to see it.

## Connecting for the first time

1. Choose `PickleHub-Staff` from the Wi-Fi list.
2. Enter your StaffID username (`firstname.lastname`) and password.
3. If your device asks about a certificate, check that it is for `radius.picklehub.example` and choose **Trust** or **Connect**.
4. On Android, if asked: EAP method **PEAP**, Phase 2 **MSCHAPV2**, CA certificate **Use system certificates**, domain `picklehub.example`.

## Wi-Fi keeps asking for my password

This is the most common issue, and it usually happens after a StaffID password reset.

1. Open Wi-Fi settings and choose **Forget** on `PickleHub-Staff`.
2. Connect again with your current StaffID password.
3. Do this on every device that uses `PickleHub-Staff`. An old password saved on one device can lock your whole account (KB-003).

## Connected but no internet

1. Turn Wi-Fi off and on again.
2. Check if other staff nearby have the same problem.
3. Check the status page (`status.picklehub.example`) for **Staff Wi-Fi – [your branch]** (KB-025).
4. If only you are affected, restart your device and forget/re-add the network.
5. If several people at the branch are affected and the status page is green, raise a ticket with the branch, the area of the club (for example, front desk or café) and the time it started. Several users at one branch is P2 (KB-024).

## Weak signal in some areas

The covered outdoor courts at General Trias and the open-air courts at Tagaytay have limited staff Wi-Fi coverage by design. If you need coverage in a new area for work, raise a request; the Systems and Network Administrator will do a site check.

## What not to do

- Do not restart, unplug or move the access points or the network cabinet. Ask IT.
- Do not set up your phone hotspot for the POS tablets. If the internet is down, follow the offline steps in KB-015.
