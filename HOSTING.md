# Host this equipment list (local Mac, NAS, or another computer)

This folder is a **static website**. There is no database or Node server—any device that can serve files over HTTP works.

## Files the live site needs

| Required | Purpose |
|----------|---------|
| `index.html`, `app.js`, `styles.css`, `data.json` | Main list |
| `images/` (all `eq-*.jpg`) | Hover photos |
| `admin.html`, `admin.js`, `admin.css` | Optional in-browser editor |

Python scripts (`sync_eq_photos.py`, etc.) are only for **your** Mac when you update photos or rebuild from PDF—they do not run on the NAS.

---

## On this Mac or any Mac (quick preview)

1. Open **Terminal** (or **Cursor → Terminal**).
2. Go to this folder and run:

   ```bash
   cd /path/to/photo-kit-equipment-site
   chmod +x serve-site.sh
   ./serve-site.sh
   ```

3. In a browser: **http://127.0.0.1:9000/**

Another port if 9000 is busy:

```bash
PORT=8765 ./serve-site.sh
```

---

## In Cursor on another computer

1. **File → Open Folder…** and choose the **`photo-kit-equipment-site`** folder (the unzipped copy).
2. **Terminal → Run Task…** (or `Cmd+Shift+B` if bound) → run **Host equipment site (local)**.
3. Open **http://127.0.0.1:9000/** in the browser.

The task runs the same `serve-site.sh` script.

---

## On your NAS (static hosting)

1. Copy **this entire folder** onto the NAS (SMB/AFP/Finder drag, Synology File Station, etc.).
2. Point your NAS **web / Web Station / virtual host** “document root” at the folder that contains **`index.html`** (not a parent that hides it).
3. Visit `http://nas-hostname/` or the hostname you configured.

**After editing in `admin.html`:** download `data.json` from the editor and **replace** the file in this folder on the NAS, then refresh the page.

**Photos:** run `sync_eq_photos.py` on a Mac, then copy the updated **`images/`** folder to the NAS again.

---

## Move the site to another Mac

- Copy the folder, or use the **`photo-kit-equipment-site-for-NAS.zip`** in **Documents** (if present).
- Unzip, then `./serve-site.sh` or deploy the folder to the NAS as above.

---

## Troubleshooting

- **“Can’t connect to 127.0.0.1:9000”** — the server is not running. Start `./serve-site.sh` and leave Terminal open.
- **`fetch` / blank list** — you must use `http://127.0.0.1:…`, not `file:///…` for `index.html`.
- **Python missing** — install from python.org or use `python3` from Xcode CLT on macOS.
