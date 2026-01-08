"""
RDF 온톨로지 기반 그래프 구축 도구
무기 재료 합성 프로세스를 RDF 그래프로 표현
"""

from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS, OWL
from rdflib.namespace import XSD
from typing import Optional, List, Dict, Any
import uuid


# 네임스페이스 정의
AITON = Namespace("http://www.aitom.com/aiton.owl#")


class Node:
    """
    RDF 그래프의 노드(개체) 클래스
    각 노드는 온톨로지의 클래스 인스턴스
    """
    
    def __init__(self, node_type: str, node_id: str = None, label: str = None):
        """
        Args:
            node_type: 노드의 타입 (예: "InorganicMaterial", "SynthesisStep")
            node_id: 노드의 고유 ID (없으면 자동 생성)
            label: 노드의 레이블 (사람이 읽기 쉬운 이름)
        """
        self.node_type = node_type
        self.node_id = node_id if node_id else str(uuid.uuid4())
        self.label = label if label else f"{node_type}_{self.node_id[:8]}"
        
        # URI 생성 (RDF에서 개체의 고유 식별자)
        self.uri = URIRef(f"http://www.aitom.com/aiton.owl#{self.node_type}_{self.node_id}")
        
        # 데이터 속성 저장
        self.data_properties: Dict[str, Any] = {}
    
    def add_data_property(self, property_name: str, value: Any, datatype=None):
        """
        노드에 데이터 속성 추가
        
        Args:
            property_name: 속성 이름 (예: "hasTemperature")
            value: 속성 값
            datatype: 데이터 타입 (XSD.float, XSD.string 등)
        """
        self.data_properties[property_name] = {
            'value': value,
            'datatype': datatype
        }
    
    def to_rdf(self, graph: Graph):
        """
        이 노드를 RDF 그래프에 추가
        
        Args:
            graph: rdflib Graph 객체
        """
        # 노드의 타입 선언
        graph.add((self.uri, RDF.type, AITON[self.node_type]))
        
        # 레이블 추가
        graph.add((self.uri, RDFS.label, Literal(self.label, lang="ko")))
        
        # 데이터 속성 추가
        for prop_name, prop_data in self.data_properties.items():
            value = prop_data['value']
            datatype = prop_data['datatype']
            
            if datatype:
                literal = Literal(value, datatype=datatype)
            else:
                literal = Literal(value)
            
            graph.add((self.uri, AITON[prop_name], literal))
    
    def __repr__(self):
        return f"Node(type={self.node_type}, id={self.node_id[:8]}, label={self.label})"


class Edge:
    """
    RDF 그래프의 엣지(관계) 클래스
    두 노드 사이의 객체 속성(Object Property) 관계
    """
    
    def __init__(self, source: Node, edge_type: str, target: Node):
        """
        Args:
            source: 출발 노드
            edge_type: 관계 타입 (예: "hasSynthesisMethod", "usesPrecursor")
            target: 도착 노드
        """
        self.source = source
        self.edge_type = edge_type
        self.target = target
    
    def to_rdf(self, graph: Graph):
        """
        이 엣지를 RDF 그래프에 추가
        
        Args:
            graph: rdflib Graph 객체
        """
        graph.add((
            self.source.uri,
            AITON[self.edge_type],
            self.target.uri
        ))
    
    def __repr__(self):
        return f"Edge({self.source.label} --[{self.edge_type}]--> {self.target.label})"


