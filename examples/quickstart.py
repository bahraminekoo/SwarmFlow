"""SwarmFlow Quickstart — Run a hedge fund swarm in ~10 lines of code."""

import asyncio
import logging

from swarmflow.engine.graph import run_swarm
from swarmflow.engine.templates import load_template_by_name

logging.basicConfig(level=logging.INFO)


async def main():
    # Load the hedge-fund template
    template = load_template_by_name("hedge-fund")
    worker_configs = template.get_worker_configs()

    # Run the swarm
    result = await run_swarm(
        team_name="my-fund",
        goal="Evaluate TSLA, AMD, META for Q2 2026 portfolio allocation",
        worker_configs=worker_configs,
    )

    # Print the final report
    print("\n" + "=" * 80)
    print("FINAL REPORT")
    print("=" * 80)
    print(result.get("final_report", "No report generated"))

    # Print individual scores
    for report in result.get("reports", []):
        score_bar = "█" * int((report.score or 0) * 20) + "░" * (20 - int((report.score or 0) * 20))
        print(f"  {report.agent_name:20s} [{score_bar}] {report.score:.2f}  {report.summary}")


if __name__ == "__main__":
    asyncio.run(main())
