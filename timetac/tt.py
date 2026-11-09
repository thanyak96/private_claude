#!/usr/bin/env python3
"""tt - minimal TimeTac time-tracking CLI (TimeTac REST API v3, stdlib only).

Commands:
  tt me                 show the logged-in user
  tt tasks [FILTER]     list tasks (optional case-insensitive name filter)
  tt start TASK         start tracking on a task (task id or unique name part)
  tt stop               stop the running time tracking
  tt status             show the running time tracking, if any
  tt today              list today's time trackings with a total

Configuration (environment variables):
  TIMETAC_ACCOUNT       account name, as in https://go.timetac.com/<account>  (default: cadsgmbh)
  TIMETAC_TOKEN         OAuth2 access token                                    (option A)
  TIMETAC_CLIENT_ID     OAuth2 client id                                       (option B)
  TIMETAC_CLIENT_SECRET OAuth2 client secret                                   (option B)
  TIMETAC_USERNAME      TimeTac login                                          (option B)
  TIMETAC_PASSWORD      TimeTac password                                       (option B)
  TIMETAC_API_BASE      override, default https://api.timetac.com/<account>/userapi/v3
  TIMETAC_TOKEN_URL     override, default https://api.timetac.com/<account>/auth/oauth2/token
"""
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


class TimeTacError(Exception):
    pass


def env(name, default=None, required=False):
    value = os.environ.get(name, default)
    if required and not value:
        raise TimeTacError(f"environment variable {name} is not set")
    return value


class TimeTac:
    def __init__(self):
        self.account = env("TIMETAC_ACCOUNT", "cadsgmbh")
        self.base = env("TIMETAC_API_BASE", f"https://api.timetac.com/{self.account}/userapi/v3").rstrip("/")
        self.token = env("TIMETAC_TOKEN") or self._password_grant()
        self._me = None

    def _password_grant(self):
        url = env("TIMETAC_TOKEN_URL", f"https://api.timetac.com/{self.account}/auth/oauth2/token")
        data = urllib.parse.urlencode({
            "grant_type": "password",
            "client_id": env("TIMETAC_CLIENT_ID", required=True),
            "client_secret": env("TIMETAC_CLIENT_SECRET", required=True),
            "username": env("TIMETAC_USERNAME", required=True),
            "password": env("TIMETAC_PASSWORD", required=True),
        }).encode()
        body = self._send(urllib.request.Request(url, data=data, method="POST"))
        if "access_token" not in body:
            raise TimeTacError(f"no access_token in token response: {body}")
        return body["access_token"]

    @staticmethod
    def _send(req):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            raise TimeTacError(f"HTTP {e.code} {req.full_url}: {e.read().decode(errors='replace')[:500]}")
        except urllib.error.URLError as e:
            raise TimeTacError(f"cannot reach {req.full_url}: {e.reason}")

    def call(self, method, path, params=None, payload=None):
        url = f"{self.base}/{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Accept", "application/json")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        body = self._send(req)
        if isinstance(body, dict) and body.get("Success") is False:
            raise TimeTacError(f"{method} {path} failed: {body.get('ErrorMessage') or body}")
        return body.get("Results", []) if isinstance(body, dict) else body

    def me(self):
        if self._me is None:
            res = self.call("GET", "users/me")
            self._me = res[0] if isinstance(res, list) else res
        return self._me

    def tasks(self):
        return self.call("GET", "tasks/read", {"_limit": 1000})

    def trackings(self, **params):
        return self.call("GET", "timeTrackings/read", {"user_id": self.me()["id"], **params})

    def running(self):
        open_ = [t for t in self.trackings(_limit=50, _sort_desc="start_time") if not t.get("end_time")]
        return open_[0] if open_ else None

    def start(self, task_id):
        return self.call("POST", "timeTrackings/start", payload={"user_id": self.me()["id"], "task_id": task_id})

    def stop(self):
        return self.call("PUT", "timeTrackings/stop", payload={"user_id": self.me()["id"]})


def fmt_duration(seconds):
    seconds = int(seconds or 0)
    return f"{seconds // 3600}:{seconds % 3600 // 60:02d}"


def parse_time(value):
    if not value:
        return None
    return dt.datetime.fromisoformat(str(value).replace(" ", "T").replace("Z", "+00:00"))


def resolve_task(tt, query):
    tasks = tt.tasks()
    if query.isdigit():
        return int(query), next((t.get("name") for t in tasks if str(t.get("id")) == query), query)
    hits = [t for t in tasks if query.lower() in str(t.get("name", "")).lower()]
    exact = [t for t in hits if str(t.get("name", "")).lower() == query.lower()]
    hits = exact or hits
    if len(hits) != 1:
        names = ", ".join(f"{t['id']}={t.get('name')}" for t in hits[:10]) or "none"
        raise TimeTacError(f"'{query}' matches {len(hits)} tasks ({names}); use the task id")
    return hits[0]["id"], hits[0].get("name")


def task_names(tt):
    return {t.get("id"): t.get("name") for t in tt.tasks()}


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    cmd, args = argv[0], argv[1:]
    tt = TimeTac()

    if cmd == "me":
        me = tt.me()
        print(f"{me.get('firstname', '')} {me.get('lastname', '')} (id {me.get('id')})".strip())
    elif cmd == "tasks":
        query = " ".join(args).lower()
        for t in sorted(tt.tasks(), key=lambda t: str(t.get("name", ""))):
            if query in str(t.get("name", "")).lower():
                print(f"{t['id']:>8}  {t.get('name')}")
    elif cmd == "start":
        if not args:
            raise TimeTacError("usage: tt start TASK")
        task_id, name = resolve_task(tt, " ".join(args))
        tt.start(task_id)
        print(f"started: {name} (task {task_id})")
    elif cmd == "stop":
        tt.stop()
        print("stopped")
    elif cmd == "status":
        run = tt.running()
        if not run:
            print("no time tracking running")
        else:
            name = task_names(tt).get(run.get("task_id"), run.get("task_id"))
            print(f"running since {run.get('start_time')}: {name}")
    elif cmd == "today":
        today = dt.date.today().isoformat()
        rows = tt.trackings(start_time=f"ge|{today} 00:00:00", _sort_asc="start_time")
        names = task_names(tt)
        total = 0
        for r in rows:
            start, end = parse_time(r.get("start_time")), parse_time(r.get("end_time"))
            secs = r.get("duration") or ((end - start).total_seconds() if start and end else
                                         (dt.datetime.now(start.tzinfo) - start).total_seconds() if start else 0)
            secs = max(0.0, float(secs))
            total += secs
            span = f"{start:%H:%M}-{end:%H:%M}" if end else f"{start:%H:%M}-  …  " if start else "?"
            print(f"{span}  {fmt_duration(secs):>6}  {names.get(r.get('task_id'), r.get('task_id'))}")
        print(f"{'total':>11}  {fmt_duration(total):>6}")
    else:
        raise TimeTacError(f"unknown command '{cmd}' (see tt --help)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except TimeTacError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
