import json
import asyncio
from typing import List
from langchain_core.documents import Document
from app.services.vector_store_service import add_documents_to_store

def _flatten_symptoms(symptoms: list) -> str:
    parts: List[str] = []
    for s in symptoms or []:
        part = s.get("部位")
        if "阶段" in s:
            for st in s["阶段"]:
                parts.append(f"[{part}-{st.get('阶段名称','')}] {st.get('描述','')}")
        elif "类型" in s:
            for tp in s["类型"]:
                parts.append(f"[{part}-{tp.get('类型名称','')}] {tp.get('特征','')}")
        else:
            if part:
                parts.append(f"[{part}]")
    return "\n".join(parts) if parts else "N/A"

def _flatten_methods(methods: list) -> str:
    out: List[str] = []
    for m in methods or []:
        # 情况1：纯字符串
        if isinstance(m, str):
            out.append(m)
            continue
        # 情况2：标准结构 { 方法分类, 具体措施 }
        if isinstance(m, dict):
            cat = m.get("方法分类") or m.get("分类") or "措施"
            steps = m.get("具体措施")
            if isinstance(steps, list):
                for step in steps:
                    out.append(f"{cat}: {step}")
                continue
            # 情况3：合并形 { 方法分类, 防治方法: { 农业/生物/化学... } }
            sub = m.get("防治方法")
            if isinstance(sub, dict):
                for subcat, items in sub.items():
                    if isinstance(items, list):
                        for it in items:
                            out.append(f"{cat}-{subcat}: {it}")
                    elif isinstance(items, str):
                        out.append(f"{cat}-{subcat}: {items}")
                continue
            # 其他字典形态：尝试展平所有键
            for k, v in m.items():
                if isinstance(v, list):
                    for it in v:
                        out.append(f"{k}: {it}")
                elif isinstance(v, str):
                    out.append(f"{k}: {v}")
    return "\n".join(out) if out else "N/A"

def load_and_process_data(file_path: str) -> List[Document]:
    """Loads data from the JSON file (中文字段) and converts to Documents."""
    documents: List[Document] = []
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for item in data:
        name = item.get("名称", "N/A")
        category = item.get("分类", "N/A")
        aliases = ", ".join(item.get("别名", [])) if isinstance(item.get("别名"), list) else str(item.get("别名", ""))
        symptoms = _flatten_symptoms(item.get("症状", []))
        pathogen = item.get("病原", {}) or {}
        pathogen_txt = f"类型: {pathogen.get('类型','N/A')}；特性: {pathogen.get('特性','N/A')}；传播途径: {', '.join(pathogen.get('传播途径', [])) if isinstance(pathogen.get('传播途径'), list) else pathogen.get('传播途径','')}"
        occurrence = item.get("发生规律", {}) or {}
        occ_txt = f"寄主范围: {', '.join(occurrence.get('寄主范围', [])) if isinstance(occurrence.get('寄主范围'), list) else occurrence.get('寄主范围','')}；传播方式: {', '.join(occurrence.get('传播方式', [])) if isinstance(occurrence.get('传播方式'), list) else occurrence.get('传播方式','')}；流行条件: {occurrence.get('流行条件','')}"
        methods = _flatten_methods(item.get("防治方法", []))

        content = f"""
名称: {name}
分类: {category}
别名: {aliases}
症状: {symptoms}
病原: {pathogen_txt}
发生规律: {occ_txt}
防治方法: {methods}
"""

        metadata = {"name": name, "type": category}
        documents.append(Document(page_content=content.strip(), metadata=metadata))

    return documents

async def main():
    print("Starting knowledge base ingestion...")
    # The path should be relative to the root of the `backend` directory
    # As you provided it in the root, we go up one level.
    json_file_path = "../结构化数据.json" 
    
    documents = load_and_process_data(json_file_path)
    if not documents:
        print("No documents found to ingest.")
        return
        
    # Use a thread to call sync function without blocking event loop
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, add_documents_to_store, documents)
    print("Knowledge base ingestion complete.")

if __name__ == "__main__":
    asyncio.run(main())
