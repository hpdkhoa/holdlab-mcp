# holdlab-mcp

Hold Lab: Measures the hand and arm, keeps joint limits as walls, and places holds on an object by rule.

8 tools replace 40. Each tool takes `action` and `args`, and calls the existing lab function
unchanged. Merged from: poselab-mcp, fakepose-mcp. Plan steps: 2, 3, 4 of
[the labs plan](https://github.com/hpdkhoa/poselab-mcp/blob/main/docs/MEANING_PLAN.md).

| Tool | Actions |
|---|---|
| `rig` | list, load, describe |
| `pose` | idle, clip, move_part, move_gun, turn_bone, shift_hand, reach |
| `measure` | where, distance, clearance, faces_eye, visible, screen |
| `view` | snapshot, view_cover, render |
| `body` | anatomy, arm_ranges, human_sizes, body_size |
| `hold` | grip, purpose, solve, solve_grip, list_presets, show_preset, set_preset, run_hands |
| `report` | hold, clip |
| `clip` | record, load, scan, fix, retarget, save, check_set |

## Install

```bash
pip install "holdlab-mcp @ git+https://github.com/hpdkhoa/holdlab-mcp.git"
claude mcp add --scope user holdlab -- holdlab-mcp
```

## Test

```bash
pip install -e ".[test]" && pytest
```

MIT license.

## Step 3: contact rules

`hold` action `rules` reads a rule file per hold type and hand (`src/holdlab/rules/pistol_grip_r.json`). Each contact
names the hand part, the gun role from Object Lab Step 1, its kind (point, line or surface) with its source, whether it
pushes, and the sentence it comes from. The pistol grip has two states: `ready` (index straight on line B, no push) and
`firing` (index pad on the trigger blade). Two checks run: completeness (every hand part has a contact or a reason to
be free, every role exists on the gun) and wrap (each digit curls about the grip's axis with the rule's sign, so an
upside-down hand fails).
