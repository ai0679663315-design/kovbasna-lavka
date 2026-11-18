"""Download product photos from the producer's Telegram channel into img/ (run by GitHub Actions).

For each product in products.js: try the stored CDN URL; if it has expired, re-read the
channel page around the source post to get a fresh URL. Saves img/<id>.jpg (max 900 px)
and writes img/manifest.js so the site uses local copies.
"""
import io, json, re, sys, urllib.request
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0 (kovbasna-lavka image sync)"}
CHANNEL = "Zhadkivski"

def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()

def fresh_photo(post_id, index=0):
    html = get(f"https://t.me/s/{CHANNEL}?before={post_id + 1}").decode("utf-8", "replace")
    blocks = re.split(r'data-post="', html)
    for b in blocks:
        if b.startswith(f"{CHANNEL}/{post_id}\""):
            urls = re.findall(r"tgme_widget_message_photo_wrap[^>]*background-image:url\('([^']+)'\)", b)
            if len(urls) > index:
                return urls[index]
    return None

def main():
    src = (ROOT / "products.js").read_text(encoding="utf-8")
    rows = re.findall(r'\["([\w-]+)","[^"]*","[^"]*",\d+,"[^"]*",\d+,"([^"]*)",(\d+)\]', src)
    out = ROOT / "img"; out.mkdir(exist_ok=True)
    ok, failed = {}, []
    idx_override = {"salo-dymok": 1}
    for pid, token, post in rows:
        if not token:
            continue
        data = None
        for url in [f"https://cdn4.telesco.pe/file/{token}.jpg", None]:
            try:
                if url is None:
                    url = fresh_photo(int(post), idx_override.get(pid, 0))
                    if not url:
                        break
                data = get(url)
                Image.open(io.BytesIO(data)).verify()
                break
            except Exception as e:  # noqa: BLE001
                print(f"{pid}: {e}", file=sys.stderr); data = None
        if not data:
            failed.append(pid); continue
        im = Image.open(io.BytesIO(data)).convert("RGB")
        im.thumbnail((900, 900))
        im.save(out / f"{pid}.jpg", "JPEG", quality=82, optimize=True, progressive=True)
        ok[pid] = True
    (out / "manifest.js").write_text("window.LOCAL_IMG = " + json.dumps(ok) + ";\n", encoding="utf-8")
    print(f"saved {len(ok)} images, failed: {failed}")

if __name__ == "__main__":
    main()
