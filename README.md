# 🧠 Incident Memory Agent (Hindsight Hackathon)

An on-call AI agent for SRE teams that **remembers every production incident** — symptoms, root cause,
the fix that worked, and the fixes that *wasted time* — and uses that memory to triage new alerts.

**Problem statement:** Engineering & DevOps → *Incident Response Agent*.
**Business case:** when production is down, every minute costs money. A stateless LLM gives generic
advice ("scale up the pods!"); an agent with team memory knows scaling pods made INC-2011 worse.

## How Hindsight is used (memory is the star)
| Hindsight API | Where | Purpose |
|---|---|---|
| `create_bank` (mission, retain_mission, disposition) | `memory.ensure_bank` | Bank tuned to extract root causes, fixes and failed approaches |
| `retain` (timestamp, document_id, metadata) | `memory.retain_incident` | Every postmortem and every *live resolution* becomes memory |
| `recall` | `memory.recall_similar` | Multi-strategy retrieval of similar past incidents (shown as evidence in UI) |
| `reflect` | `memory.reflect_insight` | Reasoning over patterns ("this is the 3rd pool exhaustion after a deploy") |

**Learning loop:** engineer resolves an incident → "Teach the agent" form → `retain` → next similar alert is
answered better. It also records whether the agent's own suggestion helped.

## Run it
```bash
pip install -r requirements.txt
cp .env.example .env        # add GROQ_API_KEY + Hindsight URL/key
# Hindsight: Cloud (ui.hindsight.vectorize.io, promo MEMHACK99) or local Docker (see hindsight docs)
python app.py               # http://localhost:5000
```

## 90-second demo script (the learning curve)
1. **Empty memory** → click *Load demo alert* → *Triage*. Both columns are generic (bank has no history).
2. `python seed.py` (11 realistic incidents from Mar–Aug 2026, retained with timestamps).
3. **Triage the same alert again.** Left stays generic (may suggest scaling pods). Right recalls
   INC-2011 / 2031 / 2044 / 2088: *roll back first, do NOT scale pods or raise pool size*, with cited IDs.
4. **Teach it:** fill the resolve form (e.g. root cause "retry worker held connections during HTTP calls")
   → *Retain*. Trigger a similar alert → the new incident now appears in the evidence.

## Structure
`app.py` Flask API/UI · `agent.py` triage (with/without memory) · `memory.py` Hindsight wrapper ·
`seed_data.py` synthetic history · `seed.py` loader · `static/index.html` UI.
