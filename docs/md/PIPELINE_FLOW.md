# RAG + Agent 파이프라인 전체 흐름도

> 2026-06-26 | `feature/agent-polish` 기준

## 전체 아키텍처

```mermaid
flowchart TB
    subgraph config["📋 config.yaml"]
        direction TB
        C1["rag.retriever<br/>rag.answerer<br/>rag.embedding"]
        C2["agent.enabled"]
        C3["agent.chatbot.enabled"]
    end

    subgraph branch["🔀 실행 경로 분기"]
        B1["agent.enabled<br/>= false"]
        B2["agent.enabled<br/>= true<br/>chatbot = false"]
        B3["agent.enabled<br/>= true<br/>chatbot = true"]
    end

    subgraph rag["📦 기존 RAG 파이프라인"]
        direction LR
        I["ingest<br/>문서 → chunk → embedding"]
        R["retrieve<br/>질문 → top-k 검색"]
        A["answer<br/>근거 → 답변 + citation"]
        E["evaluate<br/>hit_rate, judge_correct"]
        I --> R --> A --> E
    end

    subgraph agent["🤖 Agent 모드"]
        direction TB
        P1["Phase 1: extract<br/>└ extract_facts"]
        P2["Phase 2: decide<br/>└ decide_participation<br/>(depends_on: extract)"]
        ST["state dict<br/>input_from 전달"]
        OUT1["agent_state.jsonl<br/>agent_metrics.json"]
        P1 --> ST --> P2 --> OUT1
    end

    subgraph chatbot["💬 챗봇 모드"]
        direction TB
        SEL["LLM Tool 선택<br/>extract_facts?<br/>decide_participation?"]
        EXEC["Tool.run()<br/>retriever → answerer"]
        HIST["history 저장<br/>max_history=10"]
        OUT2["reply + citation"]
        SEL --> EXEC --> OUT2
        OUT2 -.-> HIST -.-> SEL
    end

    C2 --> B1
    C2 --> B2
    C2 --> B3
    B1 --> rag
    B2 --> agent
    B3 --> chatbot
```

## RAG 파이프라인 (agent.enabled = false)

```mermaid
flowchart LR
    DOC[📄 원본 문서<br/>txt/pdf/docx/hwp/csv]
    ING[🔧 ingest<br/>chunk_size=500<br/>overlap=80]
    CHUNK[📦 chunks.csv]
    EMBED[🧮 embeddings.jsonl]
    Q[❓ 질문]
    RET[🔍 retrieve<br/>keyword/semantic/hybrid]
    TOPK[📋 top-k chunks]
    ANS[💬 answer<br/>extractive/openai/ollama]
    CIT[📎 citation]
    EVAL[📊 evaluate<br/>hit_rate, judge]
    
    DOC --> ING --> CHUNK --> EMBED
    Q --> RET --> TOPK --> ANS --> CIT
    EMBED --> RET
    ANS --> EVAL
```

## Agent 모드 (agent.enabled = true, chatbot = false)

```mermaid
flowchart TB
    Q["❓ 질문: '참여해도 될까?'"]
    
    subgraph PHASE1["Phase: extract"]
        T1["🔧 Tool: extract_facts"]
        T1_R["retriever → chunks"]
        T1_A["answerer → structured_output"]
        T1_O["{예산: 5억, 자격: SW사업자, ...}"]
    end
    
    subgraph PHASE2["Phase: decide (depends_on: extract)"]
        T2["🔧 Tool: decide_participation"]
        T2_CTX["context ← extract_facts 결과"]
        T2_R["retriever → chunks"]
        T2_A["answerer → structured_output"]
        T2_O["{참여여부: true, 근거: ..., 리스크: [...]}"]
    end
    
    STATE["📊 agent_state.jsonl<br/>agent_metrics.json"]
    
    Q --> T1 --> T1_R --> T1_A --> T1_O
    T1_O -->|"input_from"| T2_CTX
    T2_CTX --> T2 --> T2_R --> T2_A --> T2_O
    T1_O --> STATE
    T2_O --> STATE
```

## 챗봇 모드 (agent.enabled = true, chatbot = true)

```mermaid
flowchart TB
    U["👤 사용자: '예산 얼마야?'"]
    LLM["🧠 LLM Tool 선택<br/>gpt-4o-mini / ollama"]
    TOOLS["사용 가능한 도구:<br/>- extract_facts<br/>- decide_participation<br/>- scan_clauses"]
    CHOOSE["→ extract_facts 선택<br/>question: '예산은 얼마인가?'"]
    EXEC["⚡ Tool.run()<br/>retriever → answerer"]
    REPLY["💬 '예산은 5억원입니다.'<br/>📎 p.8 · 2.3 예산 안내"]
    HIST["📝 history 저장<br/>다음 질문 컨텍스트로"]
    
    U --> LLM
    TOOLS --> LLM
    LLM --> CHOOSE --> EXEC --> REPLY --> HIST
    HIST -.->|"context"| LLM
```

## 데이터 흐름 요약

```mermaid
flowchart LR
    subgraph input["입력"]
        D[📄 RFP 문서 100건<br/>data_list.csv]
        Q[❓ 질문]
    end
    subgraph process["처리"]
        ING[ingest → chunks.csv<br/>embeddings.jsonl]
        AG[Agent / Chatbot / RAG]
    end
    subgraph output["산출물"]
        O1[answers.jsonl<br/>retrieval_results.jsonl]
        O2[agent_state.jsonl<br/>agent_metrics.json]
        O3[metrics.json<br/>evaluation_results.csv]
    end
    
    D --> ING --> AG
    Q --> AG
    AG --> O1
    AG --> O2
    AG --> O3
```

## 실행 명령어

```bash
# RAG 기본
python scripts/run_rag_chat.py --config rag_langchain.yaml --question "예산?"

# Agent 모드 (Phase DAG)
python scripts/run_rag_agent.py --config agent/agent_lplus.yaml --question "참여해도 될까?"

# 챗봇 모드 (대화형)
python scripts/run_rag_agent.py --config agent/agent_lplus.yaml

# Agent 평가
python scripts/run_rag_agent.py --config agent/agent_lplus.yaml --evaluate
```
