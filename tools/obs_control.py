"""Talk to OBS over its built-in WebSocket (obs-websocket v5, OBS 28+).

Used at stream shutdown: press "Stop Streaming" properly so Twitch sees a
clean end, THEN close OBS. Killing obs64.exe while live cuts the stream
mid-frame and Twitch treats it as a dropped connection.

Config is read from the portable OBS profile, so the password never lives in
our code. Localhost only.

CLI:  python tools/obs_control.py status | stop | shutdown
"""

import base64
import hashlib
import json
import os
import subprocess
import sys
import time

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WS_CONFIG = os.path.join(KIT, "tools", "obs", "config", "obs-studio",
                         "plugin_config", "obs-websocket", "config.json")


def _load_config():
    with open(WS_CONFIG, encoding="utf-8-sig") as f:
        cfg = json.load(f)
    return cfg.get("server_port", 4455), cfg.get("server_password", ""), \
        bool(cfg.get("auth_required", True))


class ObsClient:
    def __init__(self, timeout=6):
        import websocket
        port, password, auth_required = _load_config()
        self.ws = websocket.create_connection(
            "ws://127.0.0.1:%d" % port, timeout=timeout)
        hello = json.loads(self.ws.recv())          # op 0
        ident = {"op": 1, "d": {"rpcVersion": 1}}
        auth = hello.get("d", {}).get("authentication")
        if auth and auth_required:
            secret = base64.b64encode(hashlib.sha256(
                (password + auth["salt"]).encode()).digest()).decode()
            ident["d"]["authentication"] = base64.b64encode(hashlib.sha256(
                (secret + auth["challenge"]).encode()).digest()).decode()
        self.ws.send(json.dumps(ident))
        self.ws.recv()                              # op 2 Identified
        self._seq = 0

    def request(self, req_type, data=None):
        self._seq += 1
        rid = "r%d" % self._seq
        self.ws.send(json.dumps({"op": 6, "d": {
            "requestType": req_type, "requestId": rid,
            "requestData": data or {}}}))
        for _ in range(20):                         # skip unrelated events
            msg = json.loads(self.ws.recv())
            if msg.get("op") == 7 and msg["d"].get("requestId") == rid:
                return msg["d"]
        return {}

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


def stop_output_and_quit(note=print):
    """Stop streaming/recording cleanly, then close OBS. Returns True if OBS
    is gone afterwards. Never raises — shutdown must not be blocked by it."""
    stopped_something = False
    try:
        client = ObsClient()
    except Exception as e:
        note("obs websocket unavailable (%s) - will just close OBS" % e)
        client = None
    if client:
        try:
            status = client.request("GetStreamStatus").get("responseData", {})
            if status.get("outputActive"):
                client.request("StopStream")
                stopped_something = True
                note("obs: streaming stopped")
            rec = client.request("GetRecordStatus").get("responseData", {})
            if rec.get("outputActive"):
                client.request("StopRecord")
                stopped_something = True
                note("obs: recording stopped")
            if stopped_something:
                time.sleep(3)      # let the encoder flush and Twitch see the end
        except Exception as e:
            note("obs stop failed (%s)" % e)
        finally:
            client.close()
    # Now close OBS itself (graceful first, force as a last resort).
    if os.name != "nt":
        return True
    subprocess.run(["taskkill", "/IM", "obs64.exe"], capture_output=True)
    for _ in range(8):
        time.sleep(1)
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq obs64.exe"],
                             capture_output=True, text=True, errors="replace")
        if "obs64.exe" not in (out.stdout or ""):
            note("obs: closed")
            return True
    subprocess.run(["taskkill", "/F", "/IM", "obs64.exe"], capture_output=True)
    note("obs: force-closed")
    return True


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        c = ObsClient()
        print("stream:", c.request("GetStreamStatus").get("responseData"))
        print("record:", c.request("GetRecordStatus").get("responseData"))
        c.close()
    elif cmd == "stop":
        c = ObsClient()
        print(c.request("StopStream"))
        c.close()
    elif cmd == "shutdown":
        print("ok:", stop_output_and_quit())


if __name__ == "__main__":
    main()
