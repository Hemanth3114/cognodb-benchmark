import csv
import os
import statistics
import time
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase


# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "results"
RESULTS_DIR.mkdir(exist_ok=True)

RESULT_FILE = RESULTS_DIR / "cognodb_results.csv"


# ---------------------------------------------------------
# Environment
# ---------------------------------------------------------

load_dotenv(PROJECT_ROOT / ".env")

URI = os.getenv("COGNODB_URI")
USERNAME = os.getenv("COGNODB_USERNAME")
PASSWORD = os.getenv("COGNODB_PASSWORD")


# ---------------------------------------------------------
# Benchmark configuration
# ---------------------------------------------------------

WARMUP_ITERATIONS = 20
MEASURED_ITERATIONS = 200

# Use deterministic node IDs from the dataset.
TEST_NODE_ID = 582

# A timestamp value known to exist in the loaded dataset.
TEST_TIMESTAMP = 0


# ---------------------------------------------------------
# Queries
# ---------------------------------------------------------

QUERIES = {
    "1-hop traversal": """
        MATCH (p:Person {id: $node_id})-[:EMAILS]->(n)
        RETURN count(n) AS result
    """,

    "2-hop traversal": """
        MATCH (p:Person {id: $node_id})
              -[:EMAILS]->()
              -[:EMAILS]->(n)
        RETURN count(n) AS result
    """,

    "3-hop traversal": """
    MATCH (p:Person {id: $node_id})
          -[:EMAILS]->(a)
          -[:EMAILS]->(b)
          -[:EMAILS]->(n)
    RETURN n.id AS result
    LIMIT 100
    """,

    "point lookup": """
        MATCH (p:Person {id: $node_id})
        RETURN p.id AS result
    """,

    "indexed/filtered lookup": """
        MATCH (p:Person)
        WHERE p.id = $node_id
        RETURN p.id AS result
    """,

    "aggregation": """
        MATCH (p:Person)-[:EMAILS]->(n:Person)
        RETURN p.id AS source, count(n) AS degree
        ORDER BY degree DESC
        LIMIT 10
    """,
}


# ---------------------------------------------------------
# Benchmark helper
# ---------------------------------------------------------

def run_query(session, query, parameters):
    """
    Execute one query and consume the complete result.
    """

    result = session.run(
        query,
        parameters,
    )

    return result.data()


def percentile(values, percentile_value):
    """
    Calculate percentile using Python's statistics module.
    """

    if not values:
        return None

    ordered = sorted(values)

    position = (
        percentile_value / 100
    ) * (len(ordered) - 1)

    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)

    fraction = position - lower

    return (
        ordered[lower]
        + (ordered[upper] - ordered[lower]) * fraction
    )


def benchmark_workload(driver, workload_name, query):
    """
    Run warm-up iterations followed by measured iterations.
    """

    print()
    print("=" * 60)
    print(workload_name)
    print("=" * 60)

    latencies = []
    failures = 0

    with driver.session() as session:

        # -------------------------------------------------
        # Warm-up
        # -------------------------------------------------

        print(
            f"Warm-up: {WARMUP_ITERATIONS} iterations"
        )

        for _ in range(WARMUP_ITERATIONS):

            try:
                run_query(
                    session,
                    query,
                    {
                        "node_id": TEST_NODE_ID,
                        "timestamp": TEST_TIMESTAMP,
                    },
                )

            except Exception as exc:
                print(
                    f"Warm-up error: {exc}"
                )

        # -------------------------------------------------
        # Measurement
        # -------------------------------------------------

        print(
            f"Measurement: {MEASURED_ITERATIONS} iterations"
        )

        for iteration in range(MEASURED_ITERATIONS):

            start = time.perf_counter()

            try:

                run_query(
                    session,
                    query,
                    {
                        "node_id": TEST_NODE_ID,
                        "timestamp": TEST_TIMESTAMP,
                    },
                )

                elapsed_ms = (
                    time.perf_counter() - start
                ) * 1000

                latencies.append(elapsed_ms)

            except Exception as exc:

                failures += 1

                print(
                    f"Iteration {iteration + 1} failed: {exc}"
                )

    if not latencies:
        raise RuntimeError(
            f"No successful measurements for {workload_name}"
        )

    p50 = percentile(
        latencies,
        50,
    )

    p95 = percentile(
        latencies,
        95,
    )

    average = statistics.mean(
        latencies
    )

    minimum = min(latencies)
    maximum = max(latencies)

    print(
        f"Successful: {len(latencies)}"
    )

    print(
        f"Failures: {failures}"
    )

    print(
        f"Average: {average:.3f} ms"
    )

    print(
        f"P50: {p50:.3f} ms"
    )

    print(
        f"P95: {p95:.3f} ms"
    )

    print(
        f"Min: {minimum:.3f} ms"
    )

    print(
        f"Max: {maximum:.3f} ms"
    )

    return {
        "database": "CognoDB",
        "workload": workload_name,
        "warmup_iterations": WARMUP_ITERATIONS,
        "measured_iterations": len(latencies),
        "failures": failures,
        "average_ms": round(average, 3),
        "p50_ms": round(p50, 3),
        "p95_ms": round(p95, 3),
        "min_ms": round(minimum, 3),
        "max_ms": round(maximum, 3),
    }


# ---------------------------------------------------------
# Main benchmark
# ---------------------------------------------------------

def main():

    print("=" * 60)
    print("CognoDB Benchmark")
    print("=" * 60)

    if not URI:
        raise RuntimeError(
            "COGNODB_URI is missing from .env"
        )

    if not USERNAME:
        raise RuntimeError(
            "COGNODB_USERNAME is missing from .env"
        )

    if not PASSWORD:
        raise RuntimeError(
            "COGNODB_PASSWORD is missing from .env"
        )

    driver = GraphDatabase.driver(
        URI,
        auth=(USERNAME, PASSWORD),
    )

    results = []

    try:

        print("Checking database connectivity...")

        driver.verify_connectivity()

        print("CognoDB connection successful.")

        print()
        print(
            f"Warm-up iterations: {WARMUP_ITERATIONS}"
        )

        print(
            f"Measured iterations: {MEASURED_ITERATIONS}"
        )

        # -------------------------------------------------
        # Run workloads
        # -------------------------------------------------

        for workload_name, query in QUERIES.items():

            result = benchmark_workload(
                driver,
                workload_name,
                query,
            )

            results.append(result)

    finally:

        driver.close()

    # -----------------------------------------------------
    # Save CSV
    # -----------------------------------------------------

    fieldnames = [
        "database",
        "workload",
        "warmup_iterations",
        "measured_iterations",
        "failures",
        "average_ms",
        "p50_ms",
        "p95_ms",
        "min_ms",
        "max_ms",
    ]

    with open(
        RESULT_FILE,
        "w",
        newline="",
        encoding="utf-8",
    ) as output_file:

        writer = csv.DictWriter(
            output_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(results)

    # -----------------------------------------------------
    # Summary
    # -----------------------------------------------------

    print()
    print("=" * 60)
    print("BENCHMARK COMPLETE")
    print("=" * 60)

    print(
        f"Results saved to: {RESULT_FILE}"
    )

    print()

    for result in results:

        print(
            f"{result['workload']}: "
            f"P50={result['p50_ms']} ms, "
            f"P95={result['p95_ms']} ms"
        )


if __name__ == "__main__":
    main()