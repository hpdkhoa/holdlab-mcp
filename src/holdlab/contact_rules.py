"""Step 3 of the meaning plan: contact rules per hold type.

A rule file (rules/<hold_type>_<hand>.json) says which hand part touches which gun role, its kind (point, line or
surface) with the source of that kind, whether it pushes, and the owner's sentence it comes from. A hand part with no
contact must have a written reason to be free. The solver reads these rules; it does not invent contacts.

Two checks:
- completeness: every hand part has a contact or a reason, and every contact's role exists on the gun (Object Lab
  Step 1, meaning.json) and is on the hand's side;
- wrap: each digit's curl axis against the rule's axis has the rule's sign. A hand placed upside down fails here
  before anything else runs.

Points are in the gun's frame, cm along (forward, up, left), as Object Lab writes them.
"""

import json
import math
from pathlib import Path

from mcp.server.mcpserver.exceptions import ToolError

RULES = Path(__file__).parent / "rules"
CONTRACT = "holdlab-rules/1"
AXES = {"forward": 0, "up": 1, "left": 2}


def load_rules(hold_type: str, hand: str = "r") -> dict:
    path = RULES / f"{hold_type}_{hand}.json"
    if not path.exists():
        known = sorted(p.stem for p in RULES.glob("*.json"))
        raise ToolError(f"rules: no rule file {path.name}. Known: {', '.join(known)}")
    rules = json.loads(path.read_text(encoding="utf-8"))
    if rules.get("contract") != CONTRACT:
        raise ToolError(f"rules: {path.name} is not {CONTRACT}")
    return rules


def state_contacts(rules: dict, state: str) -> tuple[list, dict]:
    """The contacts and free parts of one state; a state 'from' another takes its contacts and replaces by hand part."""
    st = rules["states"].get(state)
    if st is None:
        raise ToolError(f"rules: no state {state!r}. States: {', '.join(rules['states'])}")
    if "from" in st:
        contacts, free = state_contacts(rules, st["from"])
        new = {c["hand"]: c for c in st.get("replace", [])}
        contacts = [new.pop(c["hand"], c) for c in contacts] + list(new.values())
        return contacts, {**free, **st.get("free", {})}
    return list(st["contacts"]), dict(st.get("free", {}))


def completeness(rules: dict, state: str, roles: dict | None = None) -> dict:
    """Every hand part has exactly one contact or a reason to be free; each contact names its kind, its source and
    the owner's sentence; with the gun's roles, each role exists and sits on the hand's side."""
    contacts, free = state_contacts(rules, state)
    rows, ok_all = [], True
    for part in rules["hand_parts"]:
        mine = [c for c in contacts if c["hand"] == part]
        row = {"hand": part}
        if len(mine) == 1:
            c = mine[0]
            row.update({"gun": c["gun"], "kind": c["kind"], "push": c["push"]})
            missing = [k for k in ("kind", "kind_source", "owner") if not c.get(k)]
            if c["kind"] not in ("point", "line", "surface"):
                missing.append("kind is point, line or surface")
            if not c["push"] and not c.get("why_no_push"):
                missing.append("why_no_push")
            if roles is not None:
                role = roles.get(c["gun"])
                if role is None:
                    missing.append(f"role {c['gun']} on the gun")
                elif role.get("side") and role["side"] != rules["hand"]:
                    missing.append(f"role {c['gun']} on the {role['side']} side, hand {rules['hand']}")
            row["ok"] = not missing
            if missing:
                row["missing"] = missing
        elif not mine and free.get(part):
            row.update({"free": free[part], "ok": True})
        else:
            row.update({"ok": False, "missing": [f"{len(mine)} contacts and no reason to be free"]})
        ok_all &= row["ok"]
        rows.append(row)
    extra = sorted({c["hand"] for c in contacts} - set(rules["hand_parts"]))
    if extra:
        ok_all = False
        rows.append({"hand": extra, "ok": False, "missing": ["contact for a part the rule file does not list"]})
    return {"check": "completeness", "state": state, "pass": bool(ok_all), "parts": rows}


def _sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def _cross(a, b):
    """a x b in the gun's frame. (forward, up, left) is a left-handed order (left = up x forward), so the textbook
    component formula gives -(a x b) here."""
    return [-(a[1] * b[2] - a[2] * b[1]), -(a[2] * b[0] - a[0] * b[2]), -(a[0] * b[1] - a[1] * b[0])]


def _unit(a):
    n = math.sqrt(sum(x * x for x in a))
    return [x / n for x in a] if n > 1e-12 else [0.0, 0.0, 0.0]


def curl(points: list) -> list:
    """A digit's curl: the sum over its joints of (segment before) x (segment after), unit segments. Its direction is
    the hinge the digit bends about, its length the summed sine of the bends."""
    seg = [_unit(_sub(points[k + 1], points[k])) for k in range(len(points) - 1)]
    total = [0.0, 0.0, 0.0]
    for a, b in zip(seg, seg[1:]):
        c = _cross(a, b)
        total = [total[i] + c[i] for i in range(3)]
    return total


def wrap(rules: dict, joints: dict) -> dict:
    """joints: {digit: [knuckle, ..., tip]} in the gun's frame (forward, up, left). Each digit in the rule's sign table
    must curl about the rule's axis with the rule's sign, by at least min_curl."""
    w = rules["wrap"]
    sign_axis = -1 if w["axis"].startswith("-") else 1
    ax = AXES[w["axis"].lstrip("+-")]
    rows, ok_all = [], True
    for digit, want in w["sign"].items():
        pts = joints.get(digit)
        if not pts or len(pts) < 3:
            rows.append({"digit": digit, "ok": False, "missing": "fewer than 3 joint points"})
            ok_all = False
            continue
        c = curl(pts)
        size = math.sqrt(sum(x * x for x in c))
        along = sign_axis * c[ax]
        ok = size >= w["min_curl"] and along * want > 0
        rows.append({"digit": digit, "curl_axis": [round(x / size, 3) for x in c] if size else None,
                     "curl_size": round(size, 3), "along_axis": round(along / size, 3) if size else 0.0,
                     "want_sign": want, "ok": bool(ok)})
        ok_all &= ok
    return {"check": "wrap", "axis": w["axis"], "pass": bool(ok_all), "digits": rows, "rule": w["rule"]}


def rules(hold_type: str, hand: str = "r", state: str = "ready", meaning: str | None = None,
          joints: dict | None = None) -> dict:
    """Step 3 contact rules: the hold type's rule file for one hand and state, its completeness check (against the
    gun's Step 1 roles when meaning names a meaning.json), and the wrap check when joints are given ({digit: [knuckle,
    ..., tip]} in the gun's frame, cm (forward, up, left))."""
    r = load_rules(hold_type, hand)
    roles = json.loads(Path(meaning).read_text(encoding="utf-8"))["roles"] if meaning else None
    contacts, free = state_contacts(r, state)
    out = {"contract": CONTRACT, "hold_type": hold_type, "hand": hand, "state": state, "contacts": contacts,
           "free": free, "wrap_rule": r["wrap"], "checks": [completeness(r, state, roles)]}
    if joints is not None:
        out["checks"].append(wrap(r, joints))
    out["status"] = "PASS" if all(c["pass"] for c in out["checks"]) else "FAIL"
    return out
