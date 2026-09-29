"""Thin wrapper around Hindsight. All memory operations of the agent live here."""
import asyncio
import os
from datetime import datetime

from dotenv import load_dotenv
from hindsight_client import Hindsight

load_dotenv()

BANK_ID = os.getenv("HINDSIGHT_BANK_ID", "incident-response-agent")

MISSION = (
    "I am the on-call memory of an SRE team. I remember every production incident: "
    "symptoms, root cause, the fix that worked, and - just as important - the fixes "
    "that were tried and FAILED or wasted time. I track which services and deploys "
    "repeatedly cause trouble and which runbooks are actually effective."
)
RETAIN_MISSION = (
    "Extract: service names, deploy versions, error messages, root causes, resolution "
    "steps, failed approaches, time-to-resolve, and whether the agent's suggestion helped."
)

client = Hindsight(
    base_url=os.getenv("HINDSIGHT_BASE_URL", "http://localhost:8888"),
    api_key=os.getenv("HINDSIGHT_API_KEY") or None,
    timeout=90.0,
)


def ensure_bank() -> None:
    """Create the memory bank (safe to call repeatedly)."""
    try:
        client.create_bank(
            bank_id=BANK_ID,
            name="SRE Incident Memory",
            mission=MISSION,
            retain_mission=RETAIN_MISSION,
            disposition={"skepticism": 4, "literalism": 3, "empathy": 2},
        )
    except Exception as e:  # already exists / older server - not fatal
        print(f"[memory] create_bank note: {e}")


def incident_to_text(inc: dict) -> str:
    """Turn a structured incident into a narrative Hindsight can extract facts from."""
    parts = [
        f"Incident {inc['id']} on service {inc['service']}: {inc['title']}.",
        f"Symptoms: {inc['symptoms']}",
        f"Root cause: {inc['root_cause']}",
        f"Resolution that worked: {inc['resolution']}",
    ]
    if inc.get("failed"):
        parts.append(f"Approaches that did NOT work or wasted time: {inc['failed']}")
    if inc.get("agent_feedback"):
        parts.append(f"The incident agent's suggested runbook was: {inc['agent_feedback']}.")
    parts.append(f"Time to resolve: {inc['ttr_minutes']} minutes. Resolved by {inc['engineer']}.")
    return " ".join(parts)


def _run(fn):
    """Run one Hindsight call on its own event loop + fresh client.
    Safe from any thread (Flask workers, ThreadPoolExecutor)."""
    async def main():
        c = Hindsight(
            base_url=os.getenv("HINDSIGHT_BASE_URL", "http://localhost:8888"),
            api_key=os.getenv("HINDSIGHT_API_KEY") or None,
            timeout=90.0,
        )
        try:
            return await fn(c)
        finally:
            await c.aclose()
    return asyncio.run(main())


def retain_incident(inc: dict, when: datetime | None = None) -> None:
    _run(lambda c: c.aretain(
        bank_id=BANK_ID,
        content=incident_to_text(inc),
        context="production incident postmortem",
        timestamp=when or inc.get("date") or datetime.utcnow(),
        document_id=inc["id"],  # re-seeding updates instead of duplicating
        metadata={"service": inc["service"]},
        retain_async=False,
    ))


def recall_similar(query: str, max_tokens: int = 3000) -> list[dict]:
    res = _run(lambda c: c.arecall(
        bank_id=BANK_ID, query=query, budget="mid", max_tokens=max_tokens))
    return [{"text": r.text, "type": getattr(r, "type", "memory")} for r in res.results]


def reflect_insight(alert: str) -> str:
    """Let Hindsight reason across memories (patterns, repeat offenders)."""
    ans = _run(lambda c: c.areflect(
        bank_id=BANK_ID,
        query=(
            "Given this new alert, which past incidents and recurring patterns are most "
            "relevant, what fixed them, and what wasted time?\n\nALERT:\n" + alert
        ),
        budget="low",
        context="on-call triage of a live production incident",
    ))
    return ans.text