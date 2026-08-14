"""Data normalization routines for synonyms, cross-references, definitions, and metadata."""

import re
from typing import Any, Dict, List, Optional, Tuple

from findotype.models.disease import CrossReference, Definition, Synonym
from findotype.ontology.curie import uri_to_curie

SYNONYM_PREDICATE_MAP = {
    "hasExactSynonym": "EXACT",
    "hasNarrowSynonym": "NARROW",
    "hasBroadSynonym": "BROAD",
    "hasRelatedSynonym": "RELATED",
    "exact": "EXACT",
    "narrow": "NARROW",
    "broad": "BROAD",
    "related": "RELATED",
    "http://www.geneontology.org/formats/oboInOwl#hasExactSynonym": "EXACT",
    "http://www.geneontology.org/formats/oboInOwl#hasNarrowSynonym": "NARROW",
    "http://www.geneontology.org/formats/oboInOwl#hasBroadSynonym": "BROAD",
    "http://www.geneontology.org/formats/oboInOwl#hasRelatedSynonym": "RELATED",
}


def normalize_synonym_scope(predicate: str) -> str:
    """Normalize synonym predicate into standard scope: EXACT, NARROW, BROAD, RELATED."""
    if not predicate:
        return "RELATED"
    return SYNONYM_PREDICATE_MAP.get(predicate, "RELATED")


def parse_cross_reference(xref_raw: Any) -> Optional[CrossReference]:
    """
    Parse a raw cross-reference from doid.json (either string or dict).

    Examples:
        'MESH:D006394' -> CrossReference(db='MESH', accession='D006394', full_reference='MESH:D006394')
        'ICD10CM:A00'  -> CrossReference(db='ICD10CM', accession='A00', full_reference='ICD10CM:A00')
        'url:https://...' -> CrossReference(db='url', accession='https://...', full_reference='url:https://...')
        {'val': 'NCI:C3088'} -> CrossReference(db='NCI', accession='C3088', full_reference='NCI:C3088')
    """
    if isinstance(xref_raw, dict):
        raw_val = xref_raw.get("val", "")
    elif isinstance(xref_raw, str):
        raw_val = xref_raw
    else:
        return None

    raw_val = raw_val.strip()
    if not raw_val:
        return None

    if ":" in raw_val:
        db, accession = raw_val.split(":", 1)
        db = db.strip()
        accession = accession.strip()
        if not db or not accession:
            return None
        return CrossReference(db=db, accession=accession, full_reference=raw_val)

    return CrossReference(db="OTHER", accession=raw_val, full_reference=raw_val)


def parse_definition(def_raw: Any) -> Optional[Definition]:
    """
    Parse a definition object or string from doid.json.

    Examples:
        {'val': 'A cancer...', 'xrefs': ['url:http...']}
        'A cancer...'
    """
    if not def_raw:
        return None

    if isinstance(def_raw, str):
        val = def_raw.strip()
        return Definition(definition=val, sources=[]) if val else None

    if isinstance(def_raw, dict):
        val = def_raw.get("val", "").strip()
        if not val:
            return None
        raw_xrefs = def_raw.get("xrefs", [])
        sources = []
        if isinstance(raw_xrefs, list):
            for x in raw_xrefs:
                if isinstance(x, str) and x.strip():
                    sources.append(x.strip())
                elif isinstance(x, dict) and x.get("val"):
                    sources.append(str(x.get("val")).strip())
        return Definition(definition=val, sources=sources)

    return None


def parse_synonyms(syn_list: Any) -> List[Synonym]:
    """
    Parse the synonym list from a node meta object.
    """
    if not isinstance(syn_list, list):
        return []

    synonyms: List[Synonym] = []
    seen = set()

    for item in syn_list:
        if not isinstance(item, dict):
            continue

        val = item.get("val", "").strip()
        if not val:
            continue

        scope = normalize_synonym_scope(item.get("pred", ""))
        syn_type = item.get("synonymType")
        xrefs_raw = item.get("xrefs", [])
        xrefs = [x.strip() for x in xrefs_raw if isinstance(x, str) and x.strip()]

        key = (val.lower(), scope)
        if key in seen:
            continue
        seen.add(key)

        synonyms.append(
            Synonym(
                synonym=val,
                scope=scope,
                synonym_type=syn_type,
                xrefs=xrefs,
            )
        )

    return synonyms


def parse_subsets(subset_list: Any) -> List[str]:
    """
    Parse subset names from subset URI list.
    """
    if not isinstance(subset_list, list):
        return []

    subsets = []
    for item in subset_list:
        if isinstance(item, str) and item.strip():
            curie = uri_to_curie(item.strip())
            subsets.append(curie)
    return subsets


def parse_alt_ids(basic_props: Any) -> List[str]:
    """
    Extract alternative merged IDs (oboInOwl#hasAlternativeId) from basicPropertyValues.
    """
    if not isinstance(basic_props, list):
        return []

    alt_ids = []
    for prop in basic_props:
        if not isinstance(prop, dict):
            continue
        pred = prop.get("pred", "")
        if "hasAlternativeId" in pred:
            val = prop.get("val", "").strip()
            if val:
                alt_ids.append(val)
    return alt_ids
