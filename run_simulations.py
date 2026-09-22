#!/usr/bin/env python3
"""
Run 5 canonical simulations through MVV orchestrator
Traces: INPUT → INTENT → MEMORY → DELIBERATION → PLAN → TOOL_DECISION → PERMISSION → EXECUTION → VERIFICATION → RESPONSE
"""
import sys, json, time
sys.path.insert(0, "/home/user/nis-mvv")

from nis.orchestrator import ORCHESTRATOR
from nis.incp import GLOBAL_TRACE
from pathlib import Path

def run_sim(name, raw_input, attachments=None, expected_level=None):
    attachments = attachments or []
    print(f"\n{'#'*90}")
    print(f"SIMULATION: {name}")
    print(f"INPUT: {raw_input[:120]}")
    if attachments:
        print(f"ATTACHMENTS: {attachments}")
    print(f"EXPECTED: {expected_level}")
    print(f"{'#'*90}")
    result = ORCHESTRATOR.run_turn(raw_input, attachments)
    # Print trace summary
    print(f"\n→ INTENT: {result['intent'].get('primary_intent')} (ambiguity {result['intent'].get('ambiguity_score')}, consequence {result['intent'].get('consequence_score')}) slots={result['intent'].get('slots')}")
    print(f"→ MEMORY: {len(result['memory'].get('hits',[]))} hits, {len(result['memory'].get('appendix',[]))} appendix, conflicts={result['memory'].get('conflicts')}")
    for h in result['memory'].get('hits',[])[:2]:
        print(f"   - {h['store']}:{h['key'][:40]} freshness {h['freshness']:.2f} conf {h['confidence']:.2f}")
    print(f"→ DELIBERATION: {result['deliberation'].get('level')} score {result['deliberation'].get('complexity_score')} axes {result['deliberation'].get('axes')}")
    if result.get('plan'):
        steps = result['plan'].get('steps',[])
        print(f"→ PLAN: {len(steps)} steps — " + " → ".join([f"{s['id']}:{s['tool_hint'] or 'no-tool'}" for s in steps]))
        if result['plan'].get('fallback_plan'):
            print(f"   fallback: {result['plan']['fallback_plan']}")
    else:
        print(f"→ PLAN: none (direct or blocked)")
    if result.get('tool_decision'):
        print(f"→ TOOL_DECISION: {result['tool_decision']}")
    else:
        print(f"→ TOOL_DECISION: none")
    print(f"→ PERMISSION: {result.get('permission',{}).get('verdict')} — {result.get('permission',{}).get('reasons',[])[:1]}")
    if result.get('execution'):
        print(f"→ EXECUTION: {result['execution'].get('status')} tool {result['execution'].get('tool')} provenance {result['execution'].get('provenance')} mock={result['execution'].get('mock',False)}")
        if result['execution'].get('fetch_results'):
            for fr in result['execution']['fetch_results']:
                print(f"   fetch: {fr.get('provenance')} status {fr.get('status')} mock={fr.get('mock',False)}")
    else:
        print(f"→ EXECUTION: none")
    print(f"→ VERIFICATION: {result.get('verification',{}).get('verdict')} issues {result.get('verification',{}).get('issues',[])[:2]}")
    print(f"\n→ FINAL RESPONSE:\n{result['response'][:900]}")
    print(f"\n--- TRACE ID: {result['trace_id']} ---")
    # Also print GLOBAL_TRACE detailed
    GLOBAL_TRACE.print_trace(result['trace_id'])
    return result

if __name__ == "__main__":
    results = []
    # Simulation 1: L0 Trivial — What's the time?
    results.append(run_sim(
        "1 — L0 Trivial: What's the time right now?",
        "What's the time right now?",
        expected_level="L0"
    ))
    time.sleep(0.5)
    # Simulation 2: L1 Simple — poem
    results.append(run_sim(
        "2 — L1 Simple: Write a short poem about the sea for my daughter",
        "Write a short poem about the sea for my daughter",
        expected_level="L1"
    ))
    time.sleep(0.5)
    # Simulation 3: L2 Analytical — Summarize PDF + check Helios
    results.append(run_sim(
        "3 — L2 Analytical: Summarize PDF + Helios contradiction",
        "Summarize the PDF I just uploaded and tell me if it contradicts what you remember about Project Helios",
        attachments=["/home/user/helios_spec.pdf"],
        expected_level="L2"
    ))
    time.sleep(0.5)
    # Simulation 4: L3 Complex — EU AI Act + timeline image
    results.append(run_sim(
        "4 — L3 Complex: EU AI Act enforcement dates + timeline image",
        "Search the web for the latest EU AI Act enforcement dates and make me a timeline image",
        expected_level="L3"
    ))
    time.sleep(0.5)
    # Simulation 5: L4 Critical — Send email to entire team (permission-gated)
    results.append(run_sim(
        "5 — L4 Critical: Send email to entire team delaying launch 2 weeks",
        "Send an email to my entire team saying we’re delaying the launch by 2 weeks",
        expected_level="L4"
    ))

    # Save results
    Path("/home/user/nis-mvv/logs/simulations.json").parent.mkdir(parents=True, exist_ok=True)
    with open("/home/user/nis-mvv/logs/simulations.json","w",encoding="utf-8") as f:
        # Convert results to serializable (remove non-serializable)
        serializable = []
        for r in results:
            # Keep only key fields
            serializable.append({
                "input": r["input"],
                "intent": r["intent"],
                "deliberation": r["deliberation"],
                "memory_hits": len(r["memory"].get("hits",[])),
                "plan_steps": len(r["plan"].get("steps",[])) if r.get("plan") else 0,
                "tool_decision": r.get("tool_decision"),
                "permission": r.get("permission"),
                "execution": {"status": r["execution"].get("status"), "tool": r["execution"].get("tool"), "mock": r["execution"].get("mock",False), "provenance": r["execution"].get("provenance")} if r.get("execution") else None,
                "verification": r.get("verification"),
                "response_preview": r["response"][:400],
                "trace_id": r["trace_id"]
            })
        json.dump(serializable, f, indent=2, ensure_ascii=False)
    print("\nSimulations complete. Results saved to logs/simulations.json")
    # Also save full traces
    with open("/home/user/nis-mvv/logs/traces.json","w",encoding="utf-8") as f:
        all_traces = {}
        for r in results:
            tid = r["trace_id"]
            all_traces[tid] = GLOBAL_TRACE.to_dict(tid)
        json.dump(all_traces, f, indent=2, ensure_ascii=False)
    print("Traces saved to logs/traces.json")
