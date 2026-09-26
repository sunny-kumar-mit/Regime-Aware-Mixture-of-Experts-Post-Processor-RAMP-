"""
CLI entrypoint for ml.pipeline replay
Usage:
  python -m ml.pipeline replay [--dataset <path_or_id>] [--samples <N>]
"""

import argparse
import sys
from ml.pipeline.replay import PipelineReplayer


def main():
    parser = argparse.ArgumentParser(description="RAMP End-to-End Pipeline Replay")
    subparsers = parser.add_subparsers(dest="command")

    replay_parser = subparsers.add_parser("replay", help="Replay entire data and post-processing pipeline")
    replay_parser.add_argument("--dataset", type=str, default=None, help="Path or dataset ID to replay")
    replay_parser.add_argument("--samples", type=int, default=1000, help="Max records to process")

    args = parser.parse_args()

    if args.command == "replay" or len(sys.argv) == 1:
        dataset = getattr(args, "dataset", None)
        samples = getattr(args, "samples", 1000)
        replayer = PipelineReplayer()

        print("=" * 65)
        print("  RAMP END-TO-END PIPELINE REPLAY (SIH26080 - MoES/NCMRWF)")
        print("=" * 65)
        print(f"Target Dataset: {dataset or 'Default RealDataProvider (Synthetic fallback)'}")
        print(f"Max Samples: {samples}")
        print("-" * 65)

        summary = replayer.replay(dataset_source=dataset, max_samples=samples)

        print("\n[PIPELINE REPLAY EXECUTION RESULTS]")
        print(f"Run ID:         {summary.run_id}")
        print(f"Dataset ID:     {summary.dataset_id} ({summary.data_mode})")
        print(f"Overall Status: {summary.overall_status}")
        print(f"Total Duration: {summary.total_duration_sec}s")
        print(f"Quality Status: {summary.quality_status}")
        print(f"Leakage Status: {summary.leakage_status}")
        print("\n[STAGES]")
        for s in summary.stages:
            print(f"  {s.stage_name:<42} [{s.status}] ({s.duration_ms:.1f}ms)")

        print("\n[VERIFICATION SUMMARY (RAMP vs BASELINES)]")
        for k, v in summary.verification_summary.items():
            print(f"  {k:<20}: {v}")
        print("=" * 65)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
