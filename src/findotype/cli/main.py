"""CLI interface for Findotype Disease Ontology toolkit."""

import argparse
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any, List, Optional

from findotype.config import DEFAULT_DB_PATH, DEFAULT_DOID_URL
from findotype.models.disease import Disease
from findotype.models.search import SearchResult
from findotype.services.ontology_service import Findotype


def _format_size(num_bytes: int) -> str:
    """Format bytes into human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:3.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} TB"


def cmd_download(args) -> int:
    """Download the latest Disease Ontology dataset."""
    dest_path = Path(args.output)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    url = args.url or DEFAULT_DOID_URL

    if not args.json:
        print(f"Downloading Disease Ontology from {url}...")
        print(f"Destination: {dest_path.resolve()}")

    try:
        # Standard library download with user-agent
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Findotype/0.1.0 (offline disease ontology backend)"},
        )
        with urllib.request.urlopen(req) as response, open(dest_path, "wb") as out_file:
            total_size = int(response.info().get("Content-Length", 0))
            downloaded = 0
            block_size = 65536

            while True:
                buffer = response.read(block_size)
                if not buffer:
                    break
                downloaded += len(buffer)
                out_file.write(buffer)
                if not args.json and total_size > 0:
                    percent = downloaded * 100 / total_size
                    sys.stdout.write(f"\rProgress: {percent:5.1f}% ({_format_size(downloaded)})")
                    sys.stdout.flush()

        if not args.json:
            print(f"\nDownload complete! File saved: {dest_path.resolve()} ({_format_size(dest_path.stat().st_size)})")
        else:
            print(json.dumps({
                "status": "success",
                "source_url": url,
                "output_path": str(dest_path.resolve()),
                "size_bytes": dest_path.stat().st_size,
            }))
        return 0
    except Exception as e:
        if args.json:
            print(json.dumps({"status": "error", "error": str(e)}))
        else:
            print(f"\nError downloading dataset: {e}", file=sys.stderr)
        return 1


def cmd_validate(args) -> int:
    """Validate a doid.json dataset file."""
    file_path = Path(args.file)
    result = Findotype.validate_doid(file_path)

    if args.json:
        print(json.dumps(result, indent=2))
        return 0 if result.get("valid") else 1

    print(f"\n{'='*60}")
    print(f"Validation Report: {file_path.name}")
    print(f"{'='*60}")
    status_str = "VALID [OK]" if result["valid"] else "INVALID [FAILED]"
    print(f"Status:          {status_str}")
    print(f"Graphs Found:    {result['graphs_count']}")
    print(f"Total Nodes:     {result['total_nodes']:,}")
    print(f"Total Edges:     {result['total_edges']:,}")
    print(f"DOID Nodes:      {result['doid_nodes_count']:,}")

    if result.get("errors"):
        print(f"\nErrors ({len(result['errors'])}):")
        for err in result["errors"]:
            print(f"  - [ERROR] {err}")

    if result.get("warnings"):
        print(f"\nWarnings ({len(result['warnings'])}):")
        for warn in result["warnings"]:
            print(f"  - [WARN]  {warn}")

    print(f"{'='*60}\n")
    return 0 if result["valid"] else 1


def cmd_import(args) -> int:
    """Import a doid.json dataset into the SQLite database."""
    file_path = Path(args.file)
    db_path = Path(args.db)

    if not args.json:
        print(f"\n{'='*60}")
        print(f"Importing Disease Ontology into SQLite")
        print(f"{'='*60}")
        print(f"Source file:       {file_path.resolve()}")
        print(f"Target SQLite DB:  {db_path.resolve()}")
        print(f"Include Obsolete:  {args.include_obsolete}")
        print("Parsing and ingesting dataset inside atomic transaction...")

    try:
        engine = Findotype(db_path=db_path)
        stats = engine.import_doid(
            file_path=file_path,
            include_obsolete=args.include_obsolete,
        )
        engine.close()

        if args.json:
            print(json.dumps({
                "status": "success",
                "entities_count": stats.entities_count,
                "diseases_count": stats.diseases_count,
                "synonyms_count": stats.synonyms_count,
                "definitions_count": stats.definitions_count,
                "xrefs_count": stats.xrefs_count,
                "relationships_count": stats.relationships_count,
                "subsets_count": stats.subsets_count,
                "alt_ids_count": stats.alt_ids_count,
                "obsolete_skipped": stats.obsolete_skipped,
                "duration_seconds": stats.duration_seconds,
            }, indent=2))
        else:
            print(f"\nImport Completed Successfully in {stats.duration_seconds:.2f}s!")
            print(f"  - Ingested Entities:      {stats.entities_count:,}")
            print(f"  - Primary DOID Diseases:  {stats.diseases_count:,}")
            print(f"  - Synonyms:               {stats.synonyms_count:,}")
            print(f"  - Definitions:            {stats.definitions_count:,}")
            print(f"  - Cross-References:       {stats.xrefs_count:,}")
            print(f"  - Relationships:          {stats.relationships_count:,}")
            print(f"  - Subsets / Slims:        {stats.subsets_count:,}")
            print(f"  - Alternative/Merged IDs: {stats.alt_ids_count:,}")
            if stats.obsolete_skipped > 0:
                print(f"  - Obsolete terms omitted: {stats.obsolete_skipped:,}")
            print(f"{'='*60}\n")
        return 0
    except Exception as e:
        if args.json:
            print(json.dumps({"status": "error", "error": str(e)}))
        else:
            print(f"\n[ERROR] Import failed: {e}", file=sys.stderr)
        return 1


def cmd_stats(args) -> int:
    """Display database statistics and provenance."""
    db_path = Path(args.db)
    if not db_path.exists():
        if args.json:
            print(json.dumps({"error": f"Database file not found: {db_path}"}))
        else:
            print(f"Database not found: {db_path}", file=sys.stderr)
        return 1

    with Findotype(db_path=db_path) as engine:
        stats = engine.get_stats()
        prov = engine.get_provenance()
        meta = engine.get_metadata()

    if args.json:
        data = {
            "database": str(db_path.resolve()),
            "size_bytes": stats.db_size_bytes,
            "provenance": {
                "dataset_name": prov.dataset_name if prov else None,
                "version": prov.dataset_version if prov else None,
                "source_uri": prov.source_uri if prov else None,
                "source_sha256": prov.source_sha256 if prov else None,
                "schema_version": prov.schema_version if prov else None,
                "imported_at": prov.imported_at if prov else None,
            },
            "metadata": {
                "title": meta.title,
                "description": meta.description,
                "license": meta.license,
                "root_term": meta.root_term,
            },
            "counts": {
                "entities": stats.total_entities,
                "diseases": stats.total_diseases,
                "synonyms": stats.total_synonyms,
                "definitions": stats.total_definitions,
                "cross_references": stats.total_xrefs,
                "relationships": stats.total_relationships,
                "subsets": stats.total_subsets,
                "alt_ids": stats.total_alt_ids,
            },
            "namespaces": stats.entity_namespaces,
            "top_predicates": stats.top_predicates,
            "top_xref_databases": stats.top_xref_databases,
        }
        print(json.dumps(data, indent=2))
        return 0

    print(f"\n{'='*65}")
    print(f"Findotype Database Summary: {db_path.name} ({_format_size(stats.db_size_bytes)})")
    print(f"{'='*65}")

    if prov:
        print(f"Dataset Name:     {prov.dataset_name}")
        print(f"Dataset Version:  {prov.dataset_version or 'N/A'}")
        print(f"Release Date:     {meta.date or 'N/A'}")
        print(f"License:          {meta.license or 'CC0 1.0 Universal'}")
        print(f"Source SHA-256:   {prov.source_sha256[:16]}...{prov.source_sha256[-8:]}")
        print(f"Imported At:      {prov.imported_at}")
        print(f"Schema Version:   {prov.schema_version}")
        print(f"Root Term:        {meta.root_term or 'DOID:4'}")
        print("-" * 65)

    print("TABLE METRICS:")
    print(f"  - Total Entities:         {stats.total_entities:,}")
    print(f"  - Primary DOID Diseases:  {stats.total_diseases:,}")
    print(f"  - Synonyms:               {stats.total_synonyms:,}")
    print(f"  - Definitions:            {stats.total_definitions:,}")
    print(f"  - Cross-References:       {stats.total_xrefs:,}")
    print(f"  - Graph Relationships:    {stats.total_relationships:,}")
    print(f"  - Subsets / Slims:        {stats.total_subsets:,}")
    print(f"  - Merged / Alt IDs:       {stats.total_alt_ids:,}")

    print("\nENTITY BREAKDOWN BY NAMESPACE:")
    for ns, count in sorted(stats.entity_namespaces.items(), key=lambda x: x[1], reverse=True)[:8]:
        print(f"  {ns:<12} : {count:>7,}")

    print("\nTOP RELATIONSHIP PREDICATES:")
    for pred, count in sorted(stats.top_predicates.items(), key=lambda x: x[1], reverse=True)[:6]:
        print(f"  {pred:<30} : {count:>7,}")

    print("\nTOP CROSS-REFERENCE DATABASES:")
    for db_name, count in sorted(stats.top_xref_databases.items(), key=lambda x: x[1], reverse=True)[:6]:
        print(f"  {db_name:<20} : {count:>7,}")

    print(f"{'='*65}\n")
    return 0


def cmd_search(args) -> int:
    """Search diseases in the SQLite database."""
    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Database file not found: {db_path}", file=sys.stderr)
        return 1

    with Findotype(db_path=db_path) as engine:
        results = engine.search_diseases(args.query, limit=args.limit)

    if args.json:
        data = [
            {
                "id": r.id,
                "name": r.name,
                "match_type": r.match_type.value,
                "matched_text": r.matched_text,
                "rank_score": r.rank_score,
                "definition": r.definition,
            }
            for r in results
        ]
        print(json.dumps(data, indent=2))
        return 0

    print(f"\nSearch results for: \"{args.query}\" ({len(results)} matches)")
    print("-" * 80)
    if not results:
        print("No matching diseases found.")
        print("-" * 80 + "\n")
        return 0

    for idx, r in enumerate(results, 1):
        print(f"{idx:2d}. [{r.id}] {r.name}")
        print(f"    Match Type: {r.match_type.value} | Matched: {r.matched_text}")
        if r.definition:
            short_def = r.definition[:100] + "..." if len(r.definition) > 100 else r.definition
            print(f"    Definition: {short_def}")
        print()

    print("-" * 80 + "\n")
    return 0


def cmd_inspect(args) -> int:
    """Inspect complete details for a specific DOID."""
    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Database file not found: {db_path}", file=sys.stderr)
        return 1

    with Findotype(db_path=db_path) as engine:
        disease = engine.get_disease(args.doid)
        if not disease:
            if args.json:
                print(json.dumps({"error": f"Disease not found: {args.doid}"}))
            else:
                print(f"Disease not found: {args.doid}", file=sys.stderr)
            return 1

        parents = engine.get_parents(disease.id)
        children = engine.get_children(disease.id)
        relationships = engine.get_relationships(disease.id)

    if args.json:
        data = {
            "id": disease.id,
            "name": disease.name,
            "uri": disease.uri,
            "namespace": disease.namespace,
            "entity_type": disease.entity_type,
            "is_obsolete": disease.is_obsolete,
            "comment": disease.comment,
            "definition": {
                "text": disease.definition.definition if disease.definition else None,
                "sources": disease.definition.sources if disease.definition else [],
            },
            "synonyms": [
                {
                    "synonym": s.synonym,
                    "scope": s.scope,
                    "type": s.synonym_type,
                    "xrefs": s.xrefs,
                }
                for s in disease.synonyms
            ],
            "cross_references": [
                {"db": x.db, "accession": x.accession, "full": x.full_reference}
                for x in disease.cross_references
            ],
            "subsets": [s.name for s in disease.subsets],
            "alt_ids": disease.alt_ids,
            "parents": [{"id": p.id, "name": p.name, "predicate": p.predicate_label} for p in parents],
            "children": [{"id": c.id, "name": c.name, "predicate": c.predicate_label} for c in children],
            "relationships": [
                {
                    "subject_id": r.subject_id,
                    "subject_name": r.subject_name,
                    "predicate": r.predicate_label,
                    "object_id": r.object_id,
                    "object_name": r.object_name,
                }
                for r in relationships
            ],
        }
        print(json.dumps(data, indent=2))
        return 0

    print(f"\n{'='*75}")
    print(f"Disease: [{disease.id}] {disease.name}")
    print(f"{'='*75}")
    print(f"URI:         {disease.uri}")
    print(f"Namespace:   {disease.namespace}")
    print(f"Obsolete:    {'YES' if disease.is_obsolete else 'No'}")
    if disease.alt_ids:
        print(f"Alt IDs:     {', '.join(disease.alt_ids)}")
    if disease.subsets:
        print(f"Subsets:     {', '.join(s.name for s in disease.subsets)}")

    if disease.definition:
        print(f"\nDEFINITION:")
        print(f"  {disease.definition.definition}")
        if disease.definition.sources:
            print(f"  Sources: {', '.join(disease.definition.sources)}")

    if disease.synonyms:
        print(f"\nSYNONYMS ({len(disease.synonyms)}):")
        for s in disease.synonyms:
            print(f"  - [{s.scope:<7}] {s.synonym}")

    if disease.cross_references:
        print(f"\nCROSS REFERENCES ({len(disease.cross_references)}):")
        for x in disease.cross_references[:15]:
            print(f"  - {x.full_reference}")
        if len(disease.cross_references) > 15:
            print(f"  ... and {len(disease.cross_references) - 15} more")

    if parents:
        print(f"\nPARENTS (Direct Superclasses):")
        for p in parents:
            print(f"  -> [{p.id}] {p.name}")

    if children:
        print(f"\nCHILDREN (Direct Subclasses - {len(children)}):")
        for c in children[:10]:
            print(f"  <- [{c.id}] {c.name}")
        if len(children) > 10:
            print(f"  ... and {len(children) - 10} more")

    other_rels = [r for r in relationships if r.predicate_id != "is_a"]
    if other_rels:
        print(f"\nOTHER ONTOLOGY RELATIONSHIPS ({len(other_rels)}):")
        for r in other_rels[:10]:
            if r.subject_id == disease.id:
                print(f"  --[{r.predicate_label}]--> [{r.object_id}] {r.object_name}")
            else:
                print(f"  <--[{r.predicate_label}]-- [{r.subject_id}] {r.subject_name}")
        if len(other_rels) > 10:
            print(f"  ... and {len(other_rels) - 10} more")

    print(f"{'='*75}\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build command line argument parser."""
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    parser = argparse.ArgumentParser(
        prog="findotype",
        description="Findotype: High-Performance Offline Disease Ontology Backend & SQLite Engine",
        parents=[common_parser],
    )

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # download
    p_down = subparsers.add_parser("download", parents=[common_parser], help="Download the latest Disease Ontology dataset")
    p_down.add_argument("-o", "--output", default="assets/DO/doid.json", help="Output destination path")
    p_down.add_argument("--url", default=DEFAULT_DOID_URL, help="Custom download URL")

    # validate
    p_val = subparsers.add_parser("validate", parents=[common_parser], help="Validate a doid.json file structure")
    p_val.add_argument("file", help="Path to doid.json")

    # import
    p_imp = subparsers.add_parser("import", parents=[common_parser], help="Import doid.json into SQLite database")
    p_imp.add_argument("file", help="Path to doid.json")
    p_imp.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Target SQLite database path")
    p_imp.add_argument("--include-obsolete", action="store_true", help="Include deprecated/obsolete terms")

    # stats
    p_stat = subparsers.add_parser("stats", parents=[common_parser], help="Show database summary statistics and provenance")
    p_stat.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Path to SQLite database")

    # search
    p_search = subparsers.add_parser("search", parents=[common_parser], help="Search diseases by text, synonym, or partial term")
    p_search.add_argument("query", help="Search query string")
    p_search.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Path to SQLite database")
    p_search.add_argument("-n", "--limit", type=int, default=20, help="Maximum number of results")

    # inspect
    p_insp = subparsers.add_parser("inspect", parents=[common_parser], help="Inspect a specific DOID term in detail")
    p_insp.add_argument("doid", help="Disease identifier (e.g. DOID:0001816 or 0001816)")
    p_insp.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Path to SQLite database")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """CLI main entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    commands = {
        "download": cmd_download,
        "validate": cmd_validate,
        "import": cmd_import,
        "stats": cmd_stats,
        "search": cmd_search,
        "inspect": cmd_inspect,
    }

    cmd_fn = commands.get(args.command)
    if cmd_fn:
        return cmd_fn(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
