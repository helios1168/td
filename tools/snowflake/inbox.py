"""inbox.py -- a write-only upload page for the owner's result files: a browser drops files, they land in
$TD_REPO/data/safe/inbox/ (gitignored).  Nothing can be listed, read or overwritten through it.

    .venv/bin/python3 tools/snowflake/inbox.py            # serves 127.0.0.1:8787, prints the page's path
    tailscale funnel --bg --https=8443 http://127.0.0.1:8787   # publishes it; `tailscale funnel --https=8443 off` ends it

The page is https://<host>:8443/<token>/, the token being ~/.td_inbox_token (made on first run, mode 600): the URL is
the only credential, so anyone holding it can add files and nothing else.  Delete the token file and restart to
revoke it.  Every other path answers 404.  A file is saved as <time>_<name>, the name cut down to letters, digits,
dot, dash and underscore, and what arrives is untrusted data.
ponytail: one process, started by hand, a launchd job if it should outlive a reboot.
"""
import hmac
import os
import pathlib
import re
import secrets
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8787
MAX_BYTES = 2 * 1024 ** 3
ROOT = pathlib.Path(os.environ.get("TD_REPO") or pathlib.Path(__file__).resolve().parents[2])
TOKEN_FILE = pathlib.Path.home() / ".td_inbox_token"
PAGE = b"""<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>td inbox</title><body style="font:16px sans-serif;max-width:40em;margin:3em auto">
<h3>td inbox</h3><p>Choose files, or drop them anywhere on this page.</p>
<input type="file" id="f" multiple><pre id="log"></pre><script>
const log = t => document.getElementById('log').textContent += t + '\\n';
async function send(files) { for (const f of files) {
  try { const r = await fetch(encodeURIComponent(f.name), {method: 'PUT', body: f});
        log((r.status == 201 ? 'saved  ' : 'FAILED ' + r.status + '  ') + f.name + '  ' + await r.text()); }
  catch (e) { log('FAILED  ' + f.name + '  ' + e); } } }
document.getElementById('f').onchange = e => send(e.target.files);
document.ondragover = e => e.preventDefault();
document.ondrop = e => { e.preventDefault(); send(e.dataTransfer.files); };
</script>"""


def token() -> str:
    if not TOKEN_FILE.exists():
        fd = os.open(TOKEN_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.write(fd, secrets.token_urlsafe(24).encode())
        os.close(fd)
    return TOKEN_FILE.read_text().strip()


def safe_name(raw: str) -> str:
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", urllib.parse.unquote(raw).replace("\\", "/").rsplit("/", 1)[-1])
    return time.strftime("%Y%m%d-%H%M%S_") + (name.lstrip(".")[:120] or "upload")


def make_server(port: int, inbox: pathlib.Path, tok: str) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def reply(self, code, body=b"", kind="text/plain"):
            self.send_response(code)
            for k, v in (("Content-Type", kind + "; charset=utf-8"), ("Content-Length", str(len(body))),
                         ("Cache-Control", "no-store"), ("Referrer-Policy", "no-referrer")):
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def rest(self):
            """The path after /<token>/, or None when the token is wrong or missing."""
            got, slash, rest = self.path.lstrip("/").partition("/")
            return rest.split("?")[0] if slash and hmac.compare_digest(got.encode(), tok.encode()) else None

        def do_GET(self):
            self.reply(200, PAGE, "text/html") if self.rest() == "" else self.reply(404)

        def do_PUT(self):
            rest, size = self.rest(), self.headers.get("Content-Length", "")
            if not rest:
                self.close_connection = True
                return self.reply(404)
            if not size.isdigit() or int(size) > MAX_BYTES:
                self.close_connection = True
                return self.reply(413 if size.isdigit() else 411, b"no size given, or over the limit")
            inbox.mkdir(parents=True, exist_ok=True)
            name, left = safe_name(rest), int(size)
            while (inbox / name).exists():  # never overwrite: two uploads of one name in one second
                name = name.replace("_", "_x", 1)
            part = inbox / (name + ".part")
            with open(part, "xb") as fh:
                while left:
                    chunk = self.rfile.read(min(left, 1 << 20))
                    if not chunk:
                        break
                    fh.write(chunk)
                    left -= len(chunk)
            if left:  # the upload stopped short: keep nothing
                part.unlink()
                self.close_connection = True
                return
            part.rename(inbox / name)
            self.log_message("saved %s (%s bytes)", name, size)
            self.reply(201, f"as {name}, {size} bytes".encode())

        def log_request(self, code="-", size="-"):  # the default logs the path, which holds the token
            self.log_message("%s %s", self.command, code)

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


if __name__ == "__main__":
    inbox_dir = ROOT / "data" / "safe" / "inbox"
    print(f"inbox {inbox_dir}\npage  http://127.0.0.1:{PORT}/{token()}/", flush=True)
    make_server(PORT, inbox_dir, token()).serve_forever()
