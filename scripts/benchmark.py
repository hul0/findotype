"""Performance benchmark script for Findotype SQLite search and traversal."""

import statistics
import time
from pathlib import Path

from findotype.config import DEFAULT_DB_PATH
from findotype.services.ontology_service import Findotype


def benchmark(db_path: str = str(DEFAULT_DB_PATH)):
    print(f"Running Findotype performance benchmark against {db_path}...")
    if not Path(db_path).exists():
        print(f"Error: {db_path} does not exist.")
        return

    with Findotype(db_path=db_path) as engine:
        # Warmup
        engine.get_disease("DOID:0001816")
        engine.search_diseases("cancer")

        queries = [
            "angiosarcoma",
            "tuberculosis",
            "melanoma",
            "diabetes",
            "asthma",
            "cardiovascular",
            "leukemia",
            "lymphoma",
            "syndrome",
            "infection",
        ]

        # Benchmark FTS & Multi-tiered Search
        search_times = []
        for q in queries:
            for _ in range(50):
                t0 = time.perf_counter()
                results = engine.search_diseases(q, limit=20)
                t1 = time.perf_counter()
                search_times.append((t1 - t0) * 1000)

        # Benchmark Direct ID Lookup
        id_times = []
        sample_ids = ["DOID:0001816", "DOID:162", "DOID:399", "DOID:4", "DOID:267"]
        for did in sample_ids:
            for _ in range(100):
                t0 = time.perf_counter()
                d = engine.get_disease(did)
                t1 = time.perf_counter()
                id_times.append((t1 - t0) * 1000)

        # Benchmark Recursive Ancestor Hierarchy CTE
        anc_times = []
        for did in sample_ids:
            for _ in range(50):
                t0 = time.perf_counter()
                ancestors = engine.get_ancestors(did)
                t1 = time.perf_counter()
                anc_times.append((t1 - t0) * 1000)

        # Benchmark Recursive Descendant Hierarchy CTE
        desc_times = []
        for did in ["DOID:4", "DOID:162", "DOID:175"]:
            for _ in range(50):
                t0 = time.perf_counter()
                descendants = engine.get_descendants(did)
                t1 = time.perf_counter()
                desc_times.append((t1 - t0) * 1000)

        print("\n--- BENCHMARK RESULTS ---")
        print(f"Direct ID Lookup:        Mean = {statistics.mean(id_times):.3f} ms | P95 = {sorted(id_times)[int(len(id_times)*0.95)]:.3f} ms | P99 = {sorted(id_times)[int(len(id_times)*0.99)]:.3f} ms")
        print(f"Multi-Tiered FTS Search: Mean = {statistics.mean(search_times):.3f} ms | P95 = {sorted(search_times)[int(len(search_times)*0.95)]:.3f} ms | P99 = {sorted(search_times)[int(len(search_times)*0.99)]:.3f} ms")
        print(f"Recursive Ancestors CTE: Mean = {statistics.mean(anc_times):.3f} ms | P95 = {sorted(anc_times)[int(len(anc_times)*0.95)]:.3f} ms | P99 = {sorted(anc_times)[int(len(anc_times)*0.99)]:.3f} ms")
        print(f"Recursive Descendants:   Mean = {statistics.mean(desc_times):.3f} ms | P95 = {sorted(desc_times)[int(len(desc_times)*0.95)]:.3f} ms | P99 = {sorted(desc_times)[int(len(desc_times)*0.99)]:.3f} ms")
        print("-------------------------\n")


if __name__ == "__main__":
    benchmark()
