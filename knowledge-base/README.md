# DinkDesk Knowledge Base — PickleHub Clubs

This folder is the source of truth for DinkDesk's retrieval-augmented answers. Every file is an original, fictional SOP, FAQ or policy for **PickleHub Clubs, Inc.**, a made-up chain of pickleball clubs in Cavite. Names, phone numbers, emails (`*.picklehub.example`) and URLs are placeholders.

## File format

Each document is Markdown with YAML frontmatter:

```yaml
---
id: KB-001                      # stable ID, cited in answers and used by the golden set
title: How to Reset Your StaffID Password
category: accounts-access       # see categories below
audience_roles: [staff, agent, admin]   # who may retrieve it (member | staff | agent | admin)
last_updated: 2026-09-15
owner: Systems and Network Administrator
---
```

Optional fields used by one document only: `status: superseded` and `superseded_by: KB-013` (see KB-014).

Documents use `#` for the title, `##`/`###` for sections and numbered lists for procedures, so the ingestion step can split on headings and keep each chunk self-contained.

## Categories

| Category | Covers |
|---|---|
| `company` | Company profile, branches, systems, IT team, contacts |
| `accounts-access` | Passwords, lockouts, MFA, system accounts, access requests, joiners and leavers |
| `network` | Club Wi-Fi and VPN |
| `pos-payments` | DinkPOS, card terminals, printers and cash drawers |
| `member-app-booking` | Member App sign-in, app FAQ, booking bugs |
| `policy` | Acceptable use and data privacy |
| `security` | Phishing and incident reporting |
| `support-process` | SLAs, escalation, status page, how to get help |

## Index

| ID | File | Title | Category | Audience |
|---|---|---|---|---|
| KB-000 | [kb-000-company-profile.md](kb-000-company-profile.md) | PickleHub Clubs Company Profile and IT Overview | company | member, staff, agent, admin |
| KB-001 | [kb-001-staffid-password-reset.md](kb-001-staffid-password-reset.md) | How to Reset Your StaffID Password | accounts-access | staff, agent, admin |
| KB-002 | [kb-002-password-faq.md](kb-002-password-faq.md) | Password FAQ for Staff Systems | accounts-access | staff, agent, admin |
| KB-003 | [kb-003-account-lockout.md](kb-003-account-lockout.md) | Locked StaffID Account | accounts-access | staff, agent, admin |
| KB-004 | [kb-004-mfa-setup-and-lost-phone.md](kb-004-mfa-setup-and-lost-phone.md) | Setting Up MFA and What to Do If You Lose Your Phone | accounts-access | staff, agent, admin |
| KB-005 | [kb-005-hubmail-email-issues.md](kb-005-hubmail-email-issues.md) | HubMail Staff Email Problems | accounts-access | staff, agent, admin |
| KB-006 | [kb-006-courtbook-admin-access.md](kb-006-courtbook-admin-access.md) | CourtBook Admin Portal Access and Login | accounts-access | staff, agent, admin |
| KB-007 | [kb-007-dinkpos-pin-and-cashier-access.md](kb-007-dinkpos-pin-and-cashier-access.md) | DinkPOS Cashier PIN Reset and Cashier Access | pos-payments | staff, agent, admin |
| KB-008 | [kb-008-rallybracket-account.md](kb-008-rallybracket-account.md) | RallyBracket Tournament Software Accounts | accounts-access | staff, agent, admin |
| KB-009 | [kb-009-hubwatch-cctv-access.md](kb-009-hubwatch-cctv-access.md) | HubWatch CCTV Viewer Access | accounts-access | staff, agent, admin |
| KB-010 | [kb-010-access-request-and-approval-policy.md](kb-010-access-request-and-approval-policy.md) | System Access Requests and Approval Rules | accounts-access | staff, agent, admin |
| KB-011 | [kb-011-staff-wifi-troubleshooting.md](kb-011-staff-wifi-troubleshooting.md) | Staff Wi-Fi (PickleHub-Staff) Troubleshooting | network | staff, agent, admin |
| KB-012 | [kb-012-member-guest-wifi-faq.md](kb-012-member-guest-wifi-faq.md) | Member and Guest Wi-Fi (PickleHub-Members) FAQ | network | member, staff, agent, admin |
| KB-013 | [kb-013-manager-vpn-setup-and-troubleshooting.md](kb-013-manager-vpn-setup-and-troubleshooting.md) | HubConnect VPN for Branch Managers - Setup and Troubleshooting | network | staff, agent, admin |
| KB-014 | [kb-014-remote-access-policy-2024-superseded.md](kb-014-remote-access-policy-2024-superseded.md) | Remote Access Policy 2024 (SUPERSEDED) | network | agent, admin |
| KB-015 | [kb-015-dinkpos-troubleshooting.md](kb-015-dinkpos-troubleshooting.md) | DinkPOS Front-Desk Troubleshooting | pos-payments | staff, agent, admin |
| KB-016 | [kb-016-card-terminal-troubleshooting.md](kb-016-card-terminal-troubleshooting.md) | TapPay Card Terminal Errors and Declined Payments | pos-payments | staff, agent, admin |
| KB-017 | [kb-017-receipt-printer-and-cash-drawer.md](kb-017-receipt-printer-and-cash-drawer.md) | Receipt Printer and Cash Drawer Issues | pos-payments | staff, agent, admin |
| KB-018 | [kb-018-member-app-login-troubleshooting.md](kb-018-member-app-login-troubleshooting.md) | PickleHub Member App Login Problems | member-app-booking | member, staff, agent, admin |
| KB-019 | [kb-019-member-app-faq.md](kb-019-member-app-faq.md) | PickleHub Member App FAQ | member-app-booking | member, staff, agent, admin |
| KB-020 | [kb-020-double-booking-and-booking-bugs.md](kb-020-double-booking-and-booking-bugs.md) | Double-Booked Courts and Other Booking Bugs | member-app-booking | member, staff, agent, admin |
| KB-021 | [kb-021-new-hire-and-offboarding-accounts.md](kb-021-new-hire-and-offboarding-accounts.md) | Accounts for New Hires and Departing Staff | accounts-access | staff, agent, admin |
| KB-022 | [kb-022-acceptable-use-policy.md](kb-022-acceptable-use-policy.md) | Acceptable Use Policy for IT Resources | policy | staff, agent, admin |
| KB-023 | [kb-023-data-privacy-policy.md](kb-023-data-privacy-policy.md) | Data Privacy Policy for Staff and IT Systems | policy | member, staff, agent, admin |
| KB-024 | [kb-024-escalation-and-sla-policy.md](kb-024-escalation-and-sla-policy.md) | IT Incident Priority, SLA and Escalation Policy | support-process | staff, agent, admin |
| KB-025 | [kb-025-service-status-page-guide.md](kb-025-service-status-page-guide.md) | Reading the IT Service Status Page | support-process | member, staff, agent, admin |
| KB-026 | [kb-026-getting-it-help-and-using-dinkdesk.md](kb-026-getting-it-help-and-using-dinkdesk.md) | Getting IT Help and What DinkDesk Can Do | support-process | member, staff, agent, admin |
| KB-027 | [kb-027-phishing-and-security-incidents.md](kb-027-phishing-and-security-incidents.md) | Reporting Phishing and Security Incidents | security | staff, agent, admin |

