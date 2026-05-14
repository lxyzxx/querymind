import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate QueryMind golden questions")
    parser.add_argument(
        "--semantic-layer",
        default="querymind/example/semantic_layer.yaml",
        help="YAML semantic layer file.",
    )
    parser.add_argument(
        "--golden-file",
        default="querymind/example/golden_questions.yaml",
        help="YAML golden question file.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable results.")
    args = parser.parse_args()

    from querymind.agent.evaluation import (
        evaluate_golden_questions,
        load_golden_questions,
        summarize_results,
    )
    from querymind.agent.semantic_layer import SemanticLayer

    semantic_layer = SemanticLayer.from_file(args.semantic_layer)
    questions = load_golden_questions(args.golden_file)
    results = evaluate_golden_questions(semantic_layer, questions)
    summary = summarize_results(results)

    if args.json:
        print(
            json.dumps(
                {
                    "summary": summary,
                    "results": [asdict(result) for result in results],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(
            f"Golden questions: {summary['passed']}/{summary['total']} passed "
            f"({summary['pass_rate']:.0%})"
        )
        for result in results:
            status = "PASS" if result.passed else "FAIL"
            print(f"{status} {result.id}: {result.question}")
            if not result.passed:
                if result.error:
                    print(f"  error: {result.error}")
                else:
                    print(f"  expected: {result.expected_sql}")
                    print(f"  generated: {result.generated_sql}")

    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
