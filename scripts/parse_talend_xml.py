"""Parse Talend .item XML files and extract component graphs.

Reads all .item files under a given directory, extracts nodes (components),
connections (data flows), metadata (schemas), and context parameters.
Produces analysis_output/job_inventory.json.
"""
import json
import os
import sys
from pathlib import Path

from lxml import etree

NS = {"tf": "platform:/resource/org.talend.model/model/TalendFile.xsd"}


def parse_item_file(filepath: str) -> dict:
    tree = etree.parse(filepath)
    root = tree.getroot()

    job_name = Path(filepath).stem.rsplit("_0.", 1)[0]
    domain = Path(filepath).parent.name

    # Extract contexts
    contexts = []
    for ctx in root.findall("context", root.nsmap) if root.nsmap else root.findall("context"):
        ctx_name = ctx.get("name", "Default")
        params = []
        for cp in ctx.findall("contextParameter"):
            params.append({
                "name": cp.get("name"),
                "type": cp.get("type"),
                "value": cp.get("value", ""),
                "comment": cp.get("comment", ""),
            })
        contexts.append({"name": ctx_name, "parameters": params})

    # Extract nodes (components)
    nodes = []
    for node in root.findall("node"):
        component_name = node.get("componentName", "")
        unique_name = ""
        label = ""
        params = {}
        for ep in node.findall("elementParameter"):
            name = ep.get("name", "")
            value = ep.get("value", "")
            if name == "UNIQUE_NAME":
                unique_name = value
            elif name == "LABEL":
                label = value.strip('"')
            elif name in ("QUERY", "TABLE", "FILENAME", "DATA_ACTION", "DB_VERSION"):
                params[name] = value

        # Extract metadata (schema)
        schemas = []
        for meta in node.findall("metadata"):
            connector = meta.get("connector", "")
            meta_name = meta.get("name", "")
            columns = []
            for col in meta.findall("column"):
                columns.append({
                    "name": col.get("name"),
                    "type": col.get("type"),
                    "length": col.get("length"),
                    "nullable": col.get("nullable") == "true",
                    "key": col.get("key") == "true",
                    "sourceType": col.get("sourceType", ""),
                })
            schemas.append({
                "connector": connector,
                "name": meta_name,
                "columns": columns,
            })

        # Extract tMap expressions
        tmap_expressions = []
        for nd in node.findall("nodeData"):
            for ot in nd.findall("outputTables"):
                for entry in ot.findall("mapperTableEntries"):
                    expr = entry.get("expression", "")
                    if expr:
                        tmap_expressions.append({
                            "output_table": ot.get("name", ""),
                            "column": entry.get("name", ""),
                            "expression": expr,
                        })
            for vt in nd.findall("varTables"):
                for entry in vt.findall("mapperTableEntries"):
                    expr = entry.get("expression", "")
                    if expr:
                        tmap_expressions.append({
                            "output_table": "__var__",
                            "column": entry.get("name", ""),
                            "expression": expr,
                        })

        nodes.append({
            "unique_name": unique_name,
            "component_name": component_name,
            "label": label,
            "parameters": params,
            "schemas": schemas,
            "tmap_expressions": tmap_expressions,
        })

    # Extract connections
    connections = []
    for conn in root.findall("connection"):
        connections.append({
            "source": conn.get("source"),
            "target": conn.get("target"),
            "label": conn.get("label"),
            "connector": conn.get("connectorName", "FLOW"),
        })

    # Extract routines
    routines = []
    for params_el in root.findall("parameters"):
        for rp in params_el.findall("routinesParameter"):
            routines.append(rp.get("name", ""))

    return {
        "job_name": job_name,
        "domain": domain,
        "file": str(filepath),
        "contexts": contexts,
        "nodes": nodes,
        "connections": connections,
        "routines": routines,
        "component_count": len(nodes),
        "connection_count": len(connections),
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python parse_talend_xml.py <talend_jobs_dir>")
        sys.exit(1)

    jobs_dir = sys.argv[1]
    output_dir = os.path.join(os.path.dirname(jobs_dir.rstrip("/")), "analysis_output")
    os.makedirs(output_dir, exist_ok=True)

    inventory = []
    for root_dir, _, files in os.walk(jobs_dir):
        for fname in sorted(files):
            if fname.endswith(".item"):
                filepath = os.path.join(root_dir, fname)
                try:
                    job = parse_item_file(filepath)
                    inventory.append(job)
                    print(f"  Parsed: {job['domain']}/{job['job_name']} "
                          f"({job['component_count']} components, "
                          f"{job['connection_count']} connections)")
                except Exception as e:
                    print(f"  ERROR parsing {filepath}: {e}", file=sys.stderr)

    output_path = os.path.join(output_dir, "job_inventory.json")
    with open(output_path, "w") as f:
        json.dump(inventory, f, indent=2)

    print(f"\nParsed {len(inventory)} jobs → {output_path}")
    return inventory


if __name__ == "__main__":
    main()
