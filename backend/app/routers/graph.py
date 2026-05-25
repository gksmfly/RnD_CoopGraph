import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/api", tags=["graph"])

GRAPHML_PATH = Path(__file__).parent.parent.parent.parent / "kg_storage" / "graph_chunk_entity_relation.graphml"

_cached_html: str | None = None
_cached_html_key: str | None = None  # highlight nodes 조합을 키로 캐시 구분
_node_names: set[str] | None = None


def get_node_names() -> set[str]:
    """graphml에서 모든 노드 이름(id) 로드 (한 번만)"""
    global _node_names
    if _node_names is None:
        import networkx as nx
        G = nx.read_graphml(str(GRAPHML_PATH))
        _node_names = {nid for nid in G.nodes()}
    return _node_names


def extract_entities(answer: str) -> list[str]:
    """답변 텍스트에서 KG 노드 이름과 일치하는 엔티티 추출"""
    if not GRAPHML_PATH.exists():
        return []
    names = get_node_names()
    # 3자 미만 노드 제외 (NP, PU, 연구, 기술 등 노이즈)
    found = [name for name in names if name and len(name) > 2 and name in answer]
    # 긴 이름 우선 정렬
    found = sorted(found, key=len, reverse=True)
    # 더 긴 이름의 부분 문자열인 경우 제거 (예: "PIM" ⊂ "PIM 기술", "정보통신부" ⊂ "과학기술정보통신부")
    deduped: list[str] = []
    for name in found:
        if not any(name in kept for kept in deduped):
            deduped.append(name)
    return deduped[:30]


def _build_graph_html(max_nodes: int = 300) -> str:
    import networkx as nx
    from pyvis.network import Network

    G = nx.read_graphml(str(GRAPHML_PATH))

    top_nodes = sorted(G.degree(), key=lambda x: x[1], reverse=True)[:max_nodes]
    top_node_ids = {n for n, _ in top_nodes}
    subG = G.subgraph(top_node_ids)

    color_map = {
        "기관":   "#4A90D9",
        "기술분야": "#7ED321",
        "과제":   "#F5A623",
        "연구자":  "#BD10E0",
        "부처":   "#D0021B",
    }

    net = Network(height="100%", width="100%", bgcolor="#1a1a2e", font_color="white", directed=False, cdn_resources="in_line")
    net.barnes_hut(gravity=-8000, central_gravity=0.3, spring_length=150)

    for node_id, data in subG.nodes(data=True):
        entity_type = data.get("entity_type", "")
        label = data.get("id", node_id)
        if len(label) > 20:
            label = label[:20] + "…"
        color = color_map.get(entity_type, "#9B9B9B")
        degree = subG.degree(node_id)
        size = max(10, min(50, degree * 3))
        net.add_node(node_id, label=label, color=color, size=size,
                     title=f"[{entity_type}] {data.get('id', node_id)}")

    for src, dst, data in subG.edges(data=True):
        net.add_edge(src, dst, title=data.get("relation_type", ""), color="#555577")

    legend_html = """
    <div style="position:fixed;top:10px;left:10px;background:rgba(0,0,0,0.7);
                padding:10px;border-radius:8px;color:white;font-size:12px;z-index:999">
      <b>노드 타입</b><br>
      <span style="color:#4A90D9">●</span> 기관<br>
      <span style="color:#7ED321">●</span> 기술분야<br>
      <span style="color:#F5A623">●</span> 과제<br>
      <span style="color:#BD10E0">●</span> 연구자<br>
      <span style="color:#D0021B">●</span> 부처
    </div>
    """

    html = net.generate_html()
    full_size_css = """
    <style>
      html, body { margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; }
      #mynetwork { width: 100% !important; height: 100vh !important; border: none !important; }
    </style>
    """
    html = html.replace("</head>", full_size_css + "</head>")
    html = html.replace("</body>", legend_html + "</body>")
    return html


@router.get("/graph", response_class=HTMLResponse)
async def get_graph():
    """KG 시각화 HTML 반환 (전체 top 300)"""
    global _cached_html
    if _cached_html is None:
        if not GRAPHML_PATH.exists():
            return HTMLResponse("<div style='color:white;padding:20px'>graphml 파일 없음</div>")
        _cached_html = _build_graph_html(max_nodes=300)
    return HTMLResponse(_cached_html)


def _build_subgraph_html(highlight_nodes: set[str]) -> str:
    """질의 관련 핵심 노드들만 표시 (핵심↔핵심 엣지 + 중간 연결자 포함)"""
    import networkx as nx
    from pyvis.network import Network

    G = nx.read_graphml(str(GRAPHML_PATH))

    # 핵심 노드 id 집합
    core_nids = {n for n in highlight_nodes if n in G}
    if not core_nids:
        return "<div style='color:white;padding:20px;background:#1a1a2e'>관련 노드 없음</div>"

    # 2개 이상의 핵심 노드에 연결된 중간 노드(bridge)만 포함
    bridge_count: dict[str, int] = {}
    for nid in core_nids:
        for neighbor in G.neighbors(nid):
            if neighbor not in core_nids:
                bridge_count[neighbor] = bridge_count.get(neighbor, 0) + 1
    # 2개+ 핵심 노드에 연결된 것만, degree 높은 순으로 최대 15개
    bridge_nids = {n for n, c in bridge_count.items() if c >= 2}
    if len(bridge_nids) > 15:
        bridge_nids = set(sorted(bridge_nids, key=lambda n: bridge_count[n], reverse=True)[:15])

    all_nids = core_nids | bridge_nids
    subG = G.subgraph(all_nids)

    color_map = {
        "기관":    "#4A90D9",
        "기술분야": "#7ED321",
        "과제":    "#F5A623",
        "연구자":  "#BD10E0",
        "부처":    "#D0021B",
    }

    net = Network(height="100%", width="100%", bgcolor="#1a1a2e", font_color="white",
                  directed=False, cdn_resources="in_line")
    net.barnes_hut(gravity=-5000, central_gravity=0.5, spring_length=150, spring_strength=0.05)

    for node_id, data in subG.nodes(data=True):
        entity_type = data.get("entity_type", "")
        label = node_id
        if len(label) > 18:
            label = label[:18] + "…"
        color = color_map.get(entity_type, "#9B9B9B")
        is_core = node_id in core_nids

        net.add_node(
            node_id,
            label=label,
            color={"background": color, "border": "#FFD700" if is_core else "#555577"},
            size=35 if is_core else 18,
            borderWidth=3 if is_core else 1,
            title=f"[{entity_type}] {node_id}" + (" ★" if is_core else ""),
            font={"size": 14 if is_core else 10, "color": "white"},
        )

    for src, dst, data in subG.edges(data=True):
        both_core = src in core_nids and dst in core_nids
        net.add_edge(src, dst,
                     title=data.get("relation_type", ""),
                     color="#FFD700" if both_core else "#555577",
                     width=2 if both_core else 1)

    node_count = len(all_nids)
    edge_count = subG.number_of_edges()
    legend_html = f"""
    <div style="position:fixed;top:10px;left:10px;background:rgba(0,0,0,0.75);
                padding:10px 14px;border-radius:8px;color:white;font-size:12px;z-index:999">
      <b>노드 타입</b><br>
      <span style="color:#4A90D9">●</span> 기관<br>
      <span style="color:#7ED321">●</span> 기술분야<br>
      <span style="color:#F5A623">●</span> 과제<br>
      <span style="color:#BD10E0">●</span> 연구자<br>
      <span style="color:#D0021B">●</span> 부처<br>
      <span style="color:#FFD700">★</span> 질의 핵심<br>
      <hr style="border-color:#444;margin:6px 0">
      <span style="color:#aaa">노드 {node_count} · 엣지 {edge_count}</span>
    </div>
    """

    html = net.generate_html()
    full_size_css = """
    <style>
      html, body { margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; }
      #mynetwork { width: 100% !important; height: 100vh !important; border: none !important; }
    </style>
    """
    html = html.replace("</head>", full_size_css + "</head>")
    html = html.replace("</body>", legend_html + "</body>")
    return html


@router.get("/graph/highlight", response_class=HTMLResponse)
async def get_graph_highlight(nodes: str = ""):
    """질의 관련 노드 + 이웃만 표시하는 서브그래프"""
    highlight_nodes = set(n.strip() for n in nodes.split(",") if n.strip()) if nodes else set()
    if not highlight_nodes:
        return HTMLResponse("<div style='color:white;padding:20px;background:#1a1a2e'>nodes 파라미터 없음</div>")

    if not hasattr(get_graph_highlight, "_cache"):
        get_graph_highlight._cache = {}

    cache_key = ",".join(sorted(highlight_nodes))
    if cache_key not in get_graph_highlight._cache:
        if not GRAPHML_PATH.exists():
            return HTMLResponse("<div style='color:white;padding:20px'>graphml 파일 없음</div>")
        get_graph_highlight._cache[cache_key] = _build_subgraph_html(highlight_nodes)
        if len(get_graph_highlight._cache) > 10:
            del get_graph_highlight._cache[next(iter(get_graph_highlight._cache))]

    return HTMLResponse(get_graph_highlight._cache[cache_key])


@router.get("/graph/stats")
async def get_graph_stats():
    import networkx as nx
    if not GRAPHML_PATH.exists():
        return {"error": "graphml 파일 없음"}
    G = nx.read_graphml(str(GRAPHML_PATH))
    return {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "graphml_exists": True,
    }
