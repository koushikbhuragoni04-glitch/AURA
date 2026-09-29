"""Load the historical incidents into Hindsight:  python seed.py"""
import memory
from seed_data import INCIDENTS

memory.ensure_bank()
for inc in INCIDENTS:
    memory.retain_incident(inc, when=inc["date"])
    print(f"retained {inc['id']}  {inc['service']:<16} {inc['title']}")
print(f"\nDone - {len(INCIDENTS)} incidents in bank '{memory.BANK_ID}'.")
