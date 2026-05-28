"""Generate migration manifest combining inventory, dependencies, and complexity.

Produces a single analysis_output/migration_manifest.json file that the
dashboard and conversion scripts consume.
"""
import json
import os
import sys
from datetime import datetime, timezone


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_manifest.py <analysis_output_dir>")
        sys.exit(1)

    output_dir = sys.argv[1]

    # Load all analysis outputs
    required_files = ["job_inventory.json", "dependency_graph.json", "complexity_report.json"]
    data = {}
    for fname in required_files:
        fpath = os.path.join(output_dir, fname)
        if not os.path.exists(fpath):
            print(f"Error: {fpath} not found. Run prior analysis scripts first.")
            sys.exit(1)
        with open(fpath) as f:
            data[fname.replace(".json", "")] = json.load(f)

    inventory = data["job_inventory"]
    graph = data["dependency_graph"]
    complexity = data["complexity_report"]

    # Build component distribution
    component_counts = {}
    for job in inventory:
        for node in job["nodes"]:
            comp = node["component_name"]
            component_counts[comp] = component_counts.get(comp, 0) + 1

    # Build per-job manifest entries
    complexity_lookup = {
        (r["domain"], r["job_name"]): r for r in complexity["jobs"]
    }

    manifest_jobs = []
    for job in inventory:
        key = (job["domain"], job["job_name"])
        cx = complexity_lookup.get(key, {})

        # Determine target tables
        target_tables = []
        for node in job["nodes"]:
            table = node.get("parameters", {}).get("TABLE", "").strip('"')
            if table and ("Output" in node["component_name"] or "DBOutput" in node["component_name"]):
                target_tables.append(table)

        manifest_jobs.append({
            "job_name": job["job_name"],
            "domain": job["domain"],
            "components": [
                {"name": n["unique_name"], "type": n["component_name"]}
                for n in job["nodes"]
            ],
            "connections": job["connections"],
            "routines_used": job.get("routines", []),
            "target_tables": target_tables,
            "complexity": {
                "score": cx.get("complexity_score", 0),
                "tier": cx.get("tier", "UNKNOWN"),
                "effort_hours": cx.get("effort_hours", 0),
                "factors": cx.get("factors", []),
            },
            "conversion_status": "NOT_STARTED",
            "converted_file": None,
            "test_file": None,
        })

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_platform": "Talend Open Studio / Talend Data Integration",
        "target_platform": "Python 3.11 + Snowpark for Snowflake",
        "jobs": manifest_jobs,
        "dependency_graph": {
            "edges": graph["edges"],
            "shared_contexts": graph.get("shared_contexts", {}),
            "custom_routine_usage": graph.get("custom_routine_usage", {}),
        },
        "component_distribution": dict(
            sorted(component_counts.items(), key=lambda x: -x[1])
        ),
        "summary": {
            "total_jobs": len(manifest_jobs),
            "domains": sorted(set(j["domain"] for j in manifest_jobs)),
            "tier_distribution": complexity["summary"]["tier_distribution"],
            "total_effort_hours": complexity["summary"]["total_effort_hours"],
            "total_components": sum(len(j["components"]) for j in manifest_jobs),
            "total_connections": sum(len(j["connections"]) for j in manifest_jobs),
            "unique_tables": sorted(set(
                t for j in manifest_jobs for t in j["target_tables"]
            )),
        },
    }

    output_path = os.path.join(output_dir, "migration_manifest.json")
    with open(output_path, "w") as f:
        json.dump(manifest, f, indent=2)

    s = manifest["summary"]
    print("Migration Manifest Generated")
    print(f"  Jobs: {s['total_jobs']} across {len(s['domains'])} domains")
    print(f"  Components: {s['total_components']} total")
    print(f"  Distribution: {manifest['component_distribution']}")
    print(f"  Tiers: {s['tier_distribution']}")
    print(f"  Estimated effort: {s['total_effort_hours']}h")
    print(f"  Target tables: {', '.join(s['unique_tables'])}")
    print(f"\n→ {output_path}")


if __name__ == "__main__":
    main()
