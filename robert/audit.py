import hashlib, json, time

class AuditLog:
    def __init__(self):
        self.entries = []
        self.prev = "0" * 64

    def append(self, event: dict) -> str:
        entry = {"prev": self.prev, "at": int(time.time()), "event": event}
        blob = json.dumps(entry, sort_keys=True, separators=(",", ":")).encode()
        entry["hash"] = hashlib.sha256(blob).hexdigest()
        self.entries.append(entry)
        self.prev = entry["hash"]
        return entry["hash"]

    def head(self) -> str:
        return self.prev

    def verify(self) -> bool:
        prev = "0" * 64
        for e in self.entries:
            body = {"prev": e["prev"], "at": e["at"], "event": e["event"]}
            blob = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
            if hashlib.sha256(blob).hexdigest() != e["hash"]:
                return False
            if e["prev"] != prev:
                return False
            prev = e["hash"]
        return True
