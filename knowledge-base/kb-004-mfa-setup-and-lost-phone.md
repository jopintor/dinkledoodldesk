---
id: KB-004
title: Setting Up MFA and What to Do If You Lose Your Phone
category: accounts-access
audience_roles: [staff, agent, admin]
last_updated: 2026-07-21
owner: Systems and Network Administrator
---

# Setting Up MFA and What to Do If You Lose Your Phone

Multi-factor authentication (MFA) is required on every StaffID account. After your password, you confirm the sign-in with a second step on your phone.

## Accepted MFA methods

| Method | Notes |
|---|---|
| Authenticator app (recommended) | Any standard TOTP app, such as Google Authenticator or Microsoft Authenticator |
| SMS code to registered mobile | Allowed as a backup method |

## First-time setup (new employees)

1. Sign in at `id.picklehub.example` with the temporary password from your onboarding email.
2. Set your own password (rules are in KB-001).
3. When asked to set up MFA, open your authenticator app and scan the QR code on screen.
4. Enter the 6-digit code from the app to confirm.
5. Add your mobile number as a backup method.
6. Save the 10 printed backup codes somewhere safe and private, such as a locked drawer at home. Do not save them in a photo on the same phone.

## Changing to a new phone (you still have the old one)

1. Install the authenticator app on the new phone.
2. Sign in at `id.picklehub.example`, go to **Security > MFA methods** and choose **Add authenticator**.
3. Scan the QR code with the new phone and confirm the code.
4. Remove the old phone from the list.

## Lost or stolen phone

1. **Report it the same day.** Ask DinkDesk to create a ticket or email `security@picklehub.example`. Say whether the phone had HubMail or company data on it.
2. If you still have backup codes, use one to sign in and remove the lost phone from your MFA methods yourself.
3. If you have no backup codes, the Service Desk will verify your identity (company ID on a video call, or in person with your branch manager present) and then reset your MFA.
4. IT will sign the lost phone out of HubMail and other StaffID apps.
5. Set up MFA again on your replacement phone.

DinkDesk cannot reset MFA by chat, because the person chatting may be the one holding your lost phone.

## Tips

- Never approve an MFA prompt you did not start. Report unexpected prompts to `security@picklehub.example`.
- If your codes are always rejected, check that your phone's clock is set to automatic time.
