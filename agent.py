"""Incident triage agent: same LLM, with and without Hindsight memory."""
import os
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from dotenv import load_dotenv

import memory

load_dotenv()

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

FORMAT = """Answer in concise markdown with exactly these sections:
## Likely root cause
## Immediate actions (ordered)
## Do NOT do
## Confidence & escalation"""

BASE_SYSTEM = (
    "You are an SRE incident-response assistant helping the on-call engineer during a live "
    "production incident. Be specific, brief and actionable. " + FORMAT
)

MEMORY_SYSTEM = (
    "You are an SRE incident-response assistant with long-term memory of THIS team's past "
    "incidents. Use the retrieved memories as primary evidence. Cite incident IDs (e.g. INC-2031) "
    "ONLY if they appear in the memories - never invent IDs. Explicitly say which past approaches "
    "worked and which wasted time, and put those failed approaches under 'Do NOT do'. "
    "Add a final section '## Evidence from past incidents' listing the incident IDs you relied on "
    "with one line each. Be brief and actionable. " + FORMAT
)


def llm(system: str, user: str, retries: int = 2) -> str:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY is not set (see .env.example)")
    last = None
    for attempt in range(retries + 1):
        try:
            r = requests.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "model": MODEL,
                    "temperature": 0.2,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
                timeout=90,
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:  # rate limits / transient model errors
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"LLM call failed: {last}")


def triage_without_memory(alert: str) -> str:
    return llm(BASE_SYSTEM, f"LIVE ALERT:\n{alert}")


def triage_with_memory(alert: str) -> dict:
    with ThreadPoolExecutor(max_workers=2) as pool:
        f_recall = pool.submit(memory.recall_similar, alert)
        f_reflect = pool.submit(_safe_reflect, alert)
        memories, insight = f_recall.result(), f_reflect.result()

    if not memories and not insight:
        answer = llm(BASE_SYSTEM, f"LIVE ALERT:\n{alert}\n\n(No relevant past incidents found in memory.)")
    else:
        mem_block = "\n".join(f"- [{m['type']}] {m['text']}" for m in memories)
        answer = llm(
            MEMORY_SYSTEM,
            f"LIVE ALERT:\n{alert}\n\nRETRIEVED MEMORIES (Hindsight recall):\n{mem_block}\n\n"
            f"HINDSIGHT REFLECTION:\n{insight}",
        )
    return {"answer": answer, "memories": memories, "insight": insight}


def _safe_reflect(alert: str) -> str:
    try:
        return memory.reflect_insight(alert)
    except Exception as e:
        print(f"[agent] reflect failed: {e}")
        return ""


def triage(alert: str) -> dict:
    """Run both agents in parallel so the UI can show the before/after."""
    with ThreadPoolExecutor(max_workers=2) as pool:
        base = pool.submit(triage_without_memory, alert)
        mem = pool.submit(triage_with_memory, alert)
        return {"without_memory": base.result(), "with_memory": mem.result()}
