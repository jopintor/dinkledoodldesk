---
id: KB-003
title: Locked StaffID Account
category: accounts-access
audience_roles: [staff, agent, admin]
last_updated: 2026-09-15
owner: Systems and Network Administrator
---

# Locked StaffID Account

## Why accounts get locked

StaffID locks an account after **5 failed sign-in attempts within 15 minutes**. This protects you if someone is guessing your password. Common causes:

- Typing the password wrong several times (Caps Lock is a frequent culprit).
- An old password saved on a phone, tablet or Wi-Fi profile that keeps retrying in the background after you changed it.
- Someone else trying to sign in as you.

## What a locked account looks like

- Sign-in pages show "Your account is temporarily locked."
- The `PickleHub-Staff` Wi-Fi keeps rejecting your password.
- HubMail on your phone keeps asking for a password.

## Steps to unlock

1. **Wait 15 minutes.** The lock clears by itself. Do not keep retrying during this time, because each attempt can restart the timer.
2. While you wait, find the device that keeps using an old password. Check your phone mail app, the Wi-Fi settings on your phone and laptop, and any shared front-desk tablet you signed into.
3. Update or remove the old saved password on those devices.
4. After 15 minutes, sign in once, carefully.
5. If you do not remember the password, reset it instead (KB-001). A reset also clears the lock.

## When to contact IT

Contact the Service Desk or ask DinkDesk to raise a ticket if:

- The account locks again within an hour after you fixed all your devices.
- You see sign-in alerts from places or devices you do not recognise. Treat this as a possible security incident (KB-027) and mark the ticket as urgent.
- You are a front-desk staff member, the branch is open, and you cannot check members in. This is handled as P2 (KB-024).

## Notes for agents

- Check the StaffID sign-in log for the source of the failed attempts before unlocking manually.
- If the failures come from an unknown IP or country, do not unlock. Force a password reset, revoke sessions and escalate to the Systems and Network Administrator.
- Manual unlocks must be recorded in the ticket with the reason.

## Other lockouts

- **DinkPOS PIN locked** after 3 wrong PIN entries: see KB-007.
- **Member App account locked** after 5 wrong passwords (locks for 30 minutes): see KB-018.
