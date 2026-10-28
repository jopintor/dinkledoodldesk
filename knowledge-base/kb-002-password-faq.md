---
id: KB-002
title: Password FAQ for Staff Systems
category: accounts-access
audience_roles: [staff, agent, admin]
last_updated: 2026-08-02
owner: IT Service Desk
---

# Password FAQ for Staff Systems

Quick answers to the password questions the Service Desk hears most often. For the full StaffID reset procedure, see KB-001.

## Which systems share one password?

StaffID covers HubMail, CourtBook Admin, `PickleHub-Staff` Wi-Fi and HubConnect VPN. If you reset StaffID, all four use the new password.

These systems have **separate** credentials:

| System | Credential | Where to get help |
|---|---|---|
| DinkPOS | Cashier ID and 6-digit PIN | KB-007 |
| RallyBracket | Email and RallyBracket password | KB-008 |
| HubWatch CCTV | HubWatch username and password | KB-009 |
| PickleHub Member App | Member email and password | KB-018 |

## I forgot my StaffID password. What is the quickest fix?

Use the self-service portal at `id.picklehub.example/reset`. You need your MFA app or registered mobile. If that fails, ask DinkDesk to reset it for you; it will verify you with a one-time code first.

## How long is the temporary password valid?

24 hours. After that it expires and you need another reset.

## How often must I change my password?

StaffID passwords do not expire on a schedule. Change it if you suspect someone else knows it, after a phishing scare, or when IT tells you to.

## What makes a valid password?

At least 12 characters, not containing your name, username or "picklehub", and different from your last 5 passwords.

## Can I use the same password for StaffID and RallyBracket?

You should not. RallyBracket is an outside service. If it is ever breached, a reused password would expose your StaffID too. Use a different password for each system.

## Can my manager or a co-worker reset my password for me?

No. Only you (through the portal or DinkDesk) or the IT Service Desk after verifying your identity can reset a StaffID password. Managers can unlock DinkPOS PINs for their own branch, but not StaffID.

## Can I share my login with the front-desk team for one shift?

No. Shared logins break the audit trail in CourtBook and DinkPOS and are against the Acceptable Use Policy (KB-022). Ask for your own account through an access request (KB-010).

## Someone called me from "IT" asking for my password. Is that normal?

No. IT never asks for your password, PIN or MFA code by phone, chat or email. The only exception is the one-time verification code DinkDesk itself asks for during a reset you started. Report the call to `security@picklehub.example`.

## My password works on the computer but not on Wi-Fi.

Your phone or laptop probably saved the old password. Forget the `PickleHub-Staff` network and connect again (KB-011).
