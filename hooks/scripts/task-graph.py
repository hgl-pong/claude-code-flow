#!/usr/bin/env python
"""DAG task graph manager. Usage: task-graph.py <action> [args]"""
import json, os, sys
from collections import deque

FLOW_DIR = os.path.join(".claude", "flow")
GRAPH_FILE = os.path.join(FLOW_DIR, "task-graph.json")

def load_graph():
    if os.path.exists(GRAPH_FILE):
        with open(GRAPH_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {"nodes": [], "edges": []}
    return {"nodes": [], "edges": []}

def save_graph(graph):
    os.makedirs(FLOW_DIR, exist_ok=True)
    with open(GRAPH_FILE, "w") as f:
        json.dump(graph, f, indent=2)

def find_node(graph, node_id):
    for n in graph["nodes"]:
        if n["id"] == node_id:
            return n
    return None

def detect_cycle(graph, node_id, deps, visited=None, stack=None):
    """Detect if adding deps to node_id would create a cycle."""
    if visited is None:
        visited = set()
    if stack is None:
        stack = set()

    if node_id in stack:
        return True
    if node_id in visited:
        return False

    visited.add(node_id)
    stack.add(node_id)

    node = find_node(graph, node_id)
    if node:
        for dep in node.get("dependencies", []):
            if detect_cycle(graph, dep, None, visited, stack):
                return True

    stack.remove(node_id)
    return False

def get_ready_nodes(graph):
    """Return all pending nodes whose dependencies are all done."""
    done_ids = {n["id"] for n in graph["nodes"] if n.get("status") == "done"}
    ready = []
    for n in graph["nodes"]:
        if n.get("status") != "pending":
            continue
        deps = n.get("dependencies", [])
        if all(d in done_ids for d in deps):
            ready.append(n)
    return ready

def get_status(graph):
    """Return progress summary."""
    total = len(graph["nodes"])
    by_status = {}
    for n in graph["nodes"]:
        s = n.get("status", "pending")
        by_status[s] = by_status.get(s, 0) + 1
    return {
        "total": total,
        "by_status": by_status,
        "done": by_status.get("done", 0),
        "pending": by_status.get("pending", 0),
        "running": by_status.get("running", 0),
        "failed": by_status.get("failed", 0),
        "blocked": by_status.get("blocked", 0),
    }

def visualize(graph):
    """Output text DAG visualization."""
    if not graph["nodes"]:
        return "No tasks in graph."

    status_symbols = {
        "done": "[OK]",
        "running": "[>>]",
        "pending": "[  ]",
        "failed": "[!!]",
        "blocked": "[--]",
    }

    lines = []
    lines.append("Task Graph:")
    lines.append("")

    # Group by status for clarity
    for status in ["running", "pending", "blocked", "failed", "done"]:
        nodes = [n for n in graph["nodes"] if n.get("status") == status]
        if not nodes:
            continue
        symbol = status_symbols.get(status, "?")
        for n in nodes:
            deps = n.get("dependencies", [])
            agent = n.get("agent", "?")
            dep_str = f" (after: {', '.join(deps)})" if deps else ""
            lines.append(f"  {symbol} [{n['id']}] {n['title']} ({agent}){dep_str}")
        lines.append("")

    status_summary = get_status(graph)
    lines.append(f"Progress: {status_summary['done']}/{status_summary['total']} done")
    return "\n".join(lines)

def main():
    action = sys.argv[1] if len(sys.argv) > 1 else ""

    if action == "init":
        save_graph({"nodes": [], "edges": []})
        print("OK: task graph initialized")

    elif action == "load":
        graph = load_graph()
        print(json.dumps(graph, indent=2))

    elif action == "add-node":
        # add-node <id> <title> <agent> [dep1,dep2]
        node_id = sys.argv[2] if len(sys.argv) > 2 else ""
        title = sys.argv[3] if len(sys.argv) > 3 else ""
        agent = sys.argv[4] if len(sys.argv) > 4 else "forge"
        deps_str = sys.argv[5] if len(sys.argv) > 5 else ""
        deps = [d.strip() for d in deps_str.split(",") if d.strip()] if deps_str else []

        if not node_id or not title:
            print("Error: node id and title required", file=sys.stderr)
            sys.exit(1)

        graph = load_graph()
        if find_node(graph, node_id):
            print(f"Error: node {node_id} already exists", file=sys.stderr)
            sys.exit(1)

        node = {
            "id": node_id,
            "title": title,
            "agent": agent,
            "status": "pending",
            "dependencies": deps,
            "files": [],
        }

        # Temporarily add to check for cycles
        graph["nodes"].append(node)
        if detect_cycle(graph, node_id, deps):
            graph["nodes"].pop()
            print(f"Error: adding {node_id} would create a cycle", file=sys.stderr)
            sys.exit(1)

        # Add edges
        for dep in deps:
            edge = [dep, node_id]
            if edge not in graph["edges"]:
                graph["edges"].append(edge)

        save_graph(graph)
        print(f"OK: added node {node_id}")

    elif action == "set-status":
        node_id = sys.argv[2] if len(sys.argv) > 2 else ""
        status = sys.argv[3] if len(sys.argv) > 3 else "pending"
        valid = ["pending", "running", "done", "failed", "blocked"]
        if status not in valid:
            print(f"Error: invalid status '{status}'. Must be one of: {valid}", file=sys.stderr)
            sys.exit(1)

        graph = load_graph()
        node = find_node(graph, node_id)
        if not node:
            print(f"Error: node {node_id} not found", file=sys.stderr)
            sys.exit(1)

        node["status"] = status
        save_graph(graph)
        print(f"OK: {node_id} -> {status}")

    elif action == "get-ready":
        graph = load_graph()
        ready = get_ready_nodes(graph)
        if ready:
            for n in ready:
                print(f"{n['id']}|{n['agent']}|{n['title']}")
        # Exit silent if no ready nodes (not an error)

    elif action == "get-status":
        graph = load_graph()
        status = get_status(graph)
        print(json.dumps(status, indent=2))

    elif action == "visualize":
        graph = load_graph()
        print(visualize(graph))

    elif action == "clear":
        save_graph({"nodes": [], "edges": []})
        print("OK: task graph cleared")

    else:
        print(f"Unknown action: {action}", file=sys.stderr)
        print("Usage: task-graph.py <init|load|add-node|set-status|get-ready|get-status|visualize|clear>", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
