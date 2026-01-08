"""
RDF 그래프 시각화 도구
NetworkX와 Matplotlib를 사용하여 그래프를 시각화
"""

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import networkx as nx
from rdflib import Graph, Namespace, RDF, RDFS
from matplotlib.patches import FancyBboxPatch
import matplotlib.patches as mpatches


AITON = Namespace("http://www.aitom.com/aiton.owl#")


def visualize_rdf_graph(rdf_file: str, output_image: str = None, title: str = "RDF Graph"):
    """
    RDF 그래프를 시각화
    
    Args:
        rdf_file: RDF 파일 경로
        output_image: 출력 이미지 파일 경로
        title: 그래프 제목
    """
    # RDF 그래프 로드
    g = Graph()
    g.parse(rdf_file, format='xml')
    
    # NetworkX 그래프 생성
    nx_graph = nx.DiGraph()
    
    # 노드 정보 저장
    node_info = {}
    
    # RDF에서 노드와 엣지 추출
    # 1. 노드 추출 (rdf:type이 있는 개체들)
    for s, p, o in g.triples((None, RDF.type, None)):
        if str(o).startswith("http://www.aitom.com/aiton.owl#"):
            node_type = str(o).split('#')[1]
            node_id = str(s).split('#')[1]
            
            # 레이블 찾기
            label = None
            for _, _, label_obj in g.triples((s, RDFS.label, None)):
                label = str(label_obj)
                break
            
            if label is None:
                label = node_id
            
            # 노드 추가
            nx_graph.add_node(node_id, node_type=node_type, label=label)
            node_info[node_id] = {
                'type': node_type,
                'label': label,
                'uri': str(s)
            }
    
    # 2. 엣지 추출 (Object Properties)
    object_properties = [
        'hasSynthesisMethod', 'consistOfStep', 'nextStep',
        'usesPrecursor', 'usesSolvent', 'performedUnder',
        'producesProduct', 'usesAbrasive', 'usesAddictive', 'usesMedia'
    ]
    
    edge_labels = {}
    for prop in object_properties:
        for s, p, o in g.triples((None, AITON[prop], None)):
            source_id = str(s).split('#')[1]
            target_id = str(o).split('#')[1]
            
            if source_id in nx_graph.nodes and target_id in nx_graph.nodes:
                nx_graph.add_edge(source_id, target_id, relation=prop)
                edge_labels[(source_id, target_id)] = prop
    
    # 그래프 레이아웃
    pos = nx.spring_layout(nx_graph, k=2, iterations=50, seed=42)
    
    # 한글 폰트 설정
    plt.rcParams['font.family'] = 'DejaVu Sans'
    plt.rcParams['axes.unicode_minus'] = False
    
    # 그림 생성
    fig, ax = plt.subplots(figsize=(16, 12))
    
    # 노드 타입별 색상 정의
    node_colors = {
        'InorganicMaterial': '#FF6B6B',
        'SynthesisMethod': '#4ECDC4',
        'SynthesisStep': '#45B7D1',
        'Precursor': '#FFA07A',
        'Solvent': '#98D8C8',
        'Product': '#FFD93D',
        'Condition': '#B4A7D6',
        'Abrasive': '#F8B88B',
        'Additive': '#FAA0A0',
        'Media': '#B0E57C'
    }
    
    # 노드 그리기
    for node in nx_graph.nodes():
        node_type = nx_graph.nodes[node].get('node_type', 'Unknown')
        color = node_colors.get(node_type, '#CCCCCC')
        
        x, y = pos[node]
        
        # 노드 박스
        bbox = FancyBboxPatch(
            (x-0.15, y-0.08), 0.3, 0.16,
            boxstyle="round,pad=0.01",
            facecolor=color,
            edgecolor='black',
            linewidth=2,
            transform=ax.transData
        )
        ax.add_patch(bbox)
        
        # 노드 레이블
        label = nx_graph.nodes[node].get('label', node)
        ax.text(x, y, label, 
                fontsize=9, 
                ha='center', 
                va='center',
                weight='bold',
                color='black')
    
    # 엣지 그리기
    for edge in nx_graph.edges():
        source, target = edge
        x1, y1 = pos[source]
        x2, y2 = pos[target]
        
        # 화살표
        ax.annotate('',
                   xy=(x2, y2), xycoords='data',
                   xytext=(x1, y1), textcoords='data',
                   arrowprops=dict(
                       arrowstyle='->',
                       lw=2,
                       color='gray',
                       connectionstyle="arc3,rad=0.1"
                   ))
        
        # 엣지 레이블
        relation = nx_graph.edges[edge].get('relation', '')
        mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(mid_x, mid_y, relation,
               fontsize=7,
               ha='center',
               bbox=dict(boxstyle='round,pad=0.3', 
                        facecolor='white', 
                        edgecolor='gray',
                        alpha=0.8))
    
    # 범례
    legend_elements = [
        mpatches.Patch(facecolor=color, edgecolor='black', label=node_type)
        for node_type, color in node_colors.items()
        if any(nx_graph.nodes[n].get('node_type') == node_type for n in nx_graph.nodes())
    ]
    ax.legend(handles=legend_elements, loc='upper left', 
             fontsize=10, framealpha=0.9)
    
    ax.set_title(title, fontsize=16, weight='bold', pad=20)
    ax.axis('off')
    plt.tight_layout()
    
    # 저장
    if output_image:
        plt.savefig(output_image, dpi=300, bbox_inches='tight')
        print(f"그래프 이미지 저장: {output_image}")
    
    plt.close()
    
    # 통계 출력
    print(f"\n그래프 통계:")
    print(f"  노드 수: {nx_graph.number_of_nodes()}")
    print(f"  엣지 수: {nx_graph.number_of_edges()}")
    print(f"\n노드 타입 분포:")
    
    type_count = {}
    for node in nx_graph.nodes():
        node_type = nx_graph.nodes[node].get('node_type', 'Unknown')
        type_count[node_type] = type_count.get(node_type, 0) + 1
    
    for node_type, count in sorted(type_count.items()):
        print(f"    {node_type}: {count}")


