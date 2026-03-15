import json
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

# ── CONFIG ────────────────────────────────────────────────────────────────────
PORT       = 8080
PARCEL_FILE = os.path.join(os.path.dirname(__file__), "parcels.json")
HTML_FILE   = os.path.join(os.path.dirname(__file__), "index.html")

# Map bot status text → website status key + label
STATUS_MAP = {
    "order received":        ("processing", "Order Received"),
    "processing":            ("processing", "Processing"),
    "picked up":             ("processing", "Picked Up"),
    "collection scheduled":  ("processing", "Collection Scheduled"),
    "dispatched":            ("transit",    "Dispatched"),
    "in transit":            ("transit",    "In Transit"),
    "departed origin":       ("transit",    "Departed Origin"),
    "network dispatch":      ("transit",    "Network Dispatch"),
    "arrived hub":           ("transit",    "Arrived at Hub"),
    "customs clearance":     ("transit",    "Customs Clearance"),
    "out for delivery":      ("out",        "Out for Delivery"),
    "delivered":             ("delivered",  "Delivered"),
}

def get_status(raw: str):
    key = raw.lower().strip()
    for k, v in STATUS_MAP.items():
        if k in key:
            return v
    return ("transit", raw)  # default fallback

def load_parcel(tracking_id: str):
    if not os.path.exists(PARCEL_FILE):
        return None
    with open(PARCEL_FILE, "r") as f:
        data = json.load(f)
    return data.get("parcels", {}).get(tracking_id.upper())

# ── HTTP HANDLER ──────────────────────────────────────────────────────────────
class Handler(SimpleHTTPRequestHandler):

    def log_message(self, format, *args):
        pass  # suppress console spam

    def do_GET(self):
        parsed = urlparse(self.path)

        # ── API: /api/track/<tracking_id> ─────────────────────────────────────
        if parsed.path.startswith("/api/track/"):
            tracking_id = parsed.path.replace("/api/track/", "").upper()
            parcel = load_parcel(tracking_id)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            if not parcel:
                self.wfile.write(json.dumps({"found": False}).encode())
                return

            status_key, status_label = get_status(parcel.get("status", ""))

            # Build timeline from bot history
            history = parcel.get("history", [])
            timeline = []
            for i, h in enumerate(history):
                is_last = (i == len(history) - 1)
                timeline.append({
                    "ev":   h["status"],
                    "loc":  "AU & USA Network",
                    "time": h["date"],
                    "done": not is_last,
                    "active": is_last
                })

            result = {
                "found":    True,
                "id":       tracking_id,
                "customer": parcel.get("customer_name", ""),
                "item":     parcel.get("description", ""),
                "status":   status_key,
                "label":    status_label,
                "timeline": timeline,
                "created":  parcel.get("created", "")
            }
            self.wfile.write(json.dumps(result).encode())
            return

        # ── Serve index.html for root ─────────────────────────────────────────
        if parsed.path in ("/", "/index.html"):
            if os.path.exists(HTML_FILE):
                with open(HTML_FILE, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404, "index.html not found")
            return

        # ── Everything else: 404 ──────────────────────────────────────────────
        self.send_error(404)

# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"🌐 AnonXpress Website running at http://localhost:{PORT}")
    print(f"📡 Tracking API at http://localhost:{PORT}/api/track/<ANX-XXXXXXX>")
    print("   Keep this running alongside bot.py")
    server = HTTPServer(("", PORT), Handler)
    server.serve_forever()
