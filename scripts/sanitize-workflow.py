#!/usr/bin/env python3
"""Keep only the video restoration path from the supplied ComfyUI graph."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    graph = json.loads(args.source.read_text(encoding="utf-8"))

    # 422 is a provider-specific, encrypted model wrapper; 194 only changes
    # preview behavior. The separate 430+ image/LoRA path is unrelated.
    removed = {194, 422, 428, 429} | set(range(430, 457))
    graph["nodes"] = [node for node in graph["nodes"] if node["id"] not in removed]
    links = []
    for link in graph["links"]:
        link_id, source, source_slot, dest, dest_slot, kind = link
        if link_id in (385, 395):
            source, source_slot = 2, 0
        elif source in removed or dest in removed:
            continue
        links.append([link_id, source, source_slot, dest, dest_slot, kind])
    graph["links"] = links

    incoming = {}
    outgoing = {}
    for link_id, source, _source_slot, dest, _dest_slot, _kind in links:
        outgoing.setdefault(source, set()).add(link_id)
        incoming.setdefault(dest, set()).add(link_id)
    for node in graph["nodes"]:
        for item in node.get("inputs", []):
            if item.get("link") not in incoming.get(node["id"], set()):
                item["link"] = None
        for item in node.get("outputs", []):
            if "links" in item:
                kept = [x for x in item["links"] or [] if x in outgoing.get(node["id"], set())]
                item["links"] = kept or None
        node.get("properties", {}).pop("info", None)
        node.get("properties", {}).pop("ref_info", None)
        values = node.get("widgets_values")
        if isinstance(values, dict):
            values.pop("videopreview", None)
        if node["type"] == "VHS_LoadVideo":
            values["video"] = ""
        if node["type"] == "VHS_VideoCombine":
            values["filename_prefix"] = "film-revive" if node["id"] == 347 else "film-revive-compare"
    graph["extra"] = {"frontendVersion": graph.get("extra", {}).get("frontendVersion")}
    graph["last_node_id"] = max(node["id"] for node in graph["nodes"])
    graph["last_link_id"] = max(link[0] for link in links)

    args.target.parent.mkdir(parents=True, exist_ok=True)
    args.target.write_text(json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