class RDFGraphBuilder:
    """
    RDF 그래프 구축 및 관리 클래스
    """
    
    def __init__(self, ontology_file: str = None):
        """
        Args:
            ontology_file: 기존 온톨로지 파일 경로 (로드할 경우)
        """
        self.graph = Graph()
        
        # 네임스페이스 바인딩
        self.graph.bind("aiton", AITON)
        self.graph.bind("owl", OWL)
        
        # 온톨로지 로드
        if ontology_file:
            self.load_ontology(ontology_file)
        
        # 노드와 엣지 저장
        self.nodes: List[Node] = []
        self.edges: List[Edge] = []
    
    def load_ontology(self, file_path: str):
        """기존 온톨로지 파일 로드"""
        self.graph.parse(file_path, format='xml')
        print(f"온톨로지 로드 완료: {len(self.graph)} triples")
    
    def add_node(self, node: Node):
        """노드를 그래프에 추가"""
        self.nodes.append(node)
        node.to_rdf(self.graph)
    
    def add_edge(self, edge: Edge):
        """엣지를 그래프에 추가"""
        self.edges.append(edge)
        edge.to_rdf(self.graph)
    
    def add_relationship(self, source: Node, edge_type: str, target: Node):
        """
        두 노드 사이에 관계 추가 (편의 함수)
        
        Args:
            source: 출발 노드
            edge_type: 관계 타입
            target: 도착 노드
        """
        edge = Edge(source, edge_type, target)
        self.add_edge(edge)
        return edge
    
    def save(self, output_file: str, format: str = 'xml'):
        """
        그래프를 파일로 저장
        
        Args:
            output_file: 출력 파일 경로
            format: 파일 형식 ('xml', 'turtle', 'n3', 'nt' 등)
        """
        self.graph.serialize(destination=output_file, format=format, encoding='utf-8')
        print(f"그래프 저장 완료: {output_file}")
        print(f"총 {len(self.nodes)} 노드, {len(self.edges)} 엣지")
        print(f"총 {len(self.graph)} triples")
    
    def print_summary(self):
        """그래프 요약 정보 출력"""
        print("\n=== 그래프 요약 ===")
        print(f"노드 수: {len(self.nodes)}")
        print(f"엣지 수: {len(self.edges)}")
        print(f"\n노드 목록:")
        for node in self.nodes:
            print(f"  - {node}")
        print(f"\n엣지 목록:")
        for edge in self.edges:
            print(f"  - {edge}")


# ============== 사용 예제 ==============

def example_basic():
    """기본 사용 예제: 간단한 합성 프로세스"""
    print("\n" + "="*60)
    print("예제 1: 기본 사용법")
    print("="*60)
    
    # 1. RDF 그래프 빌더 생성 (기존 온톨로지 로드)
    builder = RDFGraphBuilder(ontology_file="/Users/gamjawon/2025-2-prometheus-14Team/prometheus-project/ontology/aitom_inorganic.rdf")
    
    # 2. 노드 생성
    # 무기 재료 노드
    material = Node(
        node_type="InorganicMaterial",
        node_id="TiO2_nanoparticle",
        label="이산화티타늄 나노입자"
    )
    material.add_data_property("isOxygenDeficiency", 0.05, XSD.float)
    
    # 합성 방법 노드
    synthesis_method = Node(
        node_type="SynthesisMethod",
        node_id="sol_gel_method",
        label="졸겔법"
    )
    
    # 합성 단계 노드
    step1 = Node(
        node_type="SynthesisStep",
        node_id="mixing_step",
        label="혼합 단계"
    )
    
    step2 = Node(
        node_type="SynthesisStep",
        node_id="heating_step",
        label="가열 단계"
    )
    
    # 전구체 노드
    precursor = Node(
        node_type="Precursor",
        node_id="titanium_isopropoxide",
        label="Titanium Isopropoxide"
    )
    
    # 용매 노드
    solvent = Node(
        node_type="Solvent",
        node_id="ethanol",
        label="에탄올"
    )
    
    # 조건 노드
    condition = Node(
        node_type="Condition",
        node_id="heating_condition",
        label="가열 조건"
    )
    condition.add_data_property("hasTemperature", 500.0, XSD.float)
    condition.add_data_property("hasDuration", "2 hours", XSD.string)
    
    # 생성물 노드
    product = Node(
        node_type="Product",
        node_id="tio2_product",
        label="TiO2 생성물"
    )
    
    # 3. 노드를 그래프에 추가
    for node in [material, synthesis_method, step1, step2, precursor, solvent, condition, product]:
        builder.add_node(node)
    
    # 4. 엣지(관계) 추가
    builder.add_relationship(material, "hasSynthesisMethod", synthesis_method)
    builder.add_relationship(synthesis_method, "consistOfStep", step1)
    builder.add_relationship(step1, "nextStep", step2)
    builder.add_relationship(step1, "usesPrecursor", precursor)
    builder.add_relationship(step1, "usesSolvent", solvent)
    builder.add_relationship(step2, "performedUnder", condition)
    builder.add_relationship(step2, "producesProduct", product)
    
    # 5. 요약 출력
    builder.print_summary()
    
    # 6. 파일로 저장
    builder.save("./output/output_graph_basic.rdf", format='xml')
    
    return builder


