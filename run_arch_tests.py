#!/usr/bin/env python3
"""
Architectural Tests — 6 tests covering:
1. Simple (no tool, L0/L1)
2. Ambiguous (F-AMB, needs clarification)
3. Memory retrieval (S4/S5 hits, no tool)
4. Tool-required (read_file A0)
5. Permission-gated (ambiguous send, confirm_needed / clarify)
6. Proactive tick gated (N0.1 disabled by default)
Each asserts trace stages and logs results.
"""
import sys, json, time, pathlib
sys.path.insert(0, "/home/user/nis-mvv")

from nis.orchestrator import ORCHESTRATOR
from nis.incp import GLOBAL_TRACE

def assert_check(cond, msg):
    return (cond, msg)

def run_test(name, raw_input, attachments=None, expected=None):
    attachments = attachments or []
    result = ORCHESTRATOR.run_turn(raw_input, attachments)
    print(f"\n{'='*80}")
    print(f"TEST: {name}")
    print(f"INPUT: {raw_input!r}")
    print(f"→ INTENT: {result['intent'].get('primary_intent')} amb={result['intent'].get('ambiguity_score')} cons={result['intent'].get('consequence_score')} slots={result['intent'].get('slots')}")
    print(f"→ DELIBERATION: {result['deliberation'].get('level')} score={result['deliberation'].get('complexity_score')}")
    print(f"→ MEMORY hits: {len(result['memory'].get('hits',[]))} prov={result['memory'].get('provenance',[])[:2]}")
    print(f"→ PLAN steps: {len(result['plan'].get('steps',[])) if result.get('plan') else 0} tool_decision={result.get('tool_decision')}")
    print(f"→ PERMISSION: {result.get('permission',{}).get('verdict')} reasons={result.get('permission',{}).get('reasons',[])[:1]}")
    if result.get('execution'):
        print(f"→ EXECUTION: {result['execution'].get('status')} tool={result['execution'].get('tool')} mock={result['execution'].get('mock')} prov={result['execution'].get('provenance')}")
    print(f"→ VERIFICATION: {result.get('verification',{}).get('verdict')} issues={result.get('verification',{}).get('issues')}")
    print(f"→ RESPONSE preview: {result['response'][:400]!r}")

    checks = []
    exp = expected or {}
    # Check level if expected
    if "level" in exp:
        checks.append(assert_check(result['deliberation'].get('level') == exp["level"], f"Deliberation level expected {exp['level']} got {result['deliberation'].get('level')}"))
    if "level_in" in exp:
        checks.append(assert_check(result['deliberation'].get('level') in exp["level_in"], f"Level in {exp['level_in']} got {result['deliberation'].get('level')}"))
    if "memory_min_hits" in exp:
        checks.append(assert_check(len(result['memory'].get('hits',[])) >= exp["memory_min_hits"], f"Memory hits >= {exp['memory_min_hits']} got {len(result['memory'].get('hits',[]))}"))
    if "memory_max_hits" in exp:
        checks.append(assert_check(len(result['memory'].get('hits',[])) <= exp["memory_max_hits"], f"Memory hits <= {exp['memory_max_hits']} got {len(result['memory'].get('hits',[]))}"))
    if "tool_decision" in exp:
        got = result.get('tool_decision',{}).get('decision') if result.get('tool_decision') else None
        checks.append(assert_check(got == exp["tool_decision"], f"Tool decision expected {exp['tool_decision']} got {got}"))
    if "tool" in exp:
        got_tool = result.get('tool_decision',{}).get('tool') if result.get('tool_decision') else (result.get('execution',{}).get('tool') if result.get('execution') else None)
        # For memory retrieval, tool_decision is SKIP_TOOL, so tool None
        # For tool-required, tool_decision tool should match
        checks.append(assert_check(got_tool == exp["tool"], f"Tool expected {exp['tool']} got {got_tool}"))
    if "execution_status" in exp:
        checks.append(assert_check(result.get('execution',{}).get('status') == exp["execution_status"], f"Execution status expected {exp['execution_status']} got {result.get('execution',{}).get('status')}"))
    if "permission" in exp:
        checks.append(assert_check(result.get('permission',{}).get('verdict') == exp["permission"], f"Permission expected {exp['permission']} got {result.get('permission',{}).get('verdict')}"))
    if "response_contains" in exp:
        for substr in exp["response_contains"]:
            checks.append(assert_check(substr.lower() in result['response'].lower(), f"Response should contain '{substr}'"))
    if "response_not_contains" in exp:
        for substr in exp["response_not_contains"]:
            checks.append(assert_check(substr.lower() not in result['response'].lower(), f"Response should NOT contain '{substr}'"))
    if "verification" in exp:
        checks.append(assert_check(result.get('verification',{}).get('verdict') == exp["verification"], f"Verification expected {exp['verification']} got {result.get('verification',{}).get('verdict')}"))
    if "trace_has" in exp:
        # check that GLOBAL_TRACE has expected stages
        trace = GLOBAL_TRACE.to_dict(result['trace_id'])
        # to_dict returns list; handle both list and dict cases
        events = trace if isinstance(trace, list) else trace.get("events", [])
        stages = [e["stage"] for e in events]
        for s in exp["trace_has"]:
            checks.append(assert_check(s in stages, f"Trace should have stage {s}"))

    passed = all(c for c,_ in checks)
    for ok, msg in checks:
        print(f"  {'✓' if ok else '✗'} {msg}")
    print(f"Result: {'PASS' if passed else 'FAIL'}  trace={result['trace_id']}")
    return {"name": name, "input": raw_input, "passed": passed, "checks": [{"ok": ok, "msg": msg} for ok,msg in checks], "trace_id": result['trace_id'], "deliberation": result['deliberation'], "intent": result['intent'], "memory_hits": len(result['memory'].get('hits',[])), "tool_decision": result.get('tool_decision'), "permission": result.get('permission'), "execution": result.get('execution'), "verification": result.get('verification'), "response_preview": result['response'][:600]}

if __name__ == "__main__":
    # Ensure setup memory is fresh (like simulations)
    from pathlib import Path
    # Note: setup_memory already seeded; we reuse
    results = []

    # 1. Simple — trivial, no tool needed, L0
    results.append(run_test(
        "T1 Simple — 'Hello, how are you?'",
        "Hello, how are you?",
        expected={
            "level_in": ["L0","L1"],
            "tool_decision": "SKIP_TOOL",
            "permission": "allow",
            "verification": "pass",
            "trace_has": ["INPUT","RESPONSE"],
            "response_not_contains": ["private scratch"]
        }
    ))
    time.sleep(0.2)

    # 2. Ambiguous — 'Do it' (2 words, high ambiguity) should trigger clarification (F-AMB)
    results.append(run_test(
        "T2 Ambiguous — 'Do it'",
        "Do it",
        expected={
            "level_in": ["L0","L1","L2"],
            "response_contains": ["clarify","did you mean","ambiguous"],
            "permission": "allow",  # permission allow but V3 may still be pass because we clarified
            "trace_has": ["INPUT","RESPONSE"]
        }
    ))
    time.sleep(0.2)

    # 3. Memory retrieval — no tool, hits from S4/S5
    results.append(run_test(
        "T3 Memory retrieval — 'What do you remember about Project Helios?'",
        "What do you remember about Project Helios?",
        expected={
            "memory_min_hits": 1,
            "tool_decision": "SKIP_TOOL",
            "response_contains": ["helios","memory"],
            "trace_has": ["MEMORY"],
            "verification": "pass"
        }
    ))
    time.sleep(0.2)

    # 4. Tool-required — read_file A0
    results.append(run_test(
        "T4 Tool-required — 'Read /home/user/helios_spec.pdf and tell me efficiency'",
        "Read /home/user/helios_spec.pdf and tell me the efficiency",
        expected={
            "level_in": ["L1","L2"],
            "tool": "read_file",
            "execution_status": "ok",
            "response_contains": ["22%","efficiency","read_file"],
            "trace_has": ["EXECUTION","VERIFICATION"]
        }
    ))
    time.sleep(0.2)

    # 5. Permission-gated — ambiguous send with pronoun, high consequence, should NOT execute external effect, should clarify or confirm_needed
    results.append(run_test(
        "T5 Permission-gated — 'Send it to him'",
        "Send it to him",
        expected={
            "level_in": ["L3","L4"],  # consequence 0.75 pushes to L3+
            "response_contains": ["clarification","ambiguous","confirm"],
            "trace_has": ["PERMISSION"]
        }
    ))
    time.sleep(0.2)

    # 6. Proactive tick gated — N0.1 disabled by default
    print(f"\n{'='*80}")
    print("TEST: T6 Proactive tick — N0.1 disabled by default")
    tick_result = ORCHESTRATOR.proactive_tick()
    print(f"→ tick response: {tick_result['response'][:300]!r}")
    print(f"→ permission: {tick_result.get('permission')}")
    print(f"→ verification: {tick_result.get('verification')}")
    t6_pass = tick_result.get('permission',{}).get('verdict') == 'deny' and 'disabled' in str(tick_result.get('permission',{}).get('reasons',[])).lower() or 'suppressed' in tick_result['response'].lower()
    print(f"  {'✓' if t6_pass else '✗'} Proactive tick should be deny/suppressed when disabled")
    print(f"Result: {'PASS' if t6_pass else 'FAIL'} trace={tick_result['trace_id']}")
    results.append({"name": "T6 Proactive tick disabled", "input": "[PROACTIVE_TICK]", "passed": bool(t6_pass), "checks": [{"ok": bool(t6_pass), "msg": "Proactive tick deny when disabled"}], "trace_id": tick_result['trace_id'], "permission": tick_result.get('permission'), "response_preview": tick_result['response'][:400]})

    # Summary
    print(f"\n{'='*80}")
    print("ARCH TEST SUMMARY")
    for r in results:
        print(f"  {'✓ PASS' if r['passed'] else '✗ FAIL'} — {r['name']} (trace {r['trace_id']})")
    total = len(results)
    passed = sum(1 for r in results if r['passed'])
    print(f"\nPassed {passed}/{total} — {'ALL PASS' if passed==total else 'SOME FAILED'}")

    # Save to logs/arch_tests.json
    pathlib.Path("/home/user/nis-mvv/logs/arch_tests.json").parent.mkdir(parents=True, exist_ok=True)
    with open("/home/user/nis-mvv/logs/arch_tests.json","w",encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print("\nArch tests saved to logs/arch_tests.json")

    # Also save traces for these tests
    with open("/home/user/nis-mvv/logs/arch_traces.json","w",encoding="utf-8") as f:
        all_traces = {}
        for r in results:
            tid = r["trace_id"]
            all_traces[tid] = GLOBAL_TRACE.to_dict(tid)
        json.dump(all_traces, f, indent=2, ensure_ascii=False)
    print("Arch traces saved to logs/arch_traces.json")
