---
id: KB-015
title: DinkPOS Front-Desk Troubleshooting
category: pos-payments
audience_roles: [staff, agent, admin]
last_updated: 2026-09-22
owner: Applications Specialist
---

# DinkPOS Front-Desk Troubleshooting

DinkPOS runs on the front-desk and café tablets. It records court fees, pro-shop sales and café orders, and sends card payments to the TapPay card terminal. For card terminal errors, see KB-016. For PIN problems, see KB-007. For the receipt printer and cash drawer, see KB-017.

## First checks for any DinkPOS problem

1. Look at the status page (`status.picklehub.example`) for **DinkPOS** or **Card Payments** at your branch (KB-025). If there is a known incident, follow the offline steps below and do not raise a duplicate ticket.
2. Check whether the tablet has internet: open CourtBook Admin or any website on the same tablet.
3. Close the DinkPOS app fully and open it again.

## DinkPOS shows "Offline mode"

DinkPOS can keep taking **cash** sales while offline and stores them on the tablet.

1. Keep the tablet on and plugged in. Do not log out, uninstall the app or clear its data, or the stored sales may be lost.
2. Take cash payments and QR e-wallet payments as normal. QR payments are confirmed on the e-wallet merchant phone, not in DinkPOS, so write the reference number on the paper offline log at the front desk.
3. Card payments do not work in offline mode. Tell the customer that card payment is temporarily unavailable.
4. When the internet returns, DinkPOS shows **Syncing** and then **Online**. Check that the number of offline sales shown matches your paper log.
5. If DinkPOS stays offline for more than 15 minutes while other devices have internet, raise a ticket.

## The app freezes or crashes

1. Note what you were doing (for example, applying a discount or splitting a bill).
2. Close and reopen the app.
3. If it crashes again at the same step, take a photo of the screen and raise a ticket. Process the sale another way (for example, without the split) if the customer agrees.

## A sale is missing from the sales report

1. Check whether the tablet is in offline mode. Offline sales appear in reports only after syncing.
2. Search for the sale by receipt number in **DinkPOS > Sales history**.
3. If the sale is still missing after sync, raise a ticket with the receipt number, time and amount. Do not re-enter the sale until IT confirms, to avoid double counting.

## Wrong price or missing product

Prices and product lists are managed by head office. Ask your branch manager to raise a request; front-desk staff cannot change prices.

## Priority guide

| Situation | Priority |
|---|---|
| DinkPOS down on every tablet at an open branch, or no payments possible at all | P1 |
| One of two tablets not working, or card payments down but cash works | P2 |
| A single feature not working (for example, discounts) | P3 |

See KB-024 for response times. Outside Service Desk hours (10:00 PM – 7:00 AM), only P1 issues go to the on-call engineer.
