---
id: KB-001
title: How to Reset Your StaffID Password
category: accounts-access
audience_roles: [staff, agent, admin]
last_updated: 2026-09-15
owner: Systems and Network Administrator
---

# How to Reset Your StaffID Password

Your StaffID password is the one password you use for HubMail, CourtBook Admin, the `PickleHub-Staff` Wi-Fi and the HubConnect VPN. Changing it changes it everywhere at once.

This guide does **not** cover DinkPOS PINs (see KB-007), RallyBracket (KB-008), HubWatch (KB-009) or the Member App (KB-018). Those systems have their own passwords.

## Before you start

- You need access to your MFA method (authenticator app or registered mobile number). If you lost your phone, follow KB-004 first.
- If your account says **locked**, see KB-003. A lockout clears by itself after 15 minutes; a reset is not always needed.
- IT staff will never ask for your current or new password. Do not type your password into DinkDesk chat, email or a ticket.

## Option 1: Self-service reset portal (fastest)

1. Open `id.picklehub.example/reset` on any device.
2. Enter your StaffID username (`firstname.lastname`).
3. Approve the MFA prompt or enter the 6-digit code sent to your registered mobile number.
4. Choose a new password that follows the rules below.
5. Sign in again on every device that uses StaffID (phone email app, front-desk tablet, laptop). Old sessions are signed out after a reset.

## Option 2: Ask DinkDesk to reset it

DinkDesk can trigger a reset for `staff` users when the self-service portal does not work for you.

1. Tell DinkDesk you need a StaffID password reset.
2. DinkDesk asks for your employee number and sends a one-time code to the mobile number on file in StaffID.
3. Type the one-time code into the chat. This is the only code you should ever share with DinkDesk.
4. DinkDesk sends a temporary password to the personal recovery email address on file in StaffID. It is never shown in the chat. It is valid for 24 hours.
5. Sign in with the temporary password. You will be asked to set a new password immediately.

DinkDesk cannot reset someone else's password, even for a manager asking on behalf of a team member. The person must request it themselves, or the manager raises a ticket and the Service Desk calls the employee to verify identity.

## Option 3: Contact the Service Desk

If you have no access to your MFA method or registered mobile number, contact the Service Desk (extension 4357 or `it-help@picklehub.example` from a colleague's account). An agent will verify you in person through your branch manager or by video call with your company ID before resetting.

## StaffID password rules

- At least 12 characters. A short phrase of unrelated words works well.
- Cannot contain your name, username or the word "picklehub".
- Cannot match any of your last 5 passwords.
- No forced expiry. Change it only when you think it may be known to someone else, or when IT asks you to.

## After the reset

- Reconnect to `PickleHub-Staff` Wi-Fi with the new password (see KB-011 if it keeps prompting).
- Update the password in your phone's mail app.
- If you did not request a reset but received a reset email or code, report it to `security@picklehub.example` right away (KB-027).
