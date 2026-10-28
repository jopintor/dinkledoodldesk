---
id: KB-006
title: CourtBook Admin Portal Access and Login
category: accounts-access
audience_roles: [staff, agent, admin]
last_updated: 2026-09-02
owner: Applications Specialist
---

# CourtBook Admin Portal Access and Login

CourtBook Admin is the web portal staff use to manage court schedules, bookings, clinics and member check-in. Members do not use CourtBook Admin; they book through the PickleHub Member App.

Address: `courtbook.picklehub.example/admin`

## CourtBook roles

| CourtBook role | Typical users | What they can do |
|---|---|---|
| Front Desk | Front-desk staff | Check in members, create and move bookings, view the court timeline for their branch |
| Coach | Coaches | View their clinic schedule and roster, mark attendance; cannot move other bookings |
| Branch Manager | Branch managers | Everything Front Desk can do, plus block courts, approve refunds-as-credit, run branch reports |
| Head Office | Operations and finance staff | Read-only reports for all branches |
| System Admin | IT Applications Specialist | Configuration, users and integrations |

## How to sign in

1. Go to `courtbook.picklehub.example/admin`.
2. Choose **Sign in with StaffID**.
3. Enter your StaffID username and password and complete MFA.

There is no separate CourtBook password. If your password does not work, reset your StaffID password (KB-001).

## "You do not have access to this branch"

Your CourtBook role is tied to your home branch. If you cover a shift at another branch:

1. Ask the manager of the branch you are covering to submit an access request for temporary access (KB-010).
2. Temporary branch access lasts up to 14 days and is removed automatically.

## "Your account has no CourtBook role"

You can sign in with StaffID but you see an empty page. This means you have a StaffID but no CourtBook role yet, which is normal for new hires until their manager's access request is approved. Ask your manager to submit the request.

## CourtBook is slow or not loading

1. Check the status page for a CourtBook incident (KB-025).
2. Try a different browser or a private window.
3. Check that other websites load. If nothing loads, the problem is the Wi-Fi or internet, not CourtBook (KB-011).
4. If only CourtBook is affected and the status page is green, raise a ticket. Include your branch, the time, and a screenshot of any error.

## Booking problems

For double bookings and other booking errors, see KB-020.
