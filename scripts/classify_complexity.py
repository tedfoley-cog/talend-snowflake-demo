"""Classify Talend jobs by migration complexity.

Scoring factors:
  - Component count
  - tMap expression complexity (string operations, conditionals, custom routine calls)
  - Number of input/output tables in tMap (joins)
  - Use of custom routines
  - Multiple output flows (reject handling)
  - Context parameter count

Tiers:
  - STRAIGHTFORWARD: score < 30  (direct mappings, simple flows)
  - MODERATE: score 30-60        (some transforms, joins, routine calls)
  - COMPLEX: score > 60          (multi-join tMaps, complex expressions, SCD logic)

Produces analysis_output/complexity_report.json.
"""
import json
import os
import re
import sys


def score_expression(expr: str) -> int:
    """Score a tMap expression by complexity."""
    score = 0
    if "?" in expr and ":" in expr:
        score += 5  # ternary conditional
        score += expr.count("?") * 3  # nested ternaries
    if ".replaceAll(" in expr or ".replace(" in expr:
        score += 3
    if ".substring(" in expr:
        score += 2
    if ".contains(" in expr or ".matches(" in expr:
        score += 3
    if "&&" in expr or "||" in expr:
        score += 2 * (expr.count("&&") + expr.count("||"))
    if re.search(r'[A-Z][a-zA-Z]+\.\w+\(', expr):
        score += 4  # custom routine call
    if "Math." in expr:
        score += 3
    if "Integer.parseInt" in expr or "(int)" in expr or "(double)" in expr:
        score += 2
    score += max(0, len(expr) // 80 - 1)  # long expressions
    return score


def classify_job(job: dict) -> dict:
    """Classify a single job by complexity."""
    score = 0
    factors = []

    # Component count
    comp_count = job["component_count"]
    if comp_count >= 5:
        score += 10
        factors.append(f"{comp_count} components")
    elif comp_count >= 3:
        score += 5

    # Connection count
    conn_count = job["connection_count"]
    if conn_count >= 4:
        score += 10
        factors.append(f"{conn_count} connections (multi-flow)")

    # tMap expression complexity
    total_expr_score = 0
    expr_count = 0
    for node in job["nodes"]:
        if node["component_name"] == "tMap":
            for expr_info in node.get("tmap_expressions", []):
                expr_score = score_expression(expr_info["expression"])
                total_expr_score += expr_score
                expr_count += 1

    if total_expr_score > 30:
        score += 25
        factors.append(f"Complex tMap expressions (score={total_expr_score})")
    elif total_expr_score > 15:
        score += 15
        factors.append(f"Moderate tMap expressions (score={total_expr_score})")
    elif total_expr_score > 0:
        score += 5

    # Number of output schemas on tMap (multiple = reject handling)
    for node in job["nodes"]:
        if node["component_name"] == "tMap":
            out_schemas = [s for s in node.get("schemas", []) if s["connector"] == "FLOW"]
            if len(out_schemas) > 1:
                score += 15
                factors.append(f"tMap has {len(out_schemas)} output flows (split/reject)")

    # Input table count (joins)
    for node in job["nodes"]:
        if node["component_name"] == "tMap":
            input_count = sum(1 for e in node.get("tmap_expressions", [])
                              if e.get("output_table") == "__var__" or "row2" in e.get("expression", "") or "row3" in e.get("expression", ""))
            if input_count > 0:
                join_sources = len(set(
                    conn["source"] for conn in job["connections"]
                    if conn["target"] == node["unique_name"]
                ))
                if join_sources > 1:
                    score += 10 * (join_sources - 1)
                    factors.append(f"tMap joins {join_sources} input sources")

    # Custom routine usage
    custom = [r for r in job.get("routines", [])
              if r not in ("DataOperation", "Numeric", "StringHandling",
                           "TalendDate", "TalendString", "TalendStringUtil")]
    if custom:
        score += 8 * len(custom)
        factors.append(f"Custom routines: {', '.join(custom)}")

    # Context parameter count
    ctx_params = sum(len(c.get("parameters", [])) for c in job.get("contexts", []))
    if ctx_params > 5:
        score += 5
        factors.append(f"{ctx_params} context parameters")

    # tDBRow (dynamic SQL)
    for node in job["nodes"]:
        if node["component_name"] == "tDBRow":
            score += 10
            factors.append("Uses tDBRow (dynamic SQL execution)")

    # Multiple DB types
    db_versions = set()
    for node in job["nodes"]:
        db = node.get("parameters", {}).get("DB_VERSION", "")
        if db:
            db_versions.add(db)
    if len(db_versions) > 1:
        score += 10
        factors.append(f"Cross-database: {', '.join(sorted(db_versions))}")

    # Classify tier
    if score >= 60:
        tier = "COMPLEX"
    elif score >= 30:
        tier = "MODERATE"
    else:
        tier = "STRAIGHTFORWARD"

    # Effort estimate (person-hours)
    if tier == "COMPLEX":
        effort_hours = round(score * 0.3 + 4, 1)
    elif tier == "MODERATE":
        effort_hours = round(score * 0.2 + 2, 1)
    else:
        effort_hours = round(score * 0.1 + 1, 1)

    return {
        "job_name": job["job_name"],
        "domain": job["domain"],
        "complexity_score": score,
        "tier": tier,
        "effort_hours": effort_hours,
        "factors": factors,
        "component_count": comp_count,
        "expression_count": expr_count,
        "expression_complexity_score": total_expr_score,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python classify_complexity.py <analysis_output_dir>")
        sys.exit(1)

    output_dir = sys.argv[1]
    inventory_path = os.path.join(output_dir, "job_inventory.json")

    if not os.path.exists(inventory_path):
        print(f"Error: {inventory_path} not found. Run parse_talend_xml.py first.")
        sys.exit(1)

    with open(inventory_path) as f:
        inventory = json.load(f)

    results = [classify_job(job) for job in inventory]
    results.sort(key=lambda x: -x["complexity_score"])

    tier_counts = {"STRAIGHTFORWARD": 0, "MODERATE": 0, "COMPLEX": 0}
    total_effort = 0
    for r in results:
        tier_counts[r["tier"]] += 1
        total_effort += r["effort_hours"]

    report = {
        "jobs": results,
        "summary": {
            "total_jobs": len(results),
            "tier_distribution": tier_counts,
            "total_effort_hours": round(total_effort, 1),
            "avg_effort_hours": round(total_effort / len(results), 1) if results else 0,
        },
    }

    output_path = os.path.join(output_dir, "complexity_report.json")
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    print("Complexity Classification:")
    print(f"  {'Job':<40} {'Score':>6} {'Tier':<18} {'Effort':>8}")
    print(f"  {'-'*40} {'-'*6} {'-'*18} {'-'*8}")
    for r in results:
        print(f"  {r['domain'] + '/' + r['job_name']:<40} {r['complexity_score']:>6} "
              f"{r['tier']:<18} {r['effort_hours']:>6.1f}h")
    print(f"\n  Total: {tier_counts['STRAIGHTFORWARD']}x straightforward, "
          f"{tier_counts['MODERATE']}x moderate, {tier_counts['COMPLEX']}x complex")
    print(f"  Estimated total effort: {total_effort:.1f} hours")
    print(f"\n→ {output_path}")


if __name__ == "__main__":
    main()
