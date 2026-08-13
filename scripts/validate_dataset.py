import sys
from pathlib import Path

import pandas as pd


# Add the project root to Python's import path.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from benchmarks.config import (
    CANONICAL_DATASET,
    EXPECTED_NODE_COUNT,
    EXPECTED_RELATIONSHIP_COUNT,
)


def validate_dataset():
    if not CANONICAL_DATASET.exists():
        print(f"ERROR: Dataset not found: {CANONICAL_DATASET}")
        return False

    print(f"Dataset: {CANONICAL_DATASET}")

    data = pd.read_csv(CANONICAL_DATASET)

    required_columns = {"source_id", "target_id", "timestamp"}

    if not required_columns.issubset(data.columns):
        missing = required_columns - set(data.columns)
        print(f"ERROR: Missing columns: {sorted(missing)}")
        return False

    relationship_count = len(data)

    node_ids = set(data["source_id"]) | set(data["target_id"])
    node_count = len(node_ids)

    duplicate_count = data.duplicated().sum()

    print(f"Relationships: {relationship_count}")
    print(f"Unique nodes: {node_count}")
    print(f"Exact duplicate rows: {duplicate_count}")

    valid = True

    if relationship_count != EXPECTED_RELATIONSHIP_COUNT:
        print(
            f"ERROR: Expected {EXPECTED_RELATIONSHIP_COUNT} relationships "
            f"but found {relationship_count}."
        )
        valid = False

    if node_count != EXPECTED_NODE_COUNT:
        print(
            f"ERROR: Expected {EXPECTED_NODE_COUNT} nodes "
            f"but found {node_count}."
        )
        valid = False

    if duplicate_count != 0:
        print(
            f"ERROR: Dataset contains {duplicate_count} exact duplicate rows."
        )
        valid = False

    if data["source_id"].isna().any() or data["target_id"].isna().any():
        print("ERROR: Missing source or target node IDs.")
        valid = False

    if data["timestamp"].isna().any():
        print("ERROR: Missing timestamps.")
        valid = False

    if valid:
        print("\nDataset validation PASSED.")
        return True

    print("\nDataset validation FAILED.")
    return False


if __name__ == "__main__":
    success = validate_dataset()
    sys.exit(0 if success else 1)