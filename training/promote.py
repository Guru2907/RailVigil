"""Make a trained run the model the backend uses.

    python training/promote.py --name railvigil-s

Copies training/runs/<name>/weights/best.pt to backend/models/railvigil-seg.pt
(registered as "railvigil-seg"). Then switch the backend to it by adding this
line to backend/.env and restarting the server:

    ENC_MODELS=railvigil-seg

Only promote a run that has been evaluated (evaluate.py) and is better than
the baseline on the test split.
"""

import argparse
import json
import shutil

import rvdata as rv


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--name", required=True)
    p.add_argument("--force", action="store_true", help="promote even without an eval_test.json")
    args = p.parse_args()

    run_dir = rv.RUNS / args.name
    best = run_dir / "weights" / "best.pt"
    report = run_dir / "eval_test.json"
    if not best.is_file():
        raise SystemExit(f"No weights at {best}")
    if not report.is_file() and not args.force:
        raise SystemExit(f"Run {args.name} has not been evaluated. Run evaluate.py first (or pass --force).")

    target = rv.BACKEND / "models" / "railvigil-seg.pt"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(best, target)
    sha12 = rv.sha256_file(target)[:12]
    print(f"Promoted {best} -> {target} (version {sha12})")
    if report.is_file():
        o = json.loads(report.read_text())["overall"]["mask"]
        print("Results log row for docs/EVALUATION.md:")
        print(f"| {rv.now_iso()[:10]} | Encroachment | railvigil-seg @ {sha12} (run {args.name}) | frozen test split "
              f"| mask mAP50 {o['map50']:.3f}, mAP50-95 {o['map50_95']:.3f}, P {o['precision']:.3f}, "
              f"R {o['recall']:.3f} | training/runs/{args.name}/eval_test.json |")
    print("\nTo use it: add  ENC_MODELS=railvigil-seg  to backend/.env and restart the backend.")


if __name__ == "__main__":
    main()
