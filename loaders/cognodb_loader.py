import os
import sys
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from neo4j import GraphDatabase


# ---------------------------------------------------------
# Project setup
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from benchmarks.config import (
    CANONICAL_DATASET,
    EXPECTED_NODE_COUNT,
    EXPECTED_RELATIONSHIP_COUNT,
)


# ---------------------------------------------------------
# Environment configuration
# ---------------------------------------------------------

load_dotenv(PROJECT_ROOT / ".env")

COGNODB_URI = os.getenv("COGNODB_URI")
COGNODB_USERNAME = os.getenv("COGNODB_USERNAME")
COGNODB_PASSWORD = os.getenv("COGNODB_PASSWORD")


def check_environment():
    """Make sure all required credentials are available."""

    missing = []

    if not COGNODB_URI:
        missing.append("COGNODB_URI")

    if not COGNODB_USERNAME:
        missing.append("COGNODB_USERNAME")

    if not COGNODB_PASSWORD:
        missing.append("COGNODB_PASSWORD")

    if missing:
        raise RuntimeError(
            "Missing environment variables: "
            + ", ".join(missing)
        )


# ---------------------------------------------------------
# Database connection
# ---------------------------------------------------------

def create_driver():
    """Create a Neo4j-compatible driver for CognoDB."""

    check_environment()

    return GraphDatabase.driver(
        COGNODB_URI,
        auth=(COGNODB_USERNAME, COGNODB_PASSWORD),
    )


# ---------------------------------------------------------
# Database preparation
# ---------------------------------------------------------

def clear_database(driver):
    """
    Remove existing benchmark data.

    This makes the ingest measurement reproducible.
    """

    print("Clearing existing benchmark data...")

    with driver.session() as session:
        session.run(
            """
            MATCH (n)
            DETACH DELETE n
            """
        ).consume()

    print("Database cleared.")


def create_constraints(driver):
    """
    Create a uniqueness constraint for Person nodes.

    The constraint allows efficient and deterministic
    matching of nodes during loading.
    """

    print("Creating Person constraint...")

    with driver.session() as session:
        try:
            session.run(
                """
                CREATE CONSTRAINT person_id_unique IF NOT EXISTS
                FOR (p:Person)
                REQUIRE p.id IS UNIQUE
                """
            ).consume()

            print("Constraint ready.")

        except Exception as exc:
            print(f"Constraint creation warning: {exc}")


# ---------------------------------------------------------
# Data loading
# ---------------------------------------------------------

def load_relationship_batch(tx, rows):
    """
    Insert one batch of relationship records.

    UNWIND allows many records to be sent in a single
    database transaction instead of issuing one query
    per relationship.
    """

    tx.run(
        """
        UNWIND $rows AS row

        MERGE (source:Person {id: row.source_id})
        MERGE (target:Person {id: row.target_id})

        CREATE (source)-[:EMAILS {
            timestamp: row.timestamp
        }]->(target)
        """,
        rows=rows,
    ).consume()


def load_dataset(driver, batch_size=100):
    """Load the canonical benchmark dataset."""

    if not CANONICAL_DATASET.exists():
        raise FileNotFoundError(
            f"Dataset not found: {CANONICAL_DATASET}"
        )

    print(f"Loading dataset: {CANONICAL_DATASET}")

    data = pd.read_csv(CANONICAL_DATASET)

    actual_relationships = len(data)

    if actual_relationships != EXPECTED_RELATIONSHIP_COUNT:
        raise RuntimeError(
            f"Expected {EXPECTED_RELATIONSHIP_COUNT} relationships, "
            f"but found {actual_relationships}."
        )

    print(f"Relationships to load: {actual_relationships}")

    start_time = time.perf_counter()

    total_loaded = 0

    with driver.session() as session:

        for start in range(0, len(data), batch_size):

            batch = data.iloc[start:start + batch_size]

            rows = [
                {
                    "source_id": int(row.source_id),
                    "target_id": int(row.target_id),
                    "timestamp": int(row.timestamp),
                }
                for row in batch.itertuples(index=False)
            ]

            session.execute_write(
                load_relationship_batch,
                rows,
            )

            total_loaded += len(rows)

            print(
                f"Loaded {total_loaded:,} / "
                f"{actual_relationships:,} relationships"
            )

    elapsed = time.perf_counter() - start_time

    throughput = (
        total_loaded / elapsed
        if elapsed > 0
        else 0
    )

    print()
    print("Ingest complete.")
    print(f"Relationships loaded: {total_loaded:,}")
    print(f"Elapsed time: {elapsed:.3f} seconds")
    print(f"Throughput: {throughput:,.2f} relationships/sec")

    return elapsed, throughput


# ---------------------------------------------------------
# Verification
# ---------------------------------------------------------

def verify_database(driver):
    """Verify final node and relationship counts."""

    print()
    print("Verifying database...")

    with driver.session() as session:

        node_result = session.run(
            """
            MATCH (p:Person)
            RETURN count(p) AS count
            """
        ).single()

        relationship_result = session.run(
            """
            MATCH ()-[r:EMAILS]->()
            RETURN count(r) AS count
            """
        ).single()

    node_count = node_result["count"]
    relationship_count = relationship_result["count"]

    print(f"Database nodes: {node_count:,}")
    print(f"Database relationships: {relationship_count:,}")

    expected_nodes = EXPECTED_NODE_COUNT
    expected_relationships = EXPECTED_RELATIONSHIP_COUNT

    if node_count != expected_nodes:
        raise RuntimeError(
            f"Node count mismatch. "
            f"Expected {expected_nodes}, got {node_count}."
        )

    if relationship_count != expected_relationships:
        raise RuntimeError(
            f"Relationship count mismatch. "
            f"Expected {expected_relationships}, got "
            f"{relationship_count}."
        )

    print("Database verification PASSED.")


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():

    print("=" * 60)
    print("CognoDB Benchmark Dataset Loader")
    print("=" * 60)

    driver = create_driver()

    try:

        print("Checking CognoDB connectivity...")

        driver.verify_connectivity()

        print("CognoDB connectivity verified.")
        print()

        clear_database(driver)

        create_constraints(driver)

        load_dataset(driver)

        verify_database(driver)

    finally:

        driver.close()

    print()
    print("=" * 60)
    print("CognoDB loading completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    main()