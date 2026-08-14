"""Bidirectional URI <-> CURIE converter and ontology namespace handling."""



OBO_BASE = "http://purl.obolibrary.org/obo/"
W3C_RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
W3C_RDFS = "http://www.w3.org/2000/01/rdf-schema#"
W3C_OWL = "http://www.w3.org/2002/07/owl#"
DC_ELEMENTS = "http://purl.org/dc/elements/1.1/"
DC_TERMS = "http://purl.org/dc/terms/"
OBO_IN_OWL = "http://www.geneontology.org/formats/oboInOwl#"
SKOS = "http://www.w3.org/2004/02/skos/core#"

PREFIX_MAP = {
    OBO_BASE: "",
    W3C_RDF: "rdf:",
    W3C_RDFS: "rdfs:",
    W3C_OWL: "owl:",
    DC_ELEMENTS: "dc:",
    DC_TERMS: "dcterms:",
    OBO_IN_OWL: "oboInOwl:",
    SKOS: "skos:",
}


def uri_to_curie(uri: str) -> str:
    """
    Convert a full URI into a normalized compact URI (CURIE) or identifier.

    Examples:
        'http://purl.obolibrary.org/obo/DOID_0001816' -> 'DOID:0001816'
        'http://purl.obolibrary.org/obo/CHEBI_15365'   -> 'CHEBI:15365'
        'is_a'                                       -> 'is_a'
        'http://purl.obolibrary.org/obo/doid#DO_cancer_slim' -> 'DO_cancer_slim'
    """
    if not uri:
        return ""

    if uri == "is_a" or uri == "subClassOf":
        return "is_a"

    # Handle standard OBO purls: http://purl.obolibrary.org/obo/PREFIX_LOCAL
    if uri.startswith(OBO_BASE):
        local_part = uri[len(OBO_BASE):]
        # Check for doid#subset or hash syntax
        if "#" in local_part:
            return local_part.split("#", 1)[1]
        # Standard OBO CURIE with underscore: PREFIX_12345
        if "_" in local_part:
            prefix, local = local_part.split("_", 1)
            # Ensure prefix is uppercase for standard ontologies
            return f"{prefix}:{local}"
        return local_part

    # Handle other namespace mappings
    for base_uri, prefix in PREFIX_MAP.items():
        if uri.startswith(base_uri):
            local_part = uri[len(base_uri):]
            return f"{prefix}{local_part}"

    # Handle generic hash/slash URLs
    if "#" in uri:
        return uri.split("#")[-1]
    if "/" in uri and not uri.startswith("http"):
        return uri.split("/")[-1]

    return uri


def curie_to_uri(curie: str) -> str:
    """
    Convert a CURIE back into its canonical OBO / W3C URI where possible.

    Examples:
        'DOID:0001816' -> 'http://purl.obolibrary.org/obo/DOID_0001816'
        'CHEBI:15365'  -> 'http://purl.obolibrary.org/obo/CHEBI_15365'
    """
    if not curie:
        return ""

    if curie.startswith("http://") or curie.startswith("https://"):
        return curie

    if curie == "is_a":
        return "http://www.w3.org/2000/01/rdf-schema#subClassOf"

    if ":" in curie:
        prefix, local = curie.split(":", 1)
        if prefix in ("rdf", "rdfs", "owl", "dc", "dcterms", "oboInOwl", "skos"):
            # Lookup in reverse map
            for base_uri, mapped_prefix in PREFIX_MAP.items():
                if mapped_prefix == f"{prefix}:":
                    return f"{base_uri}{local}"
        # Standard OBO prefix
        return f"{OBO_BASE}{prefix}_{local}"

    return f"{OBO_BASE}{curie}"


def extract_namespace(curie_or_uri: str) -> str:
    """
    Extract the ontology namespace / prefix from a CURIE or URI.

    Examples:
        'DOID:0001816' -> 'DOID'
        'CHEBI:15365'  -> 'CHEBI'
        'is_a'         -> 'rdfs'
    """
    if not curie_or_uri:
        return "UNKNOWN"

    curie = uri_to_curie(curie_or_uri)
    if curie == "is_a":
        return "rdfs"

    if ":" in curie:
        return curie.split(":", 1)[0]

    return "UNKNOWN"


def normalize_identifier(identifier: str) -> str:
    """
    Normalize various user-input formats into a canonical CURIE.

    Examples:
        'doid:0001816' -> 'DOID:0001816'
        'DOID_0001816' -> 'DOID:0001816'
        '0001816'      -> 'DOID:0001816'
        '4'            -> 'DOID:4'
    """
    cleaned = identifier.strip()
    if cleaned.startswith("http://") or cleaned.startswith("https://"):
        return uri_to_curie(cleaned)

    # Check for DOID_123 or doid:123
    cleaned = cleaned.replace("_", ":")
    if ":" in cleaned:
        prefix, local = cleaned.split(":", 1)
        return f"{prefix.upper()}:{local}"

    # If purely numeric, default to DOID
    if cleaned.isdigit():
        return f"DOID:{cleaned}"

    return cleaned
