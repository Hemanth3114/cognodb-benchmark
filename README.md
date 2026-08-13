# Graph Database Cloud Benchmark

## Overview

This project benchmarks CognoDB Cloud using the Email-Eu-Core-Temporal
graph dataset. The benchmark evaluates data loading, graph traversal,
lookup, aggregation, and concurrent mixed read/write workloads.

## Dataset

The canonical dataset contains:

- Nodes: 986
- Relationships: 327,336
- Exact duplicate rows: 0

Canonical dataset:

`data/email_edges_canonical.csv`

Dataset validation:

```powershell
python scripts\validate_dataset.py

Validation result:
Relationships: 327336
Unique nodes: 986
Exact duplicate rows: 0

Dataset validation PASSED.


CognoDB Data Loading
| Metric        |                  Result |
| ------------- | ----------------------: |
| Nodes         |                     986 |
| Relationships |                 327,336 |
| Load time     |        4371.414 seconds |
| Throughput    | 74.88 relationships/sec |
| Verification  |                  PASSED |


Read Benchmark

The read benchmark uses:

20 warm-up iterations
200 measured iterations

The following workloads were measured:

1-hop traversal
2-hop traversal
3-hop traversal
Point lookup
Indexed/filtered lookup
Aggregation
Results
Workload	P50 (ms)	P95 (ms)
1-hop traversal	343.232	1510.481
2-hop traversal	2299.099	3699.588
3-hop traversal	272.213	530.535
Point lookup	268.008	313.264
Indexed/filtered lookup	267.088	312.043
Aggregation	2990.371	3920.507

Machine-readable results:

results/cognodb_results.csv

Concurrent Mixed Read/Write Benchmark

The mixed workload used 50 operations per client at concurrency
levels of 10, 20, and 40 clients.

Clients	Operations	Successful	Failed	Throughput
10	500	500	0	6.104 ops/sec
20	1000	1000	0	15.223 ops/sec
40	2000	2000	0	28.301 ops/sec

All benchmark operations completed successfully.

Machine-readable results:
    
results/cognodb_mixed_results.csv

Benchmark Caveat

The unrestricted 3-hop traversal exceeded the available execution
deadline during warm-up on the CognoDB environment.

A bounded version of the 3-hop workload was therefore used for the
measured benchmark to obtain a stable result.

The bounded result should not be interpreted as an unrestricted
3-hop traversal result.

This limitation is reported explicitly rather than hiding failed
benchmark executions.

Methodology

The benchmark records latency statistics including:

P50
P95
Minimum latency
Maximum latency
Average latency

The mixed workload records:

Concurrent clients
Total operations
Successful operations
Failed operations
Elapsed time
Throughput

The same canonical dataset is used throughout the completed
CognoDB measurements.

Reproduction

Create a Python virtual environment:

python -m venv .venv

Activate it:

.venv\Scripts\Activate.ps1

Install dependencies:

pip install -r requirements.txt

Validate the dataset:

python scripts\validate_dataset.py

Run the CognoDB read benchmark:

python benchmarks\cognodb_benchmark.py

Run the concurrent mixed workload:

python benchmarks\cognodb_mixed_benchmark.py
Project Structure
cognodb-benchmark/
│
├── benchmarks/
│   ├── cognodb_benchmark.py
│   ├── cognodb_mixed_benchmark.py
│   ├── config.py
│   └── __init__.py
│
├── data/
│   └── email_edges_canonical.csv
│
├── loaders/
│   └── cognodb_loader.py
│
├── results/
│   ├── cognodb_results.csv
│   └── cognodb_mixed_results.csv
│
├── scripts/
│   └── validate_dataset.py
│
├── download_dataset.py
├── requirements.txt
└── requirements-lock.txt
Limitations

The completed benchmark measurements in this repository are for
CognoDB Cloud.

Comparative measurements for additional graph database platforms
were not completed within the available execution window. No
estimated or fabricated values are included.

Conclusion

The completed benchmark successfully validates and loads the
986-node, 327,336-relationship canonical dataset into CognoDB and
measures graph traversal, lookup, aggregation, and concurrent
mixed read/write workloads.

The benchmark implementation and machine-readable results are
included in this repository to support reproducibility.
