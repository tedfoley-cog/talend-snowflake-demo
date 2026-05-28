"""Build job dependency map from parsed Talend inventory.

Analyzes shared tables, contexts, and routine references to infer
job-to-job dependencies. Produces analysis_output/dependency_graph.json.
"""
import json
import os
import re
import sys


def extract_table_refs(job: dict) -> tuple:
    """Extract source and target table names from a job's nodes."""
    sources = set()
    targets = set()
    for node in job["nodes"]:
        comp = node["component_name"]
        params = node.get("parameters", {})
        table = params.get("TABLE", "").strip('"')

        if not table:
            query = params.get("QUERY", "")
            from_tables = re.findall(r'FROM\s+(\w+)', query, re.IGNORECASE)
            join_tables = re.findall(r'JOIN\s+(\w+)', query, re.IGNORECASE)
            sources.update(t for t in from_tables + join_tables if t.upper() != "DUAL")

        if "Input" in comp or "DBInput" in comp.replace("t", "", 1) or comp == "tDBInput":
            if table:
                sources.add(table)
        elif "Output" in comp or "DBOutput" in comp.replace("t", "", 1) or comp == "tDBOutput":
            if table:
                targets.add(table)
        elif comp == "tDBRow":
            query = params.get("QUERY", "")
            update_tables = re.findall(r'UPDATE\s+(\w+)', query, re.IGNORECASE)
            insert_tables = re.findall(r'INSERT\s+INTO\s+(\w+)', query, re.IGNORECASE)
            targets.update(update_tables + insert_tables)

    return sources, targets


def build_graph(inventory: list) -> dict:
    """Build dependency graph based on shared table references."""
    table_producers = {}
    table_consumers = {}

    for job in inventory:
        sources, targets = extract_table_refs(job)
        job_key = f"{job['domain']}/{job['job_name']}"
        for t in targets:
            table_producers.setdefault(t, []).append(job_key)
        for s in sources:
            table_consumers.setdefault(s, []).append(job_key)

    edges = []
    for table, producers in table_producers.items():
        consumers = table_consumers.get(table, [])
        for prod in producers:
            for cons in consumers:
                if prod != cons:
                    edges.append({
                        "from": prod,
                        "to": cons,
                        "via_table": table,
                        "relationship": "produces_for",
                    })

    # Shared context dependencies
    context_groups = {}
    for job in inventory:
        job_key = f"{job['domain']}/{job['job_name']}"
        for ctx in job.get("contexts", []):
            for param in ctx.get("parameters", []):
                param_name = param["name"]
                context_groups.setdefault(param_name, []).append(job_key)

    shared_contexts = {k: v for k, v in context_groups.items() if len(v) > 1}

    # Shared routine dependencies
    routine_groups = {}
    for job in inventory:
        job_key = f"{job['domain']}/{job['job_name']}"
        for routine in job.get("routines", []):
            routine_groups.setdefault(routine, []).append(job_key)

    custom_routines = {k: v for k, v in routine_groups.items()
                       if k not in ("DataOperation", "Numeric", "StringHandling",
                                    "TalendDate", "TalendString", "TalendStringUtil")}

    nodes = []
    for job in inventory:
        job_key = f"{job['domain']}/{job['job_name']}"
        _, targets = extract_table_refs(job)
        sources, _ = extract_table_refs(job)
        nodes.append({
            "id": job_key,
            "domain": job["domain"],
            "job_name": job["job_name"],
            "reads_from": sorted(sources),
            "writes_to": sorted(targets),
            "routines": job.get("routines", []),
        })

    return {
        "nodes": nodes,
        "edges": edges,
        "shared_contexts": shared_contexts,
        "custom_routine_usage": custom_routines,
        "summary": {
            "total_jobs": len(inventory),
            "total_edges": len(edges),
            "tables_referenced": sorted(set(table_producers.keys()) | set(table_consumers.keys())),
        },
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python build_dependency_graph.py <analysis_output_dir>")
        sys.exit(1)

    output_dir = sys.argv[1]
    inventory_path = os.path.join(output_dir, "job_inventory.json")

    if not os.path.exists(inventory_path):
        print(f"Error: {inventory_path} not found. Run parse_talend_xml.py first.")
        sys.exit(1)

    with open(inventory_path) as f:
        inventory = json.load(f)

    graph = build_graph(inventory)

    output_path = os.path.join(output_dir, "dependency_graph.json")
    with open(output_path, "w") as f:
        json.dump(graph, f, indent=2)

    print(f"Dependency graph: {len(graph['nodes'])} jobs, {len(graph['edges'])} edges")
    for edge in graph["edges"]:
        print(f"  {edge['from']} → {edge['to']} (via {edge['via_table']})")
    print("\nShared custom routines:")
    for routine, jobs in graph["custom_routine_usage"].items():
        print(f"  {routine}: {', '.join(jobs)}")
    print(f"\n→ {output_path}")


if __name__ == "__main__":
    main()
