import os
import time
import uuid
import csv
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
from neo4j import GraphDatabase


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "results"
RESULTS_DIR.mkdir(exist_ok=True)

RESULT_FILE = RESULTS_DIR / "cognodb_mixed_results.csv"

load_dotenv(PROJECT_ROOT / ".env")

URI = os.getenv("COGNODB_URI")
USERNAME = os.getenv("COGNODB_USERNAME")
PASSWORD = os.getenv("COGNODB_PASSWORD")

OPERATIONS_PER_CLIENT = 50
CONCURRENCY_LEVELS = [10, 20, 40]

READ_NODE_ID = 582
WRITE_SOURCE_ID = 582
WRITE_TARGET_ID = 364

RUN_ID = "benchmark_" + uuid.uuid4().hex


def perform_operation(driver, operation_number):
    """
    Execute one mixed read/write operation.

    Odd operations = read
    Even operations = write
    """

    with driver.session() as session:

        if operation_number % 2 == 0:

            query = """
            CREATE (source:Person {id: $source_id})
            -[:EMAILS {
                timestamp: $timestamp,
                benchmark_run: $run_id
            }]->
            (target:Person {id: $target_id})

            RETURN 1 AS result
            """

            # We don't want duplicate Person nodes.
            # Use existing nodes instead.
            query = """
            MATCH (source:Person {id: $source_id})
            MATCH (target:Person {id: $target_id})
            CREATE (source)-[:EMAILS {
                timestamp: $timestamp,
                benchmark_run: $run_id
            }]->(target)
            RETURN 1 AS result
            """

            session.run(
                query,
                source_id=WRITE_SOURCE_ID,
                target_id=WRITE_TARGET_ID,
                timestamp=int(time.time_ns()),
                run_id=RUN_ID,
            ).consume()

            return "write"

        else:

            query = """
            MATCH (p:Person {id: $node_id})
            RETURN p.id AS result
            """

            session.run(
                query,
                node_id=READ_NODE_ID,
            ).consume()

            return "read"


def worker(driver):
    successful = 0
    failed = 0

    for operation_number in range(OPERATIONS_PER_CLIENT):

        try:
            perform_operation(
                driver,
                operation_number,
            )

            successful += 1

        except Exception as exc:
            failed += 1

    return successful, failed


def cleanup(driver):

    print()
    print("Cleaning up benchmark write relationships...")

    with driver.session() as session:

        result = session.run(
            """
            MATCH ()-[r:EMAILS {benchmark_run: $run_id}]->()
            DELETE r
            RETURN count(r) AS deleted
            """,
            run_id=RUN_ID,
        )

        deleted = result.single()["deleted"]

    print(
        f"Temporary benchmark relationships deleted: {deleted}"
    )


def run_concurrency_test(driver, concurrency):

    total_operations = (
        concurrency * OPERATIONS_PER_CLIENT
    )

    print()
    print("=" * 60)
    print(
        f"Concurrency: {concurrency} clients"
    )
    print(
        f"Operations: {total_operations}"
    )
    print("=" * 60)

    start_time = time.perf_counter()

    successful = 0
    failed = 0

    with ThreadPoolExecutor(
        max_workers=concurrency
    ) as executor:

        futures = [
            executor.submit(
                worker,
                driver,
            )
            for _ in range(concurrency)
        ]

        for future in as_completed(futures):

            worker_successful, worker_failed = (
                future.result()
            )

            successful += worker_successful
            failed += worker_failed

    elapsed = (
        time.perf_counter() - start_time
    )

    throughput = (
        successful / elapsed
        if elapsed > 0
        else 0
    )

    print(
        f"Successful operations: {successful}"
    )

    print(
        f"Failed operations: {failed}"
    )

    print(
        f"Elapsed time: {elapsed:.3f} seconds"
    )

    print(
        f"Throughput: {throughput:.2f} operations/sec"
    )

    return {
        "database": "CognoDB",
        "concurrency": concurrency,
        "operations": total_operations,
        "successful_operations": successful,
        "failed_operations": failed,
        "elapsed_seconds": round(elapsed, 3),
        "throughput_ops_sec": round(
            throughput,
            3,
        ),
    }


def main():

    print("=" * 60)
    print("CognoDB Concurrent Mixed Read/Write Benchmark")
    print("=" * 60)

    driver = GraphDatabase.driver(
        URI,
        auth=(
            USERNAME,
            PASSWORD,
        ),
    )

    results = []

    try:

        driver.verify_connectivity()

        print(
            "CognoDB connection successful."
        )

        print()
        print(
            f"Operations per client: "
            f"{OPERATIONS_PER_CLIENT}"
        )

        print(
            f"Concurrency levels: "
            f"{CONCURRENCY_LEVELS}"
        )

        for concurrency in CONCURRENCY_LEVELS:

            result = run_concurrency_test(
                driver,
                concurrency,
            )

            results.append(result)

    finally:

        cleanup(driver)
        driver.close()

    with open(
        RESULT_FILE,
        "w",
        newline="",
        encoding="utf-8",
    ) as output_file:

        fieldnames = [
            "database",
            "concurrency",
            "operations",
            "successful_operations",
            "failed_operations",
            "elapsed_seconds",
            "throughput_ops_sec",
        ]

        writer = csv.DictWriter(
            output_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(results)

    print()
    print("=" * 60)
    print("MIXED WORKLOAD COMPLETE")
    print("=" * 60)

    print(
        f"Results saved to: {RESULT_FILE}"
    )

    for result in results:

        print(
            f"{result['concurrency']} clients: "
            f"{result['throughput_ops_sec']} ops/sec "
            f"({result['successful_operations']} successful, "
            f"{result['failed_operations']} failed)"
        )


if __name__ == "__main__":
    main()