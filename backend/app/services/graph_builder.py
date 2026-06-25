"""
Builds a NetworkX graph from parsed markdown sections, then serializes it
into the {nodes, edges} shape React Flow expects.

Two kinds of edges:
  - "structural": heading parent -> child (the document's own hierarchy)
  - "concept": two sections that both reference the same system concept
    (e.g. both mention "database") get linked, since that's often a real
    relationship the prose itself never states explicitly.
"""
import networkx as nx

from app.parsers.markdown_parser import Section


def build_graph(sections: list[Section]) -> dict:
    g = nx.DiGraph()

    for s in sections:
        g.add_node(
            s.id,
            title=s.title,
            level=s.level,
            content=s.content.strip()[:2000],
            code_blocks=s.code_blocks[:5],
            concepts=sorted(s.concepts),
        )

    # structural edges from heading hierarchy
    for s in sections:
        if s.parent_id and g.has_node(s.parent_id):
            g.add_edge(s.parent_id, s.id, kind="structural")

    # concept co-occurrence edges (undirected in spirit, stored as one directed edge)
    concept_to_sections: dict[str, list[str]] = {}
    for s in sections:
        for c in s.concepts:
            concept_to_sections.setdefault(c, []).append(s.id)

    for concept, ids in concept_to_sections.items():
        for a, b in zip(ids, ids[1:]):
            if a != b and not g.has_edge(a, b) and not g.has_edge(b, a):
                g.add_edge(a, b, kind="concept", via=concept)

    return _to_react_flow(g)


def _to_react_flow(g: nx.DiGraph) -> dict:
    # Layered layout: x by BFS depth from roots, y by sibling order.
    roots = [n for n in g.nodes if g.in_degree(n) == 0] or list(g.nodes)[:1]

    depth: dict[str, int] = {}
    for root in roots:
        lengths = nx.single_source_shortest_path_length(g, root)
        for node, d in lengths.items():
            depth[node] = min(depth.get(node, 10**9), d)
    for n in g.nodes:
        depth.setdefault(n, 0)

    layer_counts: dict[int, int] = {}
    nodes = []
    for n, data in g.nodes(data=True):
        d = depth[n]
        col = layer_counts.get(d, 0)
        layer_counts[d] = col + 1
        nodes.append(
            {
                "id": n,
                "type": "conceptNode",
                "position": {"x": d * 320, "y": col * 140},
                "data": {
                    "title": data.get("title", n),
                    "level": data.get("level", 1),
                    "preview": (data.get("content", "")[:140]),
                    "hasCode": bool(data.get("code_blocks")),
                    "concepts": data.get("concepts", []),
                },
            }
        )

    edges = []
    for u, v, edata in g.edges(data=True):
        kind = edata.get("kind", "structural")
        edges.append(
            {
                "id": f"{u}->{v}",
                "source": u,
                "target": v,
                "animated": kind == "concept",
                "data": {"kind": kind, "via": edata.get("via")},
            }
        )

    return {"nodes": nodes, "edges": edges}
