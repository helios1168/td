"""tools/snowflake/inbox.py on a local port: the right token saves a file, nothing else does, and a name cannot
leave the inbox or overwrite a file."""
import http.client
import importlib.util
import pathlib
import tempfile
import threading

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("inbox", ROOT / "tools" / "snowflake" / "inbox.py")
inbox = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(inbox)


def _call(port, method, path, body=None, headers=None):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    c.request(method, path, body=body, headers=headers or {})
    r = c.getresponse()
    out = (r.status, r.read())
    c.close()
    return out


def test_only_the_token_path_saves_and_names_stay_inside():
    with tempfile.TemporaryDirectory() as d:
        box = pathlib.Path(d) / "inbox"
        srv = inbox.make_server(0, box, "tok")
        port = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            assert _call(port, "GET", "/tok/")[0] == 200
            for path in ("/", "/wrong/", "/tok", "/tok/x", "/to/"):
                assert _call(port, "GET", path) == (404, b""), path
            assert _call(port, "PUT", "/wrong/a.csv", b"x")[0] == 404
            assert _call(port, "PUT", "/tok/", b"x")[0] == 404
            assert not box.exists(), "a refused request made the inbox"
            assert _call(port, "PUT", "/tok/a%20b.csv", b"one")[0] == 201
            assert _call(port, "PUT", "/tok/a%20b.csv", b"two")[0] == 201  # same name: a second file, not an overwrite
            assert _call(port, "PUT", "/tok/..%2F..%2F.evil%5Cx.sh", b"three")[0] == 201
            assert _call(port, "PUT", "/tok/big", headers={"Content-Length": str(inbox.MAX_BYTES + 1)})[0] == 413
            files = sorted(p for p in pathlib.Path(d).rglob("*") if p.is_file())
            assert all(p.parent == box for p in files), files
            assert sorted(p.read_bytes() for p in files) == [b"one", b"three", b"two"]
            assert sorted(p.name.split("_")[-1] for p in files) == ["b.csv", "b.csv", "x.sh"]
        finally:
            srv.shutdown()
            srv.server_close()
