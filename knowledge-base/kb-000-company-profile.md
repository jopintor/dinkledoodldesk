---
id: KB-000
title: PickleHub Clubs Company Profile and IT Overview
category: company
audience_roles: [member, staff, agent, admin]
last_updated: 2026-10-20
owner: IT Lead
---

# PickleHub Clubs Company Profile and IT Overview

> PickleHub Clubs, Inc. is a fictional company created for the DinkDesk capstone project. All names, addresses, numbers and email domains in this knowledge base are made up.

## About PickleHub Clubs

PickleHub Clubs, Inc. runs a chain of pickleball clubs in the province of Cavite, Philippines. The company opened its first club in 2022. It now has five branches, about 140 employees (front desk, coaches, café and pro-shop crew, branch managers and head-office staff) and roughly 6,500 active members.

Members book courts, join open-play sessions, enrol in clinics and sign up for tournaments through the PickleHub Member App. Staff run the clubs using a set of business systems that the IT team supports.

## Branches

| Code | Branch | Courts | Club hours |
|---|---|---|---|
| DAS | PickleHub Dasmariñas (flagship, also hosts the head office) | 10 indoor | 6:00 AM – 11:00 PM daily |
| IMS | PickleHub Imus | 6 indoor | 6:00 AM – 11:00 PM daily |
| BAC | PickleHub Bacoor | 8 indoor | 6:00 AM – 11:00 PM daily |
| GTR | PickleHub General Trias | 4 indoor, 2 covered outdoor | 6:00 AM – 11:00 PM daily |
| TAG | PickleHub Tagaytay | 8 covered open-air | 6:00 AM – 9:00 PM daily |

All times in this knowledge base are Philippine Time (PHT, UTC+8).

## Systems in use

| System | What it does | Who uses it | How you sign in |
|---|---|---|---|
| StaffID | Central staff account (directory and single sign-on) | All employees | Username `firstname.lastname`, password and MFA |
| HubMail | Staff email and calendar (Google Workspace) | All employees | StaffID |
| CourtBook Admin | Web portal for court schedules, bookings, clinics and member check-in | Front desk, coaches, managers | StaffID |
| PickleHub Member App | Mobile app and member website for bookings, payments and membership | Members | Member email and password (separate from StaffID) |
| DinkPOS | Point-of-sale on front-desk tablets for court fees, pro shop and café | Front desk, café crew, managers | Cashier ID and 6-digit PIN |
| TapPay card terminals | Countertop card and contactless terminals supplied by the acquiring bank | Front desk | No login; linked to DinkPOS |
| RallyBracket | Cloud tournament bracket, scheduling and scoring software | Events team, coaches | Separate RallyBracket account (not StaffID) |
| HubWatch | CCTV viewer for each branch's video recorder | Authorized managers and security only | Separate HubWatch account |
| HubConnect VPN | Remote access to head-office systems | Branch managers and IT only | StaffID and MFA |
| Club Wi-Fi | `PickleHub-Staff`, `PickleHub-Members`, and the hidden `PickleHub-Devices` network | Staff, members, devices | Depends on network |
| DinkDesk | AI IT helpdesk (chat) | Everyone | Your StaffID or member account |
| IT Help (Jira Service Management, project key `ITH`) | IT ticketing system | IT agents (everyone can raise tickets through DinkDesk or email) | StaffID |
| Status page | Live health of the systems above | Everyone | `status.picklehub.example`, no login needed |

## DinkDesk user roles

DinkDesk shows different answers and actions depending on your role.

| Role | Who | What DinkDesk can do for them |
|---|---|---|
| `member` | Club members using the Member App | Answer member app, booking and member Wi-Fi questions; create a ticket for member app bugs |
| `staff` | All employees, including coaches and branch managers | Everything a member gets, plus staff system guides, StaffID password reset after identity checks, access request tickets |
| `agent` | IT Service Desk agents | Staff features plus internal troubleshooting notes and ticket triage |
| `admin` | IT Lead and system administrators | All of the above plus DinkDesk settings, analytics and audit logs |

A branch manager is a `staff` user whose job title is Branch Manager. Some guides (for example the VPN and CCTV guides) apply only to managers.

## The IT team

| Name | Position | Main areas | Support level |
|---|---|---|---|
| Ramon Villareal | IT Lead | IT strategy, vendor contracts, approvals for admin rights, major incidents | L3 |
| Lea Bautista | Systems and Network Administrator | Wi-Fi, VPN, CCTV recorders, StaffID directory | L2 |
| Noel Santos | Applications Specialist | CourtBook, DinkPOS, Member App, RallyBracket (vendor liaison) | L2 |
| Kat Mendoza | Service Desk Agent (day shift, 7:00 AM – 3:00 PM) | First-line support and tickets | L1 |
| Paolo Reyes | Service Desk Agent (evening shift, 2:00 PM – 10:00 PM) | First-line support and tickets | L1 |

Other people you may be referred to:

- **Grace Lim, Operations Head** — approves VPN and CCTV access and is the management escalation point above the IT Lead.
- **Atty. Celine Navarro, Data Protection Officer (DPO)** — handles privacy questions, data subject requests, CCTV footage requests and personal data breaches.
- **Bea Castillo, Events Coordinator** — approves RallyBracket access.

## Support hours and contacts

| Channel | Hours | Use it for |
|---|---|---|
| DinkDesk chat | 24/7 | Questions, self-service fixes, StaffID password resets, raising tickets |
| IT Service Desk (email `it-help@picklehub.example`, branch phone extension 4357) | 7:00 AM – 10:00 PM daily | Anything DinkDesk cannot solve |
| After-hours on-call engineer, mobile +63 900 000 4357 (fictional) | 10:00 PM – 7:00 AM | P1 critical incidents only (for example, all card payments down at an open branch) |
| Security reports, `security@picklehub.example` | Monitored daily | Phishing, suspicious logins, lost devices |
| Data Protection Officer, `dpo@picklehub.example` | Office hours, Mon–Fri 8:00 AM – 5:00 PM | Privacy concerns, data requests, breaches |

The Service Desk is open every day, including holidays, except reduced coverage on 25 December and 1 January (P1 on-call only).

See KB-024 for priority levels, response targets and the escalation path.
