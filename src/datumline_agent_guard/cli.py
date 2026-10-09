import argparse
import json
import sys

from .core import verify_file


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="agent-guard",
        description="Verify an agent's completion claim against the artifacts it says it produced. "
        "Exit 0 only on VERIFIED.",
    )
    parser.add_argument("manifest", help="path to manifest JSON")
    parser.add_argument("--json", action="store_true", help="print the receipt as JSON")
    args = parser.parse_args(argv)
    try:
        receipt = verify_file(args.manifest)
    except (OSError, ValueError) as e:
        print(f"agent-guard: cannot read manifest {args.manifest}: {e}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(receipt, indent=2))
    else:
        print(f"RECEIPT {receipt['job']} — verdict {receipt['verdict']} (claimed {receipt['claimed_status'] or 'n/a'})")
        for r in receipt["results"]:
            print(f"  [{r['state']}] {r['detail']}")
        if receipt.get("reason"):
            print(f"  {receipt['reason']}")
    return 0 if receipt["verdict"] == "VERIFIED" else 1


if __name__ == "__main__":
    sys.exit(main())
