#!/usr/bin/env python3
"""
빠른 수정: 깨진 그래프를 개선하는 스크립트
"""

import sys
import os

# 기존 rdf_visualizer.py의 visualize_rdf_graph 함수를 수정한 버전

def quick_fix_visualization(rdf_file: str, output_image: str):
    """
    개선된 시각화 - 빠른 수정 버전
    """
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import networkx as nx
    from rdflib import Graph, Namespace, RDF, RDFS
    import matplotlib.patches as mpatches
    
    AITON = Namespace("http://www.aitom.com/aiton.owl#")
    
    # RDF 그래프 로드
    g = Graph()
    g.parse(rdf_file, format='xml')
    
    # NetworkX 그래프 생성
    nx_graph = nx.DiGraph()
    node_info = {}
    
    # 노드 추출
    for s, p, o in g.triples((None, RDF.type, None)):
        if str(o).startswith("http://www.aitom.com/aiton.owl#"):
            node_type = str(o).split('#')[1]
            node_id = str(s).split('#')[1]
            
            label = None
            for _, _, label_obj in g.triples((s, RDFS.label, None)):
                label = str(label_obj)
                break
            
            if label is None:
                label = node_id
            
            nx_graph.add_node(node_id, node_type=node_type, label=label)
            node_info[node_id] = {'type': node_type, 'label': label}
    
    # 엣지 추출
    edge_labels = {}
    for prop in ['hasSynthesisMethod', 'consistOfStep', 'nextStep',
                 'usesPrecursor', 'usesSolvent', 'performedUnder',
                 'producesProduct']:
        for s, p, o in g.triples((None, AITON[prop], None)):
            source_id = str(s).split('#')[1]
            target_id = str(o).split('#')[1]
            
            if source_id in nx_graph.nodes and target_id in nx_graph.nodes:
                nx_graph.add_edge(source_id, target_id, relation=prop)
                edge_labels[(source_id, target_id)] = prop
    
    # 🔧 개선 1: 레이아웃 파라미터 조정
    pos = nx.spring_layout(nx_graph, k=5, iterations=150, seed=42)
    
    # 🔧 개선 2: 그래프 크기 증가
    fig, ax = plt.subplots(figsize=(28, 20))
    
    # 노드 색상
    node_colors = {
        'InorganicMaterial': '#FF6B6B',
        'SynthesisMethod': '#4ECDC4',
        'SynthesisStep': '#45B7D1',
        'Precursor': '#FFA07A',
        'Solvent': '#98D8C8',
        'Product': '#FFD93D',
        'Condition': '#B4A7D6'
    }
    
    # 🔧 개선 3: 노드 크기 증가
    for node in nx_graph.nodes():
        node_type = nx_graph.nodes[node].get('node_type', 'Unknown')
        color = node_colors.get(node_type, '#CCCCCC')
        
        x, y = pos[node]
        
        from matplotlib.patches import FancyBboxPatch
        bbox = FancyBboxPatch(
            (x-0.25, y-0.12), 0.5, 0.24,  # 크기 증가!
            boxstyle="round,pad=0.02",
            facecolor=color,
            edgecolor='black',
            linewidth=3,
            transform=ax.transData
        )
        ax.add_patch(bbox)
        
        label = nx_graph.nodes[node].get('label', node)
        ax.text(x, y, label, 
                fontsize=11,  # 폰트 크기 증가
                ha='center', 
                va='center',
                weight='bold',
                color='black')
    
    # 🔧 개선 4: 중요한 엣지만 레이블 표시
    important_relations = ['hasSynthesisMethod', 'consistOfStep', 
                          'performedUnder', 'producesProduct']
    
    for edge in nx_graph.edges():
        source, target = edge
        x1, y1 = pos[source]
        x2, y2 = pos[target]
        
        relation = nx_graph.edges[edge].get('relation', '')
        
        # nextStep은 굵게
        if relation == 'nextStep':
            lw = 3
            color = '#2C3E50'
        else:
            lw = 2
            color = 'gray'
        
        ax.annotate('',
                   xy=(x2, y2), xycoords='data',
                   xytext=(x1, y1), textcoords='data',
                   arrowprops=dict(
                       arrowstyle='->',
                       lw=lw,
                       color=color,
                       connectionstyle="arc3,rad=0.1",
                       alpha=0.6
                   ))
        
        # 중요한 관계만 레이블
        if relation in important_relations:
            mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
            ax.text(mid_x, mid_y, relation,
                   fontsize=8,
                   ha='center',
                   bbox=dict(boxstyle='round,pad=0.4', 
                            facecolor='white', 
                            edgecolor='gray',
                            alpha=0.9))
    
    # 범례
    legend_elements = [
        mpatches.Patch(facecolor=color, edgecolor='black', label=node_type)
        for node_type, color in node_colors.items()
        if any(nx_graph.nodes[n].get('node_type') == node_type for n in nx_graph.nodes())
    ]
    ax.legend(handles=legend_elements, loc='upper left', 
             fontsize=12, framealpha=0.95)
    
    ax.set_title("Synthesis Process (Improved)", fontsize=20, weight='bold', pad=20)
    ax.axis('off')
    plt.tight_layout()
    
    # 🔧 개선 5: 고해상도 저장
    plt.savefig(output_image, dpi=600, bbox_inches='tight',
               facecolor='white', edgecolor='none')
    print(f"✅ 개선된 그래프 저장: {output_image}")
    
    plt.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python fix_visualization.py <rdf_file>")
        sys.exit(1)
    
    rdf_file = sys.argv[1]
    output_file = rdf_file.replace('.rdf', '_IMPROVED.png')
    
    print(f"\n🔧 그래프 시각화 개선 중...")
    print(f"  입력: {rdf_file}")
    print(f"  출력: {output_file}\n")
    
    quick_fix_visualization(rdf_file, output_file)
    
    print(f"\n✨ 완료! 개선된 그래프를 확인하세요:")
    print(f"  → {output_file}\n")