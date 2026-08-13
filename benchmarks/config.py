from pathlib import Path


# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RESULTS_DIR = PROJECT_ROOT / "results"

CANONICAL_DATASET = DATA_DIR / "email_edges_canonical.csv"


# Dataset information
DATASET_NAME = "SNAP email-Eu-core temporal"
EXPECTED_NODE_COUNT = 986
EXPECTED_RELATIONSHIP_COUNT = 327336


# Benchmark configuration
WARMUP_RUNS = 10
MEASUREMENT_RUNS = 100


# Concurrent workload levels
CONCURRENCY_LEVELS = [1, 5, 10, 20]


# Workload names
WORKLOADS = [
    "one_hop",
    "two_hop",
    "three_hop",
    "point_lookup",
    "filtered_lookup",
    "aggregation",
]


# Database names
DATABASES = [
    "cognodb",
    "neo4j",
    "memgraph",
    "falkordb",
    "tigergraph",
]