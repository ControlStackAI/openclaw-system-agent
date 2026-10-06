"""Plan-only privileged operations. Applying plans is deliberately not implemented."""
import hashlib
import json
import re


def plan(action, target, facts, policy):
    allowed = {"restart-service": "services", "snapshot": "datasets", "scrub": "pools"}
    if action not in allowed or target not in policy.get(allowed[action], []):
        raise ValueError("This capability is not enabled for that target.")
    if not re.fullmatch(r"[A-Za-z0-9_.:/@-]+", target) or target.startswith("-"):
        raise ValueError("Invalid operation target.")
    if facts.get("phase") != "installed-candidate" or not facts.get("boot_id"):
        raise ValueError("System changes require a freshly inspected installed system.")
    record = {"schema": 1, "action": action, "target": target,
              "boot_id": facts["boot_id"], "root": facts["root"],
              "executor_available": False, "changes_applied": False}
    record["digest"] = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()
    return record
