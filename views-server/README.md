# Profile views counter (self-hosted)

No Cloudflare, no third-party dashboard — a ~150-line Node script you run yourself.
Counts are stored in a JSON file on disk and it draws the same ninja SVG badge as before.

## Run it locally

```bash
node index.js
# -> http://localhost:3000/views/your-github-username
```

## Deploy it anywhere

It's plain Node with **zero dependencies**, so any of these work:

**Option A — your own VPS**
```bash
git clone <this folder onto the server>
npm install --omit=dev   # nothing to install, but keeps the habit
ALLOWED_IDS=your-github-username pm2 start index.js --name views
```
Put it behind Nginx/Caddy with a domain + HTTPS, e.g. `https://views.yourdomain.com`.

**Option B — Docker (on any host: your VPS, a Raspberry Pi, etc.)**
```bash
docker build -t profile-views .
docker run -d -p 3000:3000 -v views-data:/app/data \
  -e ALLOWED_IDS=your-github-username \
  --restart unless-stopped profile-views
```

**Option C — a free Node host (Render, Railway, Fly.io, etc.)**
Push this folder to its own repo (or a subfolder) and point the platform at it.
Just make sure the disk is persistent (a mounted volume) — some free tiers wipe
the filesystem on redeploy, which would reset the counter.

## Environment variables

| Variable      | Default                  | Meaning                                   |
|---------------|---------------------------|--------------------------------------------|
| `PORT`        | `3000`                    | Port to listen on                          |
| `DATA_FILE`   | `./data/views.json`       | Where counts are persisted                 |
| `ALLOWED_IDS` | *(empty = allow any)*     | Comma-separated ids allowed to be counted  |

## Wire it into your README

Once deployed, point the image at your own host instead of the old
`*.workers.dev` URL:

```md
![Profile views](https://views.yourdomain.com/views/your-github-username)
```