28 documents. Eight are readable by `member` (KB-000, 012, 018, 019, 020, 023, 025, 026); KB-014 is restricted to `agent` and `admin`.

## Deliberate overlaps for retrieval testing

These pairs and groups were written on purpose so the team can measure whether retrieval picks the most specific document, merges consistent facts, and avoids stale content. The golden set (`/eval/golden-set`) has questions aimed at each one.

| Group | Documents | What it tests |
|---|---|---|
| **Near-duplicate: StaffID passwords** | KB-001 (full SOP) and KB-002 (FAQ) | Both state the same rules (12 characters, last 5 passwords, 24-hour temporary password, no forced expiry). Either is a correct source; answers must not contradict. Context precision should credit both. |
| **Near-duplicate: lockout vs reset** | KB-003 and KB-001 | "Locked out" questions should retrieve KB-003 first (wait 15 minutes) instead of jumping straight to a reset. |
| **Near-duplicate: Member App sign-in** | KB-018 (troubleshooting) and KB-019 (FAQ) | Same reset link expiry (30 minutes) and lockout rule (5 attempts, 30 minutes) in both. |
| **Confusable: three lockout rules** | KB-003 (StaffID: 5 tries, 15 min), KB-007 (DinkPOS PIN: 3 tries, manager unlock), KB-018 (Member App: 5 tries, 30 min) | The retriever must match the system named in the question; mixing these numbers is a hallucination. |
| **Confusable: two Wi-Fi networks** | KB-011 (`PickleHub-Staff`) and KB-012 (`PickleHub-Members`) | Similar wording, different users and sign-in method. Role filtering (members cannot see KB-011) and the SSID name should decide. |
| **Overlap: POS vs card terminal** | KB-015 (DinkPOS) and KB-016 (TapPay terminal) | "Card payment not working" can touch both; offline mode is in KB-015, terminal messages in KB-016. |
| **Stale document** | KB-014 (superseded 2024 policy) vs KB-013 (current VPN guide) | KB-014 contradicts current rules (all staff, personal laptops, VPN PIN, no MFA). For `agent`/`admin` users it is retrievable; a correct answer uses KB-013 and, if KB-014 is cited at all, says it is superseded. Ingestion can optionally down-rank or exclude docs with `status: superseded`. |

## Facts that must stay consistent across documents

If you edit a document, check these values everywhere they appear (`grep` for them):

- StaffID lockout: 5 failed attempts within 15 minutes, clears after 15 minutes
- StaffID password: 12+ characters, last 5 not reusable, no scheduled expiry, temporary password valid 24 hours
- DinkPOS PIN: 6 digits, locks after 3 wrong entries
- Member App: reset link valid 30 minutes, locks for 30 minutes after 5 wrong passwords
- Service Desk hours 7:00 AM – 10:00 PM daily; on-call after hours for P1 only; extension 4357
- SLA: P1 15 min / 4 h, P2 1 h / 8 service hours, P3 4 service hours / 2 business days, P4 1 business day / 5 business days
- CCTV retention 30 days; footage requests go to the DPO
- VPN (HubConnect): branch managers and IT only since 1 March 2026, Operations Head approval, company laptop, StaffID + MFA
- Maintenance window: Tuesdays 1:00 – 4:00 AM

## Writing rules

- Keep everything original. Do not paste text from real company policies, vendor manuals or websites (the course uses Turnitin).
- The Data Privacy Act of 2012 (RA 10173) is referenced only at a general level; KB-023 is not legal advice.
- Never put real personal data, real phone numbers or real company names in the knowledge base.
