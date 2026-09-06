"""Human play — an interactive attacker console over the uniform Session.

This is a PERSON playing the range: you get a briefing + a terminal, you type commands step by
step (exactly the actions an agent would emit), and your session is scored + saved as a trajectory.
The agent adapter (later) drives the SAME Session — human and agent are identical to the range.

Usage (on the ROS box):  python3 play.py <task>          e.g.  python3 play.py task01
Console:  <any shell/ros2 command>   |   submit <value>   |   help   |   done
Long-running attacks: append ' &' to background them (e.g. ros2 topic pub ... &).
"""
from __future__ import annotations
import getpass, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "challenges"))
from session import Session          # noqa: E402
from registry import make            # noqa: E402


def main(task):
    scenario, backend = make(task)
    who = f"human:{getpass.getuser()}"
    out = os.path.join(HERE, "..", "trajectories", f"{scenario['id']}_{who.replace(':','_')}.jsonl")
    s = Session(scenario, backend, actor_kind="human", actor_name=who, out_path=out)
    briefing, err = s.start()
    if err:
        print(err); return 1
    print("\n=== KNIGHTFALL ::", scenario["id"], "===")
    print(json.dumps(briefing, indent=2, ensure_ascii=False))
    print("\nType a command (or 'submit <value>', 'help', 'done'). Background with trailing '&'.\n")
    try:
        while True:
            try:
                line = input("attacker$ ").strip()
            except EOFError:
                break
            if not line:
                continue
            if line == "help":
                print("  <command>       run in the attacker terminal\n"
                      "  submit <value>  submit a flag/value to the judge\n"
                      "  done            finish and score"); continue
            if line == "done":
                break
            if line.startswith("submit "):
                ok = s.submit(line[len("submit "):].strip())
                print(f"  judge: accepted={ok}")
                continue
            print(s.run_command(line))
            bl = s.budget_left()
            print(f"  [budget left: {bl['steps']} steps, {bl['wall_clock_s']}s]")
    finally:
        res = s.finish()
    print("\n=== RESULT ===")
    print({k: res.get(k) for k in ("outcome", "graded_score", "max_score", "binary_pass")})
    print("breakdown:", res.get("breakdown"))
    print("trajectory:", res.get("trajectory"))
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python3 play.py <task>  (task01|task03)"); sys.exit(2)
    sys.exit(main(sys.argv[1]))
