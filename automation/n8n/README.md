# n8n workflows

Exports are committed **without credentials**. Create the credentials in n8n from your local `.env` after importing.

## WF-01 Ticket to Jira (`wf-01-ticket-to-jira.json`)

Prototype version of [docs/automation.md §3](../../docs/automation.md):

```
DinkDesk backend ──POST /webhook/ticket-created──▶ Webhook (Header Auth)
                                                     ▼
                                               Build Jira issue (Code)
                                                     ▼
                                     Jira: create issue in ITH (HTTP Request, Basic Auth, 3 tries)
                                                     ▼
◀──────────────── {"jira_key": "ITH-12"} ───── Respond with Jira key
```

- The backend calls it right after a user confirms a `create_ticket` card (`app/tools/jira_sync.py`) and saves the
  key on the ticket (`jira_sync_status = synced`). If n8n or Jira fails, the reply is `{"jira_key": null}` and the
  ticket stays in DinkDesk with `jira_sync_status = failed`.
- The Jira site, project key and issue type come from the backend's `.env` (`JIRA_BASE_URL`, `JIRA_PROJECT_KEY`,
  `JIRA_ISSUE_TYPE`) inside the payload, so the workflow has no site-specific values.
- Cut for the prototype: the HMAC callback, duplicate check, P1/P2 alert emails and access-request approver emails.

### Set up (once, on the demo PC)

1. Start the stack and open n8n at <http://localhost:5678>.
2. Import `wf-01-ticket-to-jira.json` as a new workflow.
3. Open **Webhook: ticket.created** and create a **Header Auth** credential:
   - Name: `X-DinkDesk-Token`
   - Value: the `N8N_WEBHOOK_TOKEN` value from `.env`
4. Open **Jira: create issue in ITH** and create a **Basic Auth** credential:
   - User: the Atlassian account email (`JIRA_EMAIL`)
   - Password: an API token from <https://id.atlassian.com/manage-profile/security/api-tokens> (`JIRA_API_TOKEN`)
5. Save, then activate the workflow (the production URL `/webhook/ticket-created` only answers while it is active).
6. Check `.env` has `JIRA_BASE_URL=https://dlsud-team-pwyio9lq.atlassian.net`, `JIRA_PROJECT_KEY=ITH` and a
   `JIRA_ISSUE_TYPE` that exists in the ITH project (default `Task`), then restart the backend:
   `docker compose -f infra/docker-compose.yml up -d backend`.

### Test it without the chat

PowerShell, from the repo root (replace the token with `N8N_WEBHOOK_TOKEN` from `.env`):

```powershell
$body = '{"event":"ticket.created","jira":{"base_url":"https://dlsud-team-pwyio9lq.atlassian.net","project_key":"ITH","issue_type":"Task"},"data":{"ticket_number":"DD-TEST01","summary":"WF-01 test","description":"Test from the README","category":"other","affected_system":"other","priority":"P4","club_code":null,"requester":{"display_name":"Test","role":"staff","email":"staff@picklehub.example"},"source":"ai_tool"}}'
Invoke-RestMethod -Method Post -Uri http://localhost:5678/webhook/ticket-created -Headers @{ 'X-DinkDesk-Token' = '<token>' } -ContentType 'application/json' -Body $body
```

Expected: `jira_key` = a new `ITH-…` issue. `jira_key: null` means Jira refused it; open the execution in n8n to see
why (most often a wrong issue type name or API token).

### After changing the workflow

Export it again over this file and check that no token, password or email is inside before committing.
