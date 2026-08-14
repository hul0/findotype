"""Validator for untrusted ontology JSON inputs."""

import json
from pathlib import Path
from typing import Any, Dict, List, Union


class OntologyValidator:
    """Validates structural and semantic correctness of OBO-JSON files."""

    @staticmethod
    def validate_file(file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Validate an OBO-JSON file against expected ontology schema rules.

        Returns:
            Dict containing:
            - 'valid': bool
            - 'errors': List[str]
            - 'warnings': List[str]
            - 'graphs_count': int
            - 'total_nodes': int
            - 'total_edges': int
            - 'doid_nodes_count': int
        """
        path = Path(file_path)
        errors: List[str] = []
        warnings: List[str] = []

        if not path.exists():
            return {
                "valid": False,
                "errors": [f"File does not exist: {path}"],
                "warnings": [],
                "graphs_count": 0,
                "total_nodes": 0,
                "total_edges": 0,
                "doid_nodes_count": 0,
            }

        if path.stat().st_size == 0:
            return {
                "valid": False,
                "errors": ["File is empty (0 bytes)"],
                "warnings": [],
                "graphs_count": 0,
                "total_nodes": 0,
                "total_edges": 0,
                "doid_nodes_count": 0,
            }

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Invalid JSON syntax: {e}"],
                "warnings": [],
                "graphs_count": 0,
                "total_nodes": 0,
                "total_edges": 0,
                "doid_nodes_count": 0,
            }

        if not isinstance(data, dict):
            errors.append("Top-level JSON element must be an object/dict")
            return {
                "valid": False,
                "errors": errors,
                "warnings": warnings,
                "graphs_count": 0,
                "total_nodes": 0,
                "total_edges": 0,
                "doid_nodes_count": 0,
            }

        graphs = data.get("graphs")
        if not isinstance(graphs, list) or len(graphs) == 0:
            errors.append("Missing or empty 'graphs' array in JSON root")
            return {
                "valid": False,
                "errors": errors,
                "warnings": warnings,
                "graphs_count": 0,
                "total_nodes": 0,
                "total_edges": 0,
                "doid_nodes_count": 0,
            }

        total_nodes = 0
        total_edges = 0
        doid_nodes_count = 0
        malformed_nodes = 0
        malformed_edges = 0

        for g_idx, graph in enumerate(graphs):
            if not isinstance(graph, dict):
                warnings.append(f"Graph index {g_idx} is not an object")
                continue

            nodes = graph.get("nodes", [])
            edges = graph.get("edges", [])

            if not isinstance(nodes, list):
                errors.append(f"Graph {g_idx} 'nodes' must be a list")
            else:
                total_nodes += len(nodes)
                for n in nodes:
                    if not isinstance(n, dict) or "id" not in n:
                        malformed_nodes += 1
                        continue
                    node_id = str(n.get("id", ""))
                    if "DOID_" in node_id:
                        doid_nodes_count += 1

            if not isinstance(edges, list):
                errors.append(f"Graph {g_idx} 'edges' must be a list")
            else:
                total_edges += len(edges)
                for e in edges:
                    if (
                        not isinstance(e, dict)
                        or "sub" not in e
                        or "pred" not in e
                        or "obj" not in e
                    ):
                        malformed_edges += 1

        if malformed_nodes > 0:
            warnings.append(f"Found {malformed_nodes} malformed node(s) missing required 'id'")
        if malformed_edges > 0:
            warnings.append(f"Found {malformed_edges} malformed edge(s) missing sub/pred/obj")

        if doid_nodes_count == 0:
            warnings.append("No DOID-prefixed nodes were identified in the dataset")

        is_valid = len(errors) == 0

        return {
            "valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "graphs_count": len(graphs),
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "doid_nodes_count": doid_nodes_count,
        }
