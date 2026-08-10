"""Find out how veadotube mini's websocket actually behaves.

It advertises its port in ~/.veadotube/instances/<id> (the port changes every
launch, so it has to be read fresh). This probes the state API rather than
trusting documentation: list the avatar's states, then try switching to one.

Run: python tools/probe_veadotube.py            list states
     python tools/probe_veadotube.py <state>    switch to it
"""

import glob
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

INSTANCES = os.path.join(os.path.expanduser("~"), ".veadotube", "instances")


def newest_instance():
    files = glob.glob(os.path.join(INSTANCES, "*"))
    if not files:
        return None
    newest = max(files, key=os.path.getmtime)
    try:
        with open(newest, encoding="utf-8") as f:
            info = json.load(f)
        info["_file"] = newest
        return info
    except (OSError, ValueError):
        return None


def main():
    info = newest_instance()
    if not info:
        print("no instance file — is veadotube mini running?")
        return
    age = time.time() - os.path.getmtime(info["_file"])
    print("instance : %s (v%s)" % (info.get("name"), info.get("version")))
    print("server   : %s   (file %.0fs old)" % (info.get("server"), age))

    import websocket
    url = "ws://%s?n=cardia-probe" % info["server"]
    print("connect  : %s" % url)
    ws = websocket.create_connection(url, timeout=5)

    def send(payload):
        msg = json.dumps({"event": "payload", "type": "stateEvents",
                          "id": "mini", "payload": payload})
        print("  -> %s" % msg)
        ws.send(msg)

    def recv(want_type, tries=6):
        """It greets you with an 'instance' message first, so keep reading
        until the reply we actually asked for turns up."""
        for _ in range(tries):
            try:
                raw = str(ws.recv())
            except Exception as e:
                print("  <- (nothing: %s)" % e)
                return None
            print("  <- %s" % raw[:400])
            brace = raw.find("{")
            if brace < 0:
                continue
            try:
                msg = json.loads(raw[brace:])
            except ValueError:
                continue
            if raw[:brace].startswith(want_type) or msg.get("type") == want_type:
                return msg
        return None

    # The reply arrives as "instance:{json}", so outgoing messages are very
    # likely channel-prefixed too. Try the plausible shapes and see which one
    # the app actually answers.
    print("\n[finding the message format]")
    body = {"event": "payload", "type": "stateEvents", "id": "mini",
            "payload": {"event": "list"}}
    candidates = [
        ("nodes:" + json.dumps(body)),
        ("nodes: " + json.dumps(body)),
        (json.dumps(body)),
        ("stateEvents:" + json.dumps({"event": "list"})),
    ]
    reply = None
    for attempt in candidates:
        print("  -> %s" % attempt[:90])
        try:
            ws.send(attempt)
        except Exception as e:
            print("     send failed: %s" % e)
            break
        got = recv("stateEvents", tries=2)
        if got and ((got.get("payload") or {}).get("states") is not None):
            print("     ^ THIS FORMAT WORKS")
            reply = got
            break
    states = (((reply or {}).get("payload") or {}).get("states")) or []
    for st in states:
        print("     state id=%-4s name=%s" % (st.get("id"), st.get("name")))

    want = sys.argv[1] if len(sys.argv) > 1 else None
    if want and states:
        match = next((s for s in states
                      if str(s.get("id")) == want
                      or str(s.get("name")).lower() == want.lower()), None)
        if not match:
            print("\nno state called %r" % want)
        else:
            print("\n[set state -> %s]" % match.get("name"))
            send({"event": "set", "state": match.get("id")})
            recv("stateEvents", tries=3)
    ws.close()


if __name__ == "__main__":
    main()