def example_complex():
    """복잡한 예제: 다단계 합성 프로세스"""
    print("\n" + "="*60)
    print("예제 2: 복잡한 합성 프로세스")
    print("="*60)
    
    builder = RDFGraphBuilder(ontology_file="/Users/gamjawon/2025-2-prometheus-14Team/prometheus-project/ontology/aitom_inorganic.rdf")
    
    # 재료
    material = Node("InorganicMaterial", "zeolite_zsm5", "ZSM-5 제올라이트")
    
    # 합성 방법
    method = Node("SynthesisMethod", "hydrothermal", "수열합성법")
    
    # 여러 단계
    steps = []
    step_configs = [
        ("preparation", "용액 준비"),
        ("aging", "숙성"),
        ("crystallization", "결정화"),
        ("calcination", "소성")
    ]
    
    for step_id, step_label in step_configs:
        step = Node("SynthesisStep", step_id, step_label)
        steps.append(step)
        builder.add_node(step)
    
    # 재료와 방법 추가
    builder.add_node(material)
    builder.add_node(method)
    
    # 관계 설정
    builder.add_relationship(material, "hasSynthesisMethod", method)
    
    # 첫 단계 연결
    builder.add_relationship(method, "consistOfStep", steps[0])
    
    # 순차적 단계 연결
    for i in range(len(steps) - 1):
        builder.add_relationship(steps[i], "nextStep", steps[i+1])
    
    # 각 단계에 화학물질과 조건 추가
    # 준비 단계
    precursor1 = Node("Precursor", "silica_source", "실리카 원료")
    precursor2 = Node("Precursor", "alumina_source", "알루미나 원료")
    solvent1 = Node("Solvent", "water", "물")
    
    builder.add_node(precursor1)
    builder.add_node(precursor2)
    builder.add_node(solvent1)
    
    builder.add_relationship(steps[0], "usesPrecursor", precursor1)
    builder.add_relationship(steps[0], "usesPrecursor", precursor2)
    builder.add_relationship(steps[0], "usesSolvent", solvent1)
    
    # 숙성 조건
    aging_cond = Node("Condition", "aging_cond", "숙성 조건")
    aging_cond.add_data_property("hasTemperature", 80.0, XSD.float)
    aging_cond.add_data_property("hasDuration", "24 hours", XSD.string)
    builder.add_node(aging_cond)
    builder.add_relationship(steps[1], "performedUnder", aging_cond)
    
    # 결정화 조건
    cryst_cond = Node("Condition", "cryst_cond", "결정화 조건")
    cryst_cond.add_data_property("hasTemperature", 180.0, XSD.float)
    cryst_cond.add_data_property("hasPressure", 10.0, XSD.float)
    cryst_cond.add_data_property("hasDuration", "48 hours", XSD.string)
    builder.add_node(cryst_cond)
    builder.add_relationship(steps[2], "performedUnder", cryst_cond)
    
    # 소성 조건
    calc_cond = Node("Condition", "calc_cond", "소성 조건")
    calc_cond.add_data_property("hasTemperature", 550.0, XSD.float)
    calc_cond.add_data_property("hasDuration", "6 hours", XSD.string)
    builder.add_node(calc_cond)
    builder.add_relationship(steps[3], "performedUnder", calc_cond)
    
    # 최종 생성물
    product = Node("Product", "zsm5_product", "ZSM-5 제올라이트 생성물")
    builder.add_node(product)
    builder.add_relationship(steps[-1], "producesProduct", product)
    
    builder.print_summary()
    builder.save("./output/output_graph_complex.rdf", format='xml')
    
    return builder


if __name__ == "__main__":
    # 예제 실행
    print("\n🔬 RDF 그래프 구축 도구 실행\n")
    
    # 기본 예제
    builder1 = example_basic()
    
    # 복잡한 예제
    builder2 = example_complex()
    
    print("\n✅ 완료! 생성된 파일:")
    print("  - ./output/output_graph_basic.rdf")
    print("  - ./output/output_graph_complex.rdf")