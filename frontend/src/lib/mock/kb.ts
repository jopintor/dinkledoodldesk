// Generated from the frontmatter in /knowledge-base (28 documents). Chunk counts are the
// number of ##/### sections, which is roughly how ingestion splits them.
import type { KbDocument } from "@/lib/types";

type Row = Pick<KbDocument, "id" | "title" | "category" | "audience_roles" | "last_updated" | "chunk_count" | "status"> & { superseded_by?: string | null };

export const KB_ROWS: Row[] = [
  {
    "id": "KB-000",
    "title": "PickleHub Clubs Company Profile and IT Overview",
    "category": "company",
    "audience_roles": [
      "member",
      "staff",
      "agent",
      "admin"
    ],
    "last_updated": "2026-10-20",
    "chunk_count": 6,
    "status": "active",
    "superseded_by": null
  },
  {
    "id": "KB-001",
    "title": "How to Reset Your StaffID Password",
    "category": "accounts-access",
    "audience_roles": [
      "staff",
      "agent",
      "admin"
    ],
    "last_updated": "2026-09-15",
    "chunk_count": 6,
    "status": "active",
    "superseded_by": null
  },
  {
    "id": "KB-002",
    "title": "Password FAQ for Staff Systems",
    "category": "accounts-access",
    "audience_roles": [
      "staff",
      "agent",
      "admin"
    ],
    "last_updated": "2026-08-02",
    "chunk_count": 10,
    "status": "active",
    "superseded_by": null
  },
  {
    "id": "KB-003",
    "title": "Locked StaffID Account",
    "category": "accounts-access",
    "audience_roles": [
      "staff",
      "agent",
      "admin"
    ],
    "last_updated": "2026-09-15",
    "chunk_count": 6,
    "status": "active",
    "superseded_by": null
  },
  {
    "id": "KB-004",
    "title": "Setting Up MFA and What to Do If You Lose Your Phone",
    "category": "accounts-access",
    "audience_roles": [
      "staff",
      "agent",
      "admin"
    ],
    "last_updated": "2026-07-21",
    "chunk_count": 5,
    "status": "active",
    "superseded_by": null
  },
  {
    "id": "KB-005",
    "title": "HubMail Staff Email Problems",
    "category": "accounts-access",
    "audience_roles": [
      "staff",
      "agent",
      "admin"
    ],
    "last_updated": "2026-06-30",
    "chunk_count": 6,
    "status": "active",
    "superseded_by": null
  },
  {
    "id": "KB-006",
    "title": "CourtBook Admin Portal Access and Login",
    "category": "accounts-access",
    "audience_roles": [
      "staff",
      "agent",
      "admin"
    ],
    "last_updated": "2026-09-02",
    "chunk_count": 6,
    "status": "active",
    "superseded_by": null
  },
  {
    "id": "KB-007",
    "title": "DinkPOS Cashier PIN Reset and Cashier Access",
    "category": "pos-payments",
    "audience_roles": [
      "staff",
      "agent",
      "admin"
    ],
    "last_updated": "2026-08-18",
    "chunk_count": 6,
    "status": "active",
    "superseded_by": null
  },
  {
    "id": "KB-008",
    "title": "RallyBracket Tournament Software Accounts",
    "category": "accounts-access",
    "audience_roles": [
      "staff",
      "agent",
      "admin"
    ],
    "last_updated": "2026-05-27",
    "chunk_count": 5,
    "status": "active",
    "superseded_by": null
  },
  {
    "id": "KB-009",
    "title": "HubWatch CCTV Viewer Access",
    "category": "accounts-access",
    "audience_roles": [
      "staff",
      "agent",
      "admin"
    ],
    "last_updated": "2026-09-10",
    "chunk_count": 7,
    "status": "active",
    "superseded_by": null
  },
  {
    "id": "KB-010",
    "title": "System Access Requests and Approval Rules",
    "category": "accounts-access",
    "audience_roles": [
      "staff",
      "agent",
      "admin"
    ],
    "last_updated": "2026-10-01",
    "chunk_count": 4,
    "status": "active",
    "superseded_by": null
  },
  {
    "id": "KB-011",
    "title": "Staff Wi-Fi (PickleHub-Staff) Troubleshooting",
    "category": "network",
    "audience_roles": [
      "staff",
      "agent",
      "admin"
    ],
    "last_updated": "2026-08-25",
    "chunk_count": 6,
    "status": "active",
    "superseded_by": null
  },
  {
    "id": "KB-012",
    "title": "Member and Guest Wi-Fi (PickleHub-Members) FAQ",
    "category": "network",
    "audience_roles": [
      "member",
      "staff",
      "agent",
      "admin"
    ],
    "last_updated": "2026-07-09",
    "chunk_count": 9,
    "status": "active",
    "superseded_by": null
  },
  {
    "id": "KB-013",
    "title": "HubConnect VPN for Branch Managers - Setup and Troubleshooting",
    "category": "network",
    "audience_roles": [
      "staff",
      "agent",
      "admin"
    ],
    "last_updated": "2026-03-01",
    "chunk_count": 10,
    "status": "active",
    "superseded_by": null
  },
  {
    "id": "KB-014",
    "title": "Remote Access Policy 2024",
    "category": "network",
    "audience_roles": [
      "agent",
      "admin"
    ],
    "last_updated": "2024-08-12",
    "chunk_count": 3,
    "status": "superseded",
    "superseded_by": "KB-013"
  },
  {
    "id": "KB-015",
    "title": "DinkPOS Front-Desk Troubleshooting",
    "category": "pos-payments",
    "audience_roles": [
      "staff",
      "agent",
      "admin"
    ],
    "last_updated": "2026-09-22",
    "chunk_count": 6,
    "status": "active",
    "superseded_by": null
  },
  {
    "id": "KB-016",
    "title": "TapPay Card Terminal Errors and Declined Payments",
    "category": "pos-payments",
    "audience_roles": [
      "staff",
      "agent",
      "admin"
    ],
    "last_updated": "2026-09-22",
    "chunk_count": 6,
    "status": "active",
    "superseded_by": null
  },
  {
    "id": "KB-017",
    "title": "Receipt Printer and Cash Drawer Issues",
    "category": "pos-payments",
    "audience_roles": [
      "staff",
      "agent",
      "admin"
    ],
    "last_updated": "2026-04-14",
    "chunk_count": 6,
    "status": "active",
    "superseded_by": null
  },
  {
    "id": "KB-018",
    "title": "PickleHub Member App Login Problems",
    "category": "member-app-booking",
    "audience_roles": [
      "member",
      "staff",
      "agent",
      "admin"
    ],
    "last_updated": "2026-10-05",
    "chunk_count": 7,
    "status": "active",
    "superseded_by": null
  },
  {
    "id": "KB-019",
    "title": "PickleHub Member App FAQ",
    "category": "member-app-booking",
    "audience_roles": [
      "member",
      "staff",
      "agent",
      "admin"
    ],
    "last_updated": "2026-08-11",
    "chunk_count": 10,
    "status": "active",
    "superseded_by": null
  },
  {
    "id": "KB-020",
    "title": "Double-Booked Courts and Other Booking Bugs",
    "category": "member-app-booking",
    "audience_roles": [
      "member",
      "staff",
      "agent",
      "admin"
    ],
    "last_updated": "2026-10-12",
    "chunk_count": 7,
    "status": "active",
    "superseded_by": null
  },
  {
    "id": "KB-021",
    "title": "Accounts for New Hires and Departing Staff",
    "category": "accounts-access",
    "audience_roles": [
      "staff",
      "agent",
      "admin"
    ],
    "last_updated": "2026-06-08",
    "chunk_count": 9,
    "status": "active",
    "superseded_by": null
  },
  {
    "id": "KB-022",
    "title": "Acceptable Use Policy for IT Resources",
    "category": "policy",
    "audience_roles": [
      "staff",
      "agent",
      "admin"
    ],
    "last_updated": "2026-01-15",
    "chunk_count": 8,
    "status": "active",
    "superseded_by": null
  },
  {
    "id": "KB-023",
    "title": "Data Privacy Policy for Staff and IT Systems",
    "category": "policy",
    "audience_roles": [
      "member",
      "staff",
      "agent",
      "admin"
    ],
    "last_updated": "2026-05-04",
    "chunk_count": 8,
    "status": "active",
    "superseded_by": null
  },
  {
    "id": "KB-024",
    "title": "IT Incident Priority, SLA and Escalation Policy",
    "category": "support-process",
    "audience_roles": [
      "staff",
      "agent",
      "admin"
    ],
    "last_updated": "2026-09-30",
    "chunk_count": 6,
    "status": "active",
    "superseded_by": null
  },
  {
    "id": "KB-025",
    "title": "Reading the IT Service Status Page",
    "category": "support-process",
    "audience_roles": [
      "member",
      "staff",
      "agent",
      "admin"
    ],
    "last_updated": "2026-09-05",
    "chunk_count": 6,
    "status": "active",
    "superseded_by": null
  },
  {
    "id": "KB-026",
    "title": "Getting IT Help and What DinkDesk Can Do",
    "category": "support-process",
    "audience_roles": [
      "member",
      "staff",
      "agent",
      "admin"
    ],
    "last_updated": "2026-10-22",
    "chunk_count": 6,
    "status": "active",
    "superseded_by": null
  },
  {
    "id": "KB-027",
    "title": "Reporting Phishing and Security Incidents",
    "category": "security",
    "audience_roles": [
      "staff",
      "agent",
      "admin"
    ],
    "last_updated": "2026-07-30",
    "chunk_count": 6,
    "status": "active",
    "superseded_by": null
  }
];
