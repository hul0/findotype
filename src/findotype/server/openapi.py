"""OpenAPI 3.0 specification generator for the Findotype REST API."""

from typing import Any, Dict


def get_openapi_spec() -> Dict[str, Any]:
    """Generate OpenAPI 3.0.3 schema for Findotype endpoints."""
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "Findotype API",
            "description": (
                "High-performance REST API and offline medical ontology engine for the "
                "Disease Ontology (DOID), Human Phenotype Ontology (HPO), and clinical phenotype matching."
            ),
            "version": "1.0.0",
            "contact": {
                "name": "Rupam Ghosh",
                "email": "hulo@crine.in",
            },
            "license": {
                "name": "GNU AGPL-3.0-or-later",
                "url": "https://www.gnu.org/licenses/agpl-3.0.html",
            },
        },
        "servers": [
            {"url": "/", "description": "Local Findotype Server"},
        ],
        "tags": [
            {"name": "Phenotypes", "description": "Clinical symptom extraction and disease matching"},
            {"name": "Diseases", "description": "Disease lookup, multi-tiered search, and entity details"},
            {"name": "Hierarchy", "description": "Ontology parents, children, ancestors, and descendants"},
            {"name": "Knowledge Base", "description": "Metadata, dataset provenance, and database metrics"},
        ],
        "paths": {
            "/api/stats": {
                "get": {
                    "tags": ["Knowledge Base"],
                    "summary": "Get database metrics and constituent datasets",
                    "description": "Returns counts of entities, relationships, synonyms, definitions, and dataset release provenance.",
                    "responses": {
                        "200": {
                            "description": "Successful database summary",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/DatabaseStatsResponse"}
                                }
                            },
                        }
                    },
                }
            },
            "/api/search": {
                "get": {
                    "tags": ["Diseases"],
                    "summary": "Search diseases by name, synonym, CURIE, or definition",
                    "parameters": [
                        {
                            "name": "q",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "Search query text or CURIE (e.g. 'tuberculosis', 'DOID:399', 'angiosarcoma')",
                        },
                        {
                            "name": "limit",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "default": 20},
                            "description": "Maximum number of results to return",
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "List of matching diseases with rank score and match type",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/SearchResult"},
                                    }
                                }
                            },
                        },
                        "400": {"description": "Missing search query parameter 'q'"},
                    },
                }
            },
            "/api/diseases/{id}": {
                "get": {
                    "tags": ["Diseases"],
                    "summary": "Get full details of a disease entity",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "DOID CURIE, secondary ID, or numeric ID (e.g. 'DOID:0001816' or '1816')",
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Complete disease object with definition, synonyms, xrefs, and relationships",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/DiseaseDetail"}
                                }
                            },
                        },
                        "404": {"description": "Disease not found"},
                    },
                }
            },
            "/api/diseases/{id}/parents": {
                "get": {
                    "tags": ["Hierarchy"],
                    "summary": "Get direct 1-hop parent terms",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "Disease CURIE (e.g. 'DOID:0001816')",
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "List of parent hierarchy nodes",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/HierarchyNode"},
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/api/diseases/{id}/children": {
                "get": {
                    "tags": ["Hierarchy"],
                    "summary": "Get direct 1-hop child terms",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "Disease CURIE (e.g. 'DOID:175')",
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "List of child hierarchy nodes",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/HierarchyNode"},
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/api/diseases/{id}/ancestors": {
                "get": {
                    "tags": ["Hierarchy"],
                    "summary": "Get all ancestor terms up to root via recursive CTE",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "Disease CURIE (e.g. 'DOID:0001816')",
                        },
                        {
                            "name": "max_depth",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "default": 50},
                            "description": "Maximum traversal depth",
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "List of ancestor hierarchy nodes ordered by distance",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/HierarchyNode"},
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/api/diseases/{id}/descendants": {
                "get": {
                    "tags": ["Hierarchy"],
                    "summary": "Get all descendant terms down hierarchy via recursive CTE",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "Disease CURIE (e.g. 'DOID:175')",
                        },
                        {
                            "name": "max_depth",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "default": 50},
                            "description": "Maximum traversal depth",
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "List of descendant hierarchy nodes ordered by distance",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/HierarchyNode"},
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/api/diseases/{id}/relationships": {
                "get": {
                    "tags": ["Hierarchy"],
                    "summary": "Get typed graph relationships (e.g. has symptom, has material basis in)",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "Disease CURIE (e.g. 'DOID:0001816')",
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "List of directed relationships",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/Relationship"},
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/api/match": {
                "get": {
                    "tags": ["Phenotypes"],
                    "summary": "Match natural language clinical symptoms (GET)",
                    "parameters": [
                        {
                            "name": "symptoms",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "Natural language symptom text (e.g. 'I have fever, cough, nausea')",
                        },
                        {
                            "name": "limit",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "default": 10},
                            "description": "Maximum candidate diseases to return",
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "Phenotype match results with query coverage and IC",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/MatchResponse"}
                                }
                            },
                        }
                    },
                },
                "post": {
                    "tags": ["Phenotypes"],
                    "summary": "Match structured or natural language clinical symptoms (POST)",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "symptoms": {
                                            "oneOf": [
                                                {"type": "string", "example": "I have fever, cough, nausea"},
                                                {"type": "array", "items": {"type": "string"}, "example": ["HP:0001945", "cough", "nausea"]},
                                            ]
                                        },
                                        "limit": {"type": "integer", "default": 10},
                                    },
                                    "required": ["symptoms"],
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Phenotype match results with query coverage and IC",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/MatchResponse"}
                                }
                            },
                        }
                    },
                },
            },
        },
        "components": {
            "schemas": {
                "DatabaseStatsResponse": {
                    "type": "object",
                    "properties": {
                        "knowledge_base": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "schema_version": {"type": "string"},
                            },
                        },
                        "datasets": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/DatasetProvenance"},
                        },
                        "counts": {
                            "type": "object",
                            "properties": {
                                "entities": {"type": "integer"},
                                "diseases": {"type": "integer"},
                                "synonyms": {"type": "integer"},
                                "definitions": {"type": "integer"},
                                "cross_references": {"type": "integer"},
                                "relationships": {"type": "integer"},
                                "subsets": {"type": "integer"},
                                "alt_ids": {"type": "integer"},
                            },
                        },
                        "namespaces": {"type": "object", "additionalProperties": {"type": "integer"}},
                        "top_predicates": {"type": "object", "additionalProperties": {"type": "integer"}},
                        "top_xref_databases": {"type": "object", "additionalProperties": {"type": "integer"}},
                    },
                },
                "DatasetProvenance": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "version": {"type": "string", "nullable": True},
                        "release_date": {"type": "string", "nullable": True},
                        "license": {"type": "string", "nullable": True},
                        "root_term": {"type": "string", "nullable": True},
                        "source_uri": {"type": "string", "nullable": True},
                        "source_sha256": {"type": "string"},
                        "imported_at": {"type": "string"},
                    },
                },
                "SearchResult": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "match_type": {"type": "string"},
                        "matched_text": {"type": "string"},
                        "rank_score": {"type": "number"},
                        "definition": {"type": "string", "nullable": True},
                    },
                },
                "HierarchyNode": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "predicate": {"type": "string"},
                        "predicate_label": {"type": "string"},
                        "depth": {"type": "integer"},
                    },
                },
                "Relationship": {
                    "type": "object",
                    "properties": {
                        "subject_id": {"type": "string"},
                        "subject_name": {"type": "string", "nullable": True},
                        "predicate_id": {"type": "string"},
                        "predicate_label": {"type": "string"},
                        "object_id": {"type": "string"},
                        "object_name": {"type": "string", "nullable": True},
                    },
                },
                "DiseaseDetail": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "uri": {"type": "string"},
                        "namespace": {"type": "string"},
                        "is_obsolete": {"type": "boolean"},
                        "definition": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string", "nullable": True},
                                "sources": {"type": "array", "items": {"type": "string"}},
                            },
                        },
                        "synonyms": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "synonym": {"type": "string"},
                                    "scope": {"type": "string"},
                                    "type": {"type": "string", "nullable": True},
                                },
                            },
                        },
                        "cross_references": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "db": {"type": "string"},
                                    "accession": {"type": "string"},
                                    "full": {"type": "string"},
                                },
                            },
                        },
                        "subsets": {"type": "array", "items": {"type": "string"}},
                        "parents": {"type": "array", "items": {"$ref": "#/components/schemas/HierarchyNode"}},
                        "children": {"type": "array", "items": {"$ref": "#/components/schemas/HierarchyNode"}},
                        "relationships": {"type": "array", "items": {"$ref": "#/components/schemas/Relationship"}},
                    },
                },
                "MatchResponse": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "disclaimer": {"type": "string"},
                        "extracted_phenotypes": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "term_id": {"type": "string"},
                                    "term_name": {"type": "string"},
                                    "raw_text": {"type": "string"},
                                    "information_content": {"type": "number"},
                                },
                            },
                        },
                        "candidate_diseases": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "disease_id": {"type": "string"},
                                    "disease_name": {"type": "string"},
                                    "score": {"type": "number"},
                                    "query_coverage_pct": {"type": "number"},
                                    "matched_count": {"type": "integer"},
                                    "total_query_count": {"type": "integer"},
                                    "matched_phenotypes": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "string"},
                                                "name": {"type": "string"},
                                                "ic": {"type": "number"},
                                                "source": {"type": "string"},
                                            },
                                        },
                                    },
                                    "unmatched_phenotypes": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "string"},
                                                "name": {"type": "string"},
                                                "ic": {"type": "number"},
                                            },
                                        },
                                    },
                                    "definition": {"type": "string", "nullable": True},
                                },
                            },
                        },
                    },
                },
            }
        },
    }
