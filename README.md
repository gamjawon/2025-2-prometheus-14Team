<p align="center">
  <a href="https://github.com/hyun-jin891/AItom/tree/main">
    <img alt="AItom" title="AItom" src="asset/logo.png" width="450">
  </a>
</p>

<h1 align="center"> Inorganic Material Synthesis Method Chatbot </h1> <br>


# 🔬 Architectural Flow
AItom consists of three core layers:

1. **LLM-Based Structured Extraction**
2. **Ontology-Aligned Knowledge Graph Construction**
3. **Graph Retrieval-Augmented Generation (Graph RAG)**
4. **Transformer-MLP Architecture for Safety Check**

The system enables an end-to-end pipeline:

```
Raw Literature (PMID: 35614129)
↓
Ontology Design
↓
LLM Extraction
↓
Ontology Mapping
↓
Graph Database
↓
Graph Retrieval
↓
LLM Generation (Graph RAG) + Safety Check (Transformer-MLP)
```







