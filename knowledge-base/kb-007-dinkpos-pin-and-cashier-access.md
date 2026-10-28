---
id: KB-007
title: DinkPOS Cashier PIN Reset and Cashier Access
category: pos-payments
audience_roles: [staff, agent, admin]
last_updated: 2026-08-18
owner: Applications Specialist
---

# DinkPOS Cashier PIN Reset and Cashier Access

DinkPOS is the point-of-sale system on the front-desk and café tablets. Each cashier has a **Cashier ID** and a **6-digit PIN**. DinkPOS does not use StaffID, so a StaffID reset does not change your PIN.

## PIN rules

- Exactly 6 digits.
- No repeated or sequential patterns such as 111111 or 123456.
- Never share your PIN or let another cashier ring sales under your Cashier ID. Every sale, void and discount is logged against the Cashier ID that entered it.

## My PIN is locked

DinkPOS locks a Cashier ID after **3 wrong PIN entries in a row**.

1. Ask your **branch manager** (or the shift supervisor with manager rights) to unlock it.
2. The manager signs in to **DinkPOS Back Office > Staff > Cashiers**, selects your Cashier ID and chooses **Unlock and reset PIN**.
3. DinkPOS shows a one-time PIN. Sign in with it and set a new 6-digit PIN right away.

If no manager is on duty, ask DinkDesk to raise a ticket. The Service Desk will call the branch phone, confirm your identity with the person in charge on site and reset the PIN. During the wait, another cashier on shift may process sales under **their own** Cashier ID.

## I forgot my PIN but it is not locked

Do not keep guessing. Ask your manager to reset it using the same steps as above.

## Getting a new Cashier ID

New cashiers need:

1. An access request from the branch manager (KB-010) stating the branch and the role: **Cashier**, **Café Cashier** or **Supervisor**.
2. Completion of the 30-minute DinkPOS cash-handling orientation.

Supervisor rights (voids, refunds and discounts above PHP 500) need approval from the Operations Head in addition to the branch manager.

## Cashier IDs when someone leaves

The branch manager must ask IT to disable a departing cashier's ID on their last day (KB-021). Never reassign a Cashier ID to a different person.

## Who can reset what

| Request | Who handles it |
|---|---|
| Locked or forgotten PIN | Branch manager, or IT Service Desk if no manager is available |
| New Cashier ID | IT Service Desk after manager approval |
| Supervisor rights | IT Service Desk after manager and Operations Head approval |
| DinkPOS Back Office (manager) password | IT Service Desk only |

DinkDesk cannot reset DinkPOS PINs directly. It can explain these steps and create a ticket.