def create_simplified_view(rdf_file: str, output_image: str = None):
    """
    간소화된 그래프 뷰 (주요 구조만 표시)
    
    Args:
        rdf_file: RDF 파일 경로
        output_image: 출력 이미지 파일 경로
    """
    # RDF 그래프 로드
    g = Graph()
    g.parse(rdf_file, format='xml')
    
    # NetworkX 그래프 생성
    nx_graph = nx.DiGraph()
    
    # 주요 노드 타입만 선택
    main_types = ['InorganicMaterial', 'SynthesisMethod', 'SynthesisStep', 
                  'Product', 'Precursor', 'Condition']
    
    # 노드 추출
    node_info = {}
    for s, p, o in g.triples((None, RDF.type, None)):
        if str(o).startswith("http://www.aitom.com/aiton.owl#"):
            node_type = str(o).split('#')[1]
            
            if node_type in main_types:
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
    for prop in ['hasSynthesisMethod', 'consistOfStep', 'nextStep', 
                 'performedUnder', 'producesProduct']:
        for s, p, o in g.triples((None, AITON[prop], None)):
            source_id = str(s).split('#')[1]
            target_id = str(o).split('#')[1]
            
            if source_id in nx_graph.nodes and target_id in nx_graph.nodes:
                nx_graph.add_edge(source_id, target_id, relation=prop)
    
    # 계층적 레이아웃
    pos = nx.spring_layout(nx_graph, k=3, iterations=50, seed=42)
    
    # 그림 생성
    fig, ax = plt.subplots(figsize=(14, 10))
    
    node_colors = {
        'InorganicMaterial': '#FF6B6B',
        'SynthesisMethod': '#4ECDC4',
        'SynthesisStep': '#45B7D1',
        'Product': '#FFD93D',
        'Precursor': '#FFA07A',
        'Condition': '#B4A7D6'
    }
    
    # 노드 그리기
    for node in nx_graph.nodes():
        node_type = nx_graph.nodes[node].get('node_type', 'Unknown')
        color = node_colors.get(node_type, '#CCCCCC')
        
        x, y = pos[node]
        
        circle = plt.Circle((x, y), 0.1, 
                           facecolor=color, 
                           edgecolor='black', 
                           linewidth=2.5,
                           zorder=2)
        ax.add_patch(circle)
        
        label = nx_graph.nodes[node].get('label', node)
        ax.text(x, y-0.15, label,
               fontsize=10,
               ha='center',
               va='top',
               weight='bold',
               bbox=dict(boxstyle='round,pad=0.5',
                        facecolor='white',
                        edgecolor='gray',
                        alpha=0.9))
    
    # 엣지 그리기
    for edge in nx_graph.edges():
        source, target = edge
        x1, y1 = pos[source]
        x2, y2 = pos[target]
        
        ax.annotate('',
                   xy=(x2, y2), xycoords='data',
                   xytext=(x1, y1), textcoords='data',
                   arrowprops=dict(
                       arrowstyle='-|>',
                       lw=2.5,
                       color='#555555',
                       connectionstyle="arc3,rad=0.2"
                   ),
                   zorder=1)
    
    ax.set_title('Synthesis Process Flow (Simplified)', 
                fontsize=16, weight='bold', pad=20)
    ax.axis('off')
    plt.tight_layout()
    
    if output_image:
        plt.savefig(output_image, dpi=300, bbox_inches='tight')
        print(f"간소화된 그래프 저장: {output_image}")
    
    plt.close()


if __name__ == "__main__":
    print("\n📊 RDF 그래프 시각화\n")
    
    # 기본 예제 시각화
    print("1. 기본 예제 시각화 중...")
    visualize_rdf_graph(
        "./output/output_graph_basic.rdf",
        "./output/graph_basic_viz.png",
        "TiO2 Nanoparticle Synthesis Process"
    )
    
    # 복잡한 예제 시각화
    print("\n2. 복잡한 예제 시각화 중...")
    visualize_rdf_graph(
        "./output/output_graph_complex.rdf",
        "./output/graph_complex_viz.png",
        "ZSM-5 Zeolite Hydrothermal Synthesis"
    )
    
    # 간소화된 뷰
    print("\n3. 간소화된 뷰 생성 중...")
    create_simplified_view(
        "./output/output_graph_complex.rdf",
        "./output/graph_simplified_viz.png"
    )
    
    print("\n✅ 시각화 완료!")
    print("생성된 이미지:")
    print("  - ./output/graph_basic_viz.png")
    print("  - ./output/graph_complex_viz.png")
    print("  - ./output/graph_simplified_viz.png")