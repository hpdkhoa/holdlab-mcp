import json

import pytest

from holdlab import contact_rules as C

ROLES = {r: {} for r in ("grip_back", "grip_side_r", "grip_front", "thumb_rest", "trigger_blade")}
ROLES["line_b"] = {"side": "r"}


def right_hand():
    """A right hand wrapped on a pistol grip, (forward, up, left) cm: fingers run forward on the right side, across
    the front strap to the left, then back; the thumb runs forward on the left side and closes in."""
    finger = lambda u: [[0, u, -1.5], [2, u, -1.0], [2, u, 1.0], [0.5, u, 1.5]]
    return {"middle": finger(-4), "ring": finger(-6), "pinky": finger(-8),
            "thumb": [[-3, -2, 2.0], [-1, -2, 2.0], [0.5, -2, 1.2]]}


def upside_down(joints):
    """The same hand turned 180 degrees about the bore: up and left change sign."""
    return {d: [[p[0], -p[1], -p[2]] for p in pts] for d, pts in joints.items()}


def test_the_m1911_ready_rules_are_complete():
    r = C.rules("pistol_grip", "r", "ready")
    assert r["checks"][0]["pass"]
    assert {c["hand"]: c["gun"] for c in r["contacts"]}["index"] == "line_b"


def test_firing_puts_the_index_pad_on_the_trigger_blade():
    contacts = {c["hand"]: c for c in C.rules("pistol_grip", "r", "firing")["contacts"]}
    assert contacts["index"]["gun"] == "trigger_blade" and contacts["index"]["push"]
    assert len(contacts) == 7


def test_a_hand_part_with_no_rule_and_no_reason_fails():
    r = C.load_rules("pistol_grip", "r")
    r["states"]["ready"]["contacts"] = [c for c in r["states"]["ready"]["contacts"] if c["hand"] != "pinky"]
    row = next(p for p in C.completeness(r, "ready")["parts"] if p["hand"] == "pinky")
    assert not row["ok"]
    r["states"]["ready"]["free"] = {"pinky": "pinky free on a short grip"}
    assert C.completeness(r, "ready")["pass"]


def test_a_role_missing_on_the_gun_or_on_the_wrong_side_fails():
    r = C.load_rules("pistol_grip", "r")
    assert C.completeness(r, "ready", ROLES)["pass"]
    no_line_b = {k: v for k, v in ROLES.items() if k != "line_b"}
    assert not C.completeness(r, "ready", no_line_b)["pass"]
    assert not C.completeness(r, "ready", {**ROLES, "line_b": {"side": "l"}})["pass"]


def test_curl_of_a_right_angle_is_one_about_the_hinge():
    assert C.curl([[0, 0, 0], [1, 0, 0], [1, 0, 1]]) == pytest.approx([0, 1, 0])  # forward x left = up
    assert C.curl([[0, 0, 0], [1, 0, 0], [2, 0, 0]]) == [0, 0, 0]


def test_the_wrapped_right_hand_passes_and_upside_down_fails():
    r = C.load_rules("pistol_grip", "r")
    good = C.wrap(r, right_hand())
    assert good["pass"], good
    bad = C.wrap(r, upside_down(right_hand()))
    assert not bad["pass"]
    assert all(not d["ok"] for d in bad["digits"])


def test_a_straight_digit_has_no_curl_to_read_and_fails():
    j = right_hand()
    j["middle"] = [[0, -4, -1.5], [2, -4, -1.5], [4, -4, -1.5], [6, -4, -1.5]]
    row = next(d for d in C.wrap(C.load_rules("pistol_grip", "r"), j)["digits"] if d["digit"] == "middle")
    assert not row["ok"] and row["curl_size"] == 0


def test_rules_reads_the_gun_roles_from_meaning_json(tmp_path):
    m = tmp_path / "meaning.json"
    m.write_text(json.dumps({"roles": ROLES}))
    out = C.rules("pistol_grip", "r", "ready", str(m), right_hand())
    assert out["status"] == "PASS" and [c["check"] for c in out["checks"]] == ["completeness", "wrap"]


def test_an_unknown_hold_type_names_the_known_ones():
    with pytest.raises(Exception, match="pistol_grip_r"):
        C.load_rules("forend", "r")
