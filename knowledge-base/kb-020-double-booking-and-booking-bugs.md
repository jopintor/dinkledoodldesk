---
id: KB-020
title: Double-Booked Courts and Other Booking Bugs
category: member-app-booking
audience_roles: [member, staff, agent, admin]
last_updated: 2026-10-12
owner: Applications Specialist
---

# Double-Booked Courts and Other Booking Bugs

## Known issue: double bookings

**Status: known issue, fix in progress with the CourtBook vendor (tracked as ITH-1187).**

Rarely, two members can book the same court and time slot. This happens when both bookings are made within about two minutes of each other while the Member App and CourtBook are syncing, most often right after midnight when new dates open.

## Which booking is valid

**CourtBook is the official record.** The booking with the **earlier confirmation time** in CourtBook keeps the court. The confirmation time is shown in the booking details in CourtBook Admin and in the app under **My Bookings > Details**.

## What front-desk staff should do

1. Open CourtBook Admin and go to **Court Timeline** for the court and time.
2. Open both bookings and compare the confirmation times.
3. Give the court to the member with the earlier confirmation.
4. Offer the other member, in this order:
   1. Another free court at the same time, or
   2. A different time slot the same day, or
   3. Cancellation with full app credit (branch managers can approve this in CourtBook).
5. Report the double booking (see "How to report a booking bug" below), even if you solved it on the spot. Each report helps the vendor find the cause.

## What members should do

1. Show your booking in the app to the front desk. Staff will follow the steps above.
2. If you were moved or credited and want to report the problem, use **Help > Report a problem** in the app.

## Other booking bugs

| Problem | Quick check | Then |
|---|---|---|
| Paid but booking missing | Refresh **My Bookings**; wait 10 minutes | Report with the payment reference. Do not book again. |
| Booking shows wrong branch or time | Check the branch selected at the top of the **Book** screen | Report with the `BK-` reference |
| Clinic shows full but roster has space | Refresh; check if the clinic is restricted to a home branch | Report with clinic name and date |
| Court shows booked but is empty | Check CourtBook Court Timeline for blocks set by the branch manager | Ask the manager; report only if no block exists |

## How to report a booking bug

Ask DinkDesk to create a ticket, or use the app's **Help > Report a problem**. Include:

- The booking reference(s), which look like `BK-` followed by six digits
- The branch, court number, date and time
- What you expected and what happened
- A screenshot if possible

Do **not** include members' phone numbers, emails or payment card details in the report. The booking reference is enough for IT to find the records.

## Priority

A single double booking is **P3**. If CourtBook or the app is creating many wrong bookings at once, or no one can book, it is **P1** (KB-024).
