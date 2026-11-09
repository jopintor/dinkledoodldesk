# Installing Docker Desktop + WSL 2 on the demo PC (Jose)

The demo host is Jose's Windows 11 Pro PC (32 GB RAM). This needs an **administrator account and one or two
reboots**, so only Jose can do it. Budget about 45 minutes, most of it downloads.

> Docker Desktop is free for personal use, education and non-commercial projects, which covers this capstone.
> You can skip signing in to a Docker account.

## Part A — Install

### 1. Check that virtualisation is on

1. Press `Ctrl+Shift+Esc` to open Task Manager → **Performance** → **CPU**.
2. Under the graph, **Virtualization** must say **Enabled**.
3. If it says Disabled: reboot into the BIOS/UEFI (usually `Del` or `F2` while booting) and enable
   **Intel VT-x / Intel Virtualization Technology** or **AMD SVM / AMD-V**. Save and reboot.

### 2. Install WSL 2

1. Right-click **Start** → **Terminal (Admin)** (or "Windows PowerShell (Admin)"). Click **Yes** on the prompt.
2. Run:
   ```powershell
   wsl --install --no-distribution
   ```
   This turns on the *Virtual Machine Platform* and *Windows Subsystem for Linux* features. Docker does not need
   an Ubuntu distribution, so `--no-distribution` skips it.
3. **Reboot.**
4. Open the admin terminal again and run:
   ```powershell
   wsl --update
   wsl --set-default-version 2
   wsl --status
   ```
   `wsl --status` should show **Default Version: 2**.

### 3. Limit how much RAM Docker may use (recommended)

WSL 2 can take up to half the PC's memory. The whole DinkDesk stack needs under 3 GB, so cap it at 8 GB to keep
the PC responsive during the demo (screen recording, browser, slides).

1. Press `Win+R`, type `notepad %UserProfile%\.wslconfig`, press Enter, and create the file if asked.
2. Paste and save:
   ```ini
   [wsl2]
   memory=8GB
   processors=4
   ```
3. In a terminal: `wsl --shutdown` (applies the limit next time Docker starts).

### 4. Install Docker Desktop

Either download **Docker Desktop for Windows (AMD64)** from <https://www.docker.com/products/docker-desktop/> and
run the installer, or in the admin terminal:

```powershell
winget install -e --id Docker.DockerDesktop
```

In the installer:

- Keep **Use WSL 2 instead of Hyper-V (recommended)** ticked.
- Leave "Add shortcut to desktop" as you like.
- Click **Close and log out** (or **Close and restart**) at the end. Logging out is required: it adds you to the
  `docker-users` group.

If your daily Windows account is **not** the admin account, add it to the group from the admin terminal, then
log out and back in:

```powershell
net localgroup docker-users "<your-windows-username>" /add
```

### 5. First start

1. Start **Docker Desktop** from the Start menu.
2. Accept the Docker Subscription Service Agreement. Skip the sign-in and the survey.
3. Wait until the bottom-left corner shows **Engine running** (green).
4. Settings (gear icon) → **General**: tick **Start Docker Desktop when you sign in** (handy on demo day).
   Settings → **Resources → WSL integration** can stay as it is.

### 6. Install cloudflared (for the tunnels)

```powershell
winget install --id Cloudflare.cloudflared
```

Close and reopen the terminal so `cloudflared` is on the PATH. No Cloudflare account is needed for quick tunnels.

### 7. Get the project ready

In a normal (non-admin) terminal, from the repo folder:

```powershell
git switch main
git pull
Copy-Item .env.example .env      # skip if you already have a .env
notepad .env                      # set GEMINI_API_KEY (and change the change-me values)
```

## Part B — Verify (checklist)

Tick these off in order. If one fails, see *Troubleshooting* below.

- [ ] `docker version` shows both a **Client** and a **Server** section.
- [ ] `docker compose version` prints v2.x.
- [ ] `docker run --rm hello-world` prints "Hello from Docker!".
- [ ] `wsl --status` shows Default Version 2.
- [ ] `cloudflared --version` prints a version.
- [ ] Local stack starts (no tunnels yet), first run takes 5–10 minutes:
      ```powershell
      powershell -ExecutionPolicy Bypass -File infra\scripts\demo-up.ps1 -NoTunnel
      ```
      It ends with a green list of URLs.
- [ ] Health checks pass:
      ```powershell
      powershell -ExecutionPolicy Bypass -File infra\scripts\verify-stack.ps1
      ```
      Every line is `[ OK ]`, including **OTP for demo.staff reaches Mailpit**.
- [ ] <http://localhost:8000/docs> shows the DinkDesk Swagger UI.
- [ ] <http://localhost:8025> (Mailpit) shows an "SMS to +…0021" message from the check above.
- [ ] <http://localhost:5678> opens n8n's owner-setup page (create the owner account once).
- [ ] <http://localhost:3000> shows the DinkDesk frontend.
- [ ] Docker Desktop → **Containers** shows `dinkdesk` with postgres, chromadb, n8n, backend, frontend,
      mock-directory and mailpit all running.
- [ ] Task Manager → Memory: the `VmmemWSL` process stays under the `.wslconfig` limit.
- [ ] Tunnels work: run `demo-up.ps1` **without** `-NoTunnel`, then open the printed backend URL + `/health` on
      your phone (mobile data, not Wi-Fi). It returns `{"status":"ok",…}`.
- [ ] `powershell -ExecutionPolicy Bypass -File infra\scripts\demo-down.ps1` closes the tunnels
      (the backend URL stops working).
- [ ] Reboot the PC, start Docker Desktop, run `demo-up.ps1 -NoTunnel` again: the containers come back with their
      data (n8n owner account still exists).

When all boxes are ticked, update `PROGRESS.md` (T1 / Docker) and tell Andre and Arjan the stack is live.

## Troubleshooting

| Symptom | Fix |
|---|---|
| "WSL 2 installation is incomplete" / "WSL needs updating" | Admin terminal: `wsl --update`, then restart Docker Desktop. |
| "Virtual Machine Platform is not enabled" | Admin terminal: `dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart`, reboot. |
| Docker Desktop stuck on "Engine starting" | Tray icon → **Restart**. Still stuck: `wsl --shutdown`, start Docker Desktop again. |
| `permission denied ... docker_engine` | Your account is not in `docker-users`: see step 4, then log out and in. |
| `port is already allocated` (5432, 8000, 3000, …) | Another program uses the port (often a local PostgreSQL or another dev server). Stop it, or find it with `netstat -ano \| findstr :5432` and end that PID in Task Manager. |
| A container is `unhealthy` | `docker compose -f infra/docker-compose.yml logs <service>` and read the last lines. |
| Backend `/health` OK but ingestion fails | `GEMINI_API_KEY` missing or wrong in `.env`, or the free-tier quota is used up. Re-run later with `demo-up.ps1 -NoTunnel` (unchanged documents are skipped). |
| Arjan's browser shows a CORS error | Use the URLs from the latest `demo-up.ps1` run: tunnel URLs change every run, and the script adds the new frontend URL to `CORS_ORIGINS`. Arjan's own `npm run dev` on `localhost:3000` is always allowed. |
| `cloudflared` not found right after installing | Open a new terminal (PATH is read at start). |
| `running scripts is disabled on this system` | Run scripts as shown, with `powershell -ExecutionPolicy Bypass -File …`. |
