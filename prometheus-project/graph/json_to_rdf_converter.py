"""
LLM JSON 출력을 RDF 그래프로 변환하는 도구 (리스트 구조 지원)
"""

import json
from rdflib import Namespace, XSD
from rdflib.namespace import RDF, RDFS
from typing import Dict, Any, List
import re

# 기존 모듈 import
from rdf_graph_builder import Node, Edge, RDFGraphBuilder


class JSONtoRDFConverter:
    """
    LLM의 JSON 출력을 RDF 그래프로 변환
    """
    
    def __init__(self, ontology_file: str = None):
        """
        Args:
            ontology_file: 기존 온톨로지 파일 경로
        """
        self.builder = RDFGraphBuilder(ontology_file)
        self.nodes_cache = {}  # 중복 노드 방지용 캐시
    
    def convert_json_to_graph(self, json_file: str) -> RDFGraphBuilder:
        """
        JSON 파일을 읽어서 RDF 그래프로 변환
        
        Args:
            json_file: JSON 파일 경로
            
        Returns:
            RDFGraphBuilder 객체
        """
        # JSON 파일 로드
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # extracted 섹션 가져오기
        extracted = data.get('extracted', {})
        
        # ✅ 리스트를 딕셔너리로 변환하는 헬퍼 함수
        def get_first_or_empty(key):
            """리스트면 첫 번째 요소, 아니면 그대로 반환"""
            value = extracted.get(key, [])
            if isinstance(value, list):
                return value[0] if value else {}
            return value
        
        # 1. InorganicMaterial 생성
        inorg_materials = extracted.get('InorganicMaterial', [])
        if isinstance(inorg_materials, list) and inorg_materials:
            # 리스트의 첫 번째 항목 사용
            material_node = self._create_material_node(inorg_materials[0])
        elif isinstance(inorg_materials, dict):
            # 이미 딕셔너리면 그대로 사용
            material_node = self._create_material_node(inorg_materials)
        else:
            material_node = None
        
        # 2. SynthesisMethod 생성
        synthesis_methods = extracted.get('SynthesisMethod', [])
        if isinstance(synthesis_methods, list) and synthesis_methods:
            synthesis_method = synthesis_methods[0]
        elif isinstance(synthesis_methods, dict):
            synthesis_method = synthesis_methods
        else:
            synthesis_method = {}
        
        method_node = self._create_method_node(synthesis_method)
        
        # 3. 재료와 방법 연결
        if material_node and method_node:
            self.builder.add_relationship(material_node, "hasSynthesisMethod", method_node)
        
        # 4. Steps 생성 및 연결
        # SynthesisStep은 extracted에 직접 리스트로 있을 수 있음
        steps = extracted.get('SynthesisStep', [])
        if not steps:
            # 또는 SynthesisMethod 안에 있을 수도 있음
            steps = synthesis_method.get('steps', [])
        
        if steps:
            step_nodes = self._create_step_nodes(steps, extracted)
            
            # 첫 번째 단계를 방법에 연결
            if step_nodes and method_node:
                self.builder.add_relationship(method_node, "consistOfStep", step_nodes[0])
        
        return self.builder
    
    def _create_material_node(self, material_data: Dict) -> Node:
        """InorganicMaterial 노드 생성"""
        name = material_data.get('hasName', 'Unknown_Material')
        
        # 안전한 ID 생성 (특수문자 제거)
        safe_id = self._make_safe_id(name)
        
        material = Node(
            node_type="InorganicMaterial",
            node_id=safe_id,
            label=name
        )
        
        # 속성 추가
        if material_data.get('hasAcronym'):
            material.add_data_property("hasAcronym", material_data['hasAcronym'], XSD.string)
        
        if material_data.get('hasPhase'):
            material.add_data_property("hasPhase", material_data['hasPhase'], XSD.string)
        
        self.builder.add_node(material)
        return material
    
    def _create_method_node(self, method_data: Dict) -> Node:
        """SynthesisMethod 노드 생성"""
        method_id = method_data.get('hasID', method_data.get('id', 1))
        
        method = Node(
            node_type="SynthesisMethod",
            node_id=f"method_{method_id}",
            label=f"합성 방법 {method_id}"
        )
        
        self.builder.add_node(method)
        return method
    
    def _create_step_nodes(self, steps: List[Dict], extracted: Dict) -> List[Node]:
        """
        합성 단계 노드들 생성 및 연결
        
        Args:
            steps: SynthesisStep 리스트
            extracted: 전체 extracted 데이터 (Precursor, Solvent 등 참조용)
        """
        step_nodes = []
        
        # Precursor, Solvent, Additive를 미리 인덱스화
        precursors_map = self._build_reference_map(extracted.get('Precursor', []))
        solvents_map = self._build_reference_map(extracted.get('Solvent', []))
        additives_map = self._build_reference_map(extracted.get('Additive', []))
        products_map = self._build_reference_map(extracted.get('Product', []))
        conditions_map = self._build_reference_map(extracted.get('Condition', []))
        
        for step_data in steps:
            step_num = step_data.get('step_number', step_data.get('id', 0))
            action = step_data.get('hasAction', step_data.get('action', 'unknown'))
            
            # Step 노드 생성
            step_node = Node(
                node_type="SynthesisStep",
                node_id=f"step_{step_num}",
                label=f"{step_num}. {action}"
            )
            
            self.builder.add_node(step_node)
            step_nodes.append(step_node)
            
            # Precursor 연결
            precursor_ids = step_data.get('usesPrecursor', [])
            if not isinstance(precursor_ids, list):
                precursor_ids = [precursor_ids]
            
            for pid in precursor_ids:
                if pid in precursors_map:
                    precursor_data = precursors_map[pid]
                    precursor_node = self._get_or_create_precursor(
                        precursor_data.get('hasName', str(pid))
                    )
                    self.builder.add_relationship(step_node, "usesPrecursor", precursor_node)
            
            # Solvent 연결
            solvent_ids = step_data.get('usesSolvent', [])
            if not isinstance(solvent_ids, list):
                solvent_ids = [solvent_ids]
            
            for sid in solvent_ids:
                if sid in solvents_map:
                    solvent_data = solvents_map[sid]
                    solvent_node = self._get_or_create_solvent(
                        solvent_data.get('hasName', str(sid))
                    )
                    self.builder.add_relationship(step_node, "usesSolvent", solvent_node)
            
            # Additive 연결
            additive_ids = step_data.get('usesAdditive', [])
            if not isinstance(additive_ids, list):
                additive_ids = [additive_ids]
            
            for aid in additive_ids:
                if aid in additives_map:
                    additive_data = additives_map[aid]
                    additive_node = self._get_or_create_additive(
                        additive_data.get('hasName', str(aid))
                    )
                    self.builder.add_relationship(step_node, "usesAddictive", additive_node)
            
            # Condition 연결
            condition_id = step_data.get('performedUnder')
            if condition_id and condition_id in conditions_map:
                condition_data = conditions_map[condition_id]
                condition_node = self._create_condition_node(step_num, condition_data)
                self.builder.add_relationship(step_node, "performedUnder", condition_node)
            
            # Product 연결
            product_id = step_data.get('producesProduct')
            if product_id and product_id in products_map:
                product_data = products_map[product_id]
                product_node = self._get_or_create_product(
                    product_data.get('hasName', str(product_id))
                )
                self.builder.add_relationship(step_node, "producesProduct", product_node)
        
        # nextStep 관계 연결
        for i in range(len(step_nodes) - 1):
            self.builder.add_relationship(step_nodes[i], "nextStep", step_nodes[i + 1])
        
        return step_nodes
    
    def _build_reference_map(self, items: List[Dict]) -> Dict[str, Dict]:
        """
        리스트를 id를 키로 하는 딕셔너리로 변환
        
        Args:
            items: 항목 리스트 (각 항목은 'id' 키를 가짐)
            
        Returns:
            {id: item_data} 형태의 딕셔너리
        """
        if not isinstance(items, list):
            return {}
        
        result = {}
        for item in items:
            if isinstance(item, dict):
                item_id = item.get('id', item.get('hasID'))
                if item_id:
                    result[item_id] = item
        
        return result
    
    def _get_or_create_precursor(self, name: str) -> Node:
        """Precursor 노드 가져오기 또는 생성 (캐시 사용)"""
        cache_key = f"Precursor_{name}"
        
        if cache_key in self.nodes_cache:
            return self.nodes_cache[cache_key]
        
        safe_id = self._make_safe_id(name)
        node = Node(
            node_type="Precursor",
            node_id=safe_id,
            label=name
        )
        self.builder.add_node(node)
        self.nodes_cache[cache_key] = node
        return node
    
    def _get_or_create_solvent(self, name: str) -> Node:
        """Solvent 노드 가져오기 또는 생성"""
        cache_key = f"Solvent_{name}"
        
        if cache_key in self.nodes_cache:
            return self.nodes_cache[cache_key]
        
        safe_id = self._make_safe_id(name)
        node = Node(
            node_type="Solvent",
            node_id=safe_id,
            label=name
        )
        self.builder.add_node(node)
        self.nodes_cache[cache_key] = node
        return node
    
    def _get_or_create_additive(self, name: str) -> Node:
        """Additive 노드 가져오기 또는 생성"""
        cache_key = f"Additive_{name}"
        
        if cache_key in self.nodes_cache:
            return self.nodes_cache[cache_key]
        
        safe_id = self._make_safe_id(name)
        node = Node(
            node_type="Additive",
            node_id=safe_id,
            label=name
        )
        self.builder.add_node(node)
        self.nodes_cache[cache_key] = node
        return node
    
    def _get_or_create_product(self, name: str) -> Node:
        """Product 노드 가져오기 또는 생성"""
        cache_key = f"Product_{name}"
        
        if cache_key in self.nodes_cache:
            return self.nodes_cache[cache_key]
        
        safe_id = self._make_safe_id(name)
        node = Node(
            node_type="Product",
            node_id=safe_id,
            label=name
        )
        self.builder.add_node(node)
        self.nodes_cache[cache_key] = node
        return node
    
    def _create_condition_node(self, step_num: int, conditions: Dict) -> Node:
        """Condition 노드 생성"""
        node = Node(
            node_type="Condition",
            node_id=f"condition_step_{step_num}",
            label=f"조건 (단계 {step_num})"
        )
        
        # 온도
        temp = conditions.get('hasTemperature', conditions.get('temperature'))
        if temp is not None:
            try:
                node.add_data_property("hasTemperature", float(temp), XSD.float)
            except:
                pass
        
        # 시간
        time_val = conditions.get('hasDuration', conditions.get('time'))
        if time_val is not None:
            node.add_data_property("hasDuration", str(time_val), XSD.string)
        
        # 압력
        pressure = conditions.get('hasPressure', conditions.get('pressure'))
        if pressure is not None:
            try:
                node.add_data_property("hasPressure", float(pressure), XSD.float)
            except:
                pass
        
        # pH
        ph = conditions.get('haspH', conditions.get('pH'))
        if ph is not None:
            node.add_data_property("haspH", str(ph), XSD.string)
        
        self.builder.add_node(node)
        return node
    
    def _make_safe_id(self, text: str) -> str:
        """
        안전한 ID 생성 (특수문자 제거, URI에 사용 가능하게)
        
        Args:
            text: 원본 텍스트
            
        Returns:
            안전한 ID 문자열
        """
        # 특수문자를 언더스코어로 변경
        safe = re.sub(r'[^\w\s-]', '', str(text))
        safe = re.sub(r'[-\s]+', '_', safe)
        return safe.strip('_')