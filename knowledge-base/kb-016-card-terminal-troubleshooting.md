---
id: KB-016
title: TapPay Card Terminal Errors and Declined Payments
category: pos-payments
audience_roles: [staff, agent, admin]
last_updated: 2026-09-22
owner: Applications Specialist
---

# TapPay Card Terminal Errors and Declined Payments

Each front desk has a TapPay countertop terminal for card and contactless payments. The terminal belongs to PickleHub's acquiring bank and is linked to DinkPOS: DinkPOS sends the amount, the customer taps or inserts the card, and the result comes back to DinkPOS.

## Common terminal messages

| Message on terminal | What it means | What to do |
|---|---|---|
| **APPROVED** | Payment went through | Hand over the receipt |
| **DECLINED - CONTACT ISSUER** | The customer's bank refused the payment | Ask for another card or payment method. Do not retry the same card more than twice. This is not an IT problem. |
| **CARD READ ERROR** | Chip or tap could not be read | Ask the customer to insert the chip instead of tapping, or the other way round. Wipe the card reader slot gently with a dry cloth. |
| **NO LINE / HOST UNREACHABLE** | Terminal cannot reach the bank | See "Terminal cannot connect" below |
| **NOT PAIRED** | Terminal lost its link to DinkPOS | Restart the terminal, then the DinkPOS app. If still showing, raise a ticket. |
| **PAPER OUT** | Terminal receipt roll is empty | Replace the roll (spare rolls are in the front-desk drawer) |

## Terminal cannot connect

1. Check the status page for **Card Payments** at your branch (KB-025).
2. Check that DinkPOS itself is online (KB-015).
3. Restart the terminal: hold the power button for 5 seconds, then turn it on again. Wait 2 minutes for it to reconnect.
4. Make sure the terminal is still on its stand and its cable is plugged in. Do not move the terminal to a different network or hotspot.
5. If it still cannot connect, take cash or QR e-wallet payments and raise a ticket. Card payments down at a branch is **P2**; if no payment method at all is working, it is **P1** (KB-024).

## The customer was charged but DinkPOS shows "failed"

This can happen if the connection dropped mid-payment.

1. **Do not charge the card again.**
2. Check the terminal's last transaction: press **Menu > Last receipt**.
3. If the terminal shows APPROVED, mark the DinkPOS sale as paid by card using **Manual card confirmation** and write the terminal's approval code in the note.
4. If you are unsure, record the time, amount and last 4 digits of the card on the paper incident log and raise a ticket. The Applications Specialist checks with the bank.

## Refunds and disputed charges

Card refunds must be done by the branch manager in DinkPOS Back Office. Questions about chargebacks or settlement go to Finance, not IT.

## Card data rules

- Never write down, photograph or type a full card number anywhere, including tickets and DinkDesk chat. Last 4 digits are enough.
- Never key in a card number by hand on the terminal.
- Never let anyone you do not know, even someone claiming to be from the bank, open, swap or update the terminal without a ticket from IT confirming the visit.

## Contacting the bank

The bank's merchant hotline is printed on the sticker under each terminal. The Service Desk normally calls the bank for you; call directly only if IT asks you to or during a P1 after hours.
