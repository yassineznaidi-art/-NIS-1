from nis.memory import SUBSTRATE
from pathlib import Path
import json, time

# Reset memory stores for clean run
import os
base = Path("/home/user/nis-mvv/data/memory")
for f in base.glob("*.json"):
    try:
        f.unlink()
    except: pass
# Re-init
from nis.memory import MemorySubstrate
substrate = MemorySubstrate()

# S3 Preferences [REAL]
substrate.set_preference("tone_preference", "warm")
substrate.set_preference("proactive_level", 0)
substrate.set_preference("language", "en")
# Add concise preference
substrate.set_preference("concise", True)
print("S3 prefs set")

# S4 LTM [REAL] — add Helios project memory and team list
substrate.add_ltm("helios_project", "Helios is a solar tracker project; spec v2 efficiency 21.5%, launch Q2 2026, team Alice,Bob,Carol,Dan,Eve", provenance="Project Memory 2026-06-10 manual", confidence=0.8)
substrate.add_ltm("team_list", ["Alice","Bob","Carol","Dan","Eve"], provenance="Project Memory 2026-09-02 team sync", confidence=0.7)
substrate.add_ltm("helios_spec_v2", {"efficiency": "21.5%", "version": "v2", "date": "2026-06-10"}, provenance="S4 2026-06-10", confidence=0.8)
# Add EU AI Act general knowledge (stale) — v0.3-P1 correction: timestamp must be 2024-12-01 not now
substrate.add_ltm("eu_ai_act_general", "EU AI Act is regulation; details pre-2025", provenance="S4 2024-12-01", confidence=0.6)
# CORRECTION v0.3-P1: patch timestamp to 2024-12-01 and add provenance record (freshness will be stale <0.3, triggers web_search)
import datetime
try:
    correction_ts = datetime.datetime(2024, 12, 1, tzinfo=datetime.timezone.utc).timestamp()
    import json
    s4_path = Path("/home/user/nis-mvv/data/memory/S4_ltm.json")
    data = json.loads(s4_path.read_text(encoding="utf-8"))
    for entry in data:
        if entry.get("key") == "eu_ai_act_general":
            entry["timestamp"] = correction_ts
            entry["provenance"] = "S4 2024-12-01 [CORRECTED v0.3-P1 2026-09-22: timestamp fixed from 2026-09-22(now) to 2024-12-01 to restore stale freshness 0.08; original was bug where add_ltm uses time.now]"
            entry["correction_record"] = {"fixed_at": time.time(), "fixed_by": "setup_memory.py v0.3-P1", "old_timestamp_was_now": True, "new_timestamp": correction_ts, "freshness_expected": "~0.08 at 2026-09-22 (age 660d, half 180d)", "reason": "eu_ai_act_general must be stale to trigger web_search for 2025-2026 enforcement dates, not fresh 1.0"}
            break
    s4_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    # Also write standalone correction log
    corr_path = Path("/home/user/nis-mvv/data/memory/correction_eu_ai_act.json")
    corr_path.write_text(json.dumps({"key": "eu_ai_act_general", "correction": entry["correction_record"], "provenance": entry["provenance"], "timestamp": correction_ts}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Corrected eu_ai_act_general timestamp to 2024-12-01 ({correction_ts}) freshness ~0.08")
except Exception as e:
    print(f"Correction failed: {e}")
print("S4 LTM set")

# Create Helios spec PDF mock file (as text, will be read via read_file)
helios_content = """Helios Solar Tracker — Spec Sheet (Project Helios)
Version 3 — 2026-09-15
Efficiency: 22% (p.4)
Architecture: Dual-axis tracker with AI optimization
Launch: Q2 2026
Team: Alice, Bob, Carol, Dan, Eve
Notes: Efficiency improved from 21.5% (v2) to 22% (v3) via new coating.
"""
Path("/home/user/helios_spec.pdf").write_text(helios_content, encoding="utf-8")
Path("/home/user/helios_spec.txt").write_text(helios_content, encoding="utf-8")
print("Created /home/user/helios_spec.pdf and .txt")

# Create a project file for S5 search
Path("/home/user/project_helios.md").write_text("# Project Helios\n\nGoals: solar tracker 22% efficiency\nTeam: Alice, Bob, Carol, Dan, Eve\nStatus: v3 spec 2026-09-15", encoding="utf-8")
print("Created project_helios.md")

# Verify
print("S4 hits:", len(substrate.get_ltm()))
print("S3 prefs:", substrate.get_preferences())
print("Setup done")
