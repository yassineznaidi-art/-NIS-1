"""
App tests A1-A10 — must pass before declaring complete
Uses FastAPI TestClient, real NIS Core (not mock), no private leak
"""
import sys, pathlib, json, time
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from fastapi.testclient import TestClient

# Import app
from app.main import app
client = TestClient(app)

def assert_in(text, sub, msg=""):
    if sub.lower() not in text.lower():
        raise AssertionError(f"{msg}: expected {sub!r} in {text[:800]!r}")

# Keep track
passed=[]
failed=[]

def run(name, fn):
    try:
        fn()
        print(f"✓ PASS {name}")
        passed.append(name)
    except Exception as e:
        print(f"✗ FAIL {name}: {e}")
        import traceback; traceback.print_exc()
        failed.append((name, str(e)))

def test_A1_first_conversation():
    """A1 first conversation — create session + chat Hello"""
    # Ensure health
    h = client.get("/api/health")
    assert h.status_code==200, f"health {h.status_code} {h.text}"
    assert h.json().get("status") in ["ok","degraded"]
    # Create session
    r = client.post("/api/sessions", json={})
    assert r.status_code==200, r.text
    sess_id = r.json()["session"]["id"]
    # Chat
    r = client.post("/api/chat", json={"message":"Hello, how are you?","session_id": sess_id})
    assert r.status_code==200, r.text
    data = r.json()
    assert "message" in data
    assert len(data["message"])>5
    # Should not contain private scratch
    assert "private scratch" not in data["message"].lower()
    # Verify deliberation_level present (NIS Core)
    assert data.get("deliberation_level") in ["L0","L1","L2","L3","L4"]
    # Session should now have 2 messages
    r2 = client.get(f"/api/sessions/{sess_id}")
    assert r2.status_code==200
    msgs = r2.json()["session"]["messages"]
    assert len(msgs)==2, f"expected 2 msgs got {len(msgs)}"
    assert msgs[0]["role"]=="user"
    assert msgs[1]["role"]=="assistant"
    # Save for next tests
    test_A1_first_conversation.sess_id = sess_id

def test_A2_multi_turn():
    """A2 multi-turn — continue same session"""
    sess_id = getattr(test_A1_first_conversation, "sess_id", None)
    # If no sess, create one
    if not sess_id:
        r = client.post("/api/sessions", json={}); sess_id=r.json()["session"]["id"]
        client.post("/api/chat", json={"message":"Hello","session_id":sess_id})
    r = client.post("/api/chat", json={"message":"What do you remember about Project Helios?","session_id": sess_id})
    assert r.status_code==200, r.text
    data = r.json()
    # Memory retrieval should be grounded (should mention Helios or team)
    assert "helios" in data["message"].lower() or "solar" in data["message"].lower() or "team" in data["message"].lower(), f"expected helios memory in {data['message'][:500]}"
    # No CoT leak
    assert "PRIVATE" not in data["message"]
    # Session now 4 msgs
    r2 = client.get(f"/api/sessions/{sess_id}")
    assert len(r2.json()["session"]["messages"])>=4
    test_A2_multi_turn.sess_id = sess_id

def test_A3_new_conversation():
    """A3 new conversation — new session id, isolated"""
    r = client.post("/api/sessions", json={})
    sess2 = r.json()["session"]["id"]
    assert sess2 != test_A1_first_conversation.sess_id
    r = client.post("/api/chat", json={"message":"Write a short poem about the sea for my daughter","session_id": sess2})
    assert r.status_code==200
    data = r.json()
    assert "sea" in data["message"].lower() or "poem" in data["message"].lower()
    # Should be L1
    assert data.get("deliberation_level")=="L1", f"poem should be L1 got {data.get('deliberation_level')}"
    # Verify no contamination: poem response should not contain helios when mocked? It may contain helios hits but should not be in poem content as contamination
    # At least should contain poem lines
    assert "sea" in data["message"].lower()
    # Session list should contain both
    r3 = client.get("/api/sessions")
    ids = [s["id"] for s in r3.json()["sessions"]]
    assert test_A1_first_conversation.sess_id in ids
    assert sess2 in ids
    test_A3_new_conversation.sess2 = sess2

def test_A4_reopen_conversation():
    """A4 reopen previous conversation — GET session returns history"""
    sess_id = test_A1_first_conversation.sess_id
    r = client.get(f"/api/sessions/{sess_id}")
    assert r.status_code==200
    sess = r.json()["session"]
    assert len(sess["messages"])>=2
    # Re-send chat in same session and ensure continuity
    r2 = client.post("/api/chat", json={"message":"Thanks!","session_id": sess_id})
    assert r2.status_code==200
    r3 = client.get(f"/api/sessions/{sess_id}")
    assert len(r3.json()["session"]["messages"])>=3

def test_A5_memory_retrieval():
    """A5 memory retrieval via app — solar tracker paraphrase"""
    r = client.post("/api/sessions", json={})
    sid = r.json()["session"]["id"]
    # Paraphrase without exact keyword helios
    r2 = client.post("/api/chat", json={"message":"Tell me about the solar tracker project","session_id": sid})
    assert r2.status_code==200, r2.text
    data = r2.json()
    # Should retrieve helios via hybrid (dense or TFIDF) — check provenance via health? We check message contains helios or solar
    assert "helios" in data["message"].lower() or "solar" in data["message"].lower()
    # Deliberation should be L2 maybe but at least not L0 (needs memory)
    assert data.get("deliberation_level") in ["L1","L2","L3"]

def test_A6_model_failure():
    """A6 model failure — empty message should return error, not fabricate"""
    r = client.post("/api/chat", json={"message":"","session_id": test_A1_first_conversation.sess_id})
    # Our API returns 400 for empty, or 500 with error payload
    assert r.status_code in [400,500,503]
    # Also test provider health fallback: mock provider always ok, but we test empty handling
    # Test overly long message
    long_msg = "x"*9000
    r2 = client.post("/api/chat", json={"message": long_msg})
    assert r2.status_code in [400,500,503]
    # Response should not be fabricated poem
    if r2.status_code==200:
        assert "x"*100 not in r2.json().get("message","")

def test_A7_malformed_model_response():
    """A7 malformed model response — adapter should handle gracefully"""
    # Simulate by calling adapter directly with broken provider
    from app.adapter import NISAdapter
    from model_providers.mock_provider import MockProvider
    class BrokenProvider(MockProvider):
        def generate(self, prompt, context=None):
            return {"text": None, "provenance": None}  # malformed: text is None
    adapter = NISAdapter(BrokenProvider())
    res = adapter.chat("Hello")
    # Should not crash, should return ok with empty string or error
    assert res.get("status") in ["ok","error"]
    if res.get("status")=="ok":
        assert isinstance(res.get("message"), str)

def test_A8_verification_failure():
    """A8 verification remains active — try to trigger V1/V7 via unverified claim"""
    # Use NIS Core directly to create a failing verification scenario
    from nis.nodes import N14_Verification
    n14 = N14_Verification()
    # Failing draft: no evidence for L2
    ver = n14.process(
        reasoning_trace={"evidence_links":[],"conclusions":["Helios efficiency 22%"],"plan_skeleton":[]},
        plan={"steps":[{"tool_hint":"read_file"}]},
        execution_result={"status":"skipped"},
        memory_bundle={"hits":[],"conflicts":[]},
        intent_frame={"primary_intent":"analysis","ambiguity_score":0.2,"consequence_score":0.5},
        draft_response="Helios efficiency is 22% (no provenance)",
        deliberation_level="L2",
        trace_id="test-A8"
    )
    assert ver["verdict"]=="fail"
    assert any(i["axis"]=="V1" for i in ver["issues"])
    # App chat should not bypass verification — check that a real chat still verifies
    r = client.post("/api/chat", json={"message":"Write a poem","session_id": test_A1_first_conversation.sess_id})
    assert r.status_code==200
    assert r.json().get("verification") in ["pass","pass_with_warnings","pass_needs_confirm","blocked","F-AMB","F-INS"]

def test_A9_mobile_layout():
    """A9 mobile layout — check HTML contains viewport, responsive CSS, no console leak"""
    r = client.get("/")
    assert r.status_code==200
    html = r.text
    assert 'name="viewport"' in html
    assert 'content="width=device-width' in html
    assert "NIS" in html
    assert "conversation" in html.lower()
    assert "Message NIS" in html or "message" in html.lower()
    # CSS should exist
    r2 = client.get("/static/style.css")
    assert r2.status_code==200
    css = r2.text
    assert "viewport" not in css  # just check responsive
    assert "@media" in css  # responsive
    assert "max-width" in css
    # JS should exist
    r3 = client.get("/static/app.js")
    assert r3.status_code==200
    assert "fetch('/api/chat'" in r3.text

def test_A10_secret_protection():
    """A10 secret/API-key protection — /api/config should NOT expose secrets"""
    r = client.get("/api/config")
    assert r.status_code==200
    cfg = r.json()
    # Should contain public fields
    assert "app_name" in cfg
    # Should NOT contain api keys
    flat = json.dumps(cfg).lower()
    assert "api_key" not in flat
    assert "openai" not in flat
    assert "secret" not in flat
    # Check that frontend HTML doesn't contain api keys
    r2 = client.get("/")
    assert "OPENAI_API_KEY" not in r2.text
    assert "sk-" not in r2.text
    # Check health doesn't leak keys
    r3 = client.get("/api/health")
    flat3 = json.dumps(r3.json()).lower()
    assert "sk-" not in flat3

if __name__ == "__main__":
    tests = [
        ("A1 first conversation", test_A1_first_conversation),
        ("A2 multi-turn", test_A2_multi_turn),
        ("A3 new conversation", test_A3_new_conversation),
        ("A4 reopen", test_A4_reopen_conversation),
        ("A5 memory retrieval", test_A5_memory_retrieval),
        ("A6 model failure", test_A6_model_failure),
        ("A7 malformed", test_A7_malformed_model_response),
        ("A8 verification", test_A8_verification_failure),
        ("A9 mobile", test_A9_mobile_layout),
        ("A10 secret protection", test_A10_secret_protection),
    ]
    for name, fn in tests:
        run(name, fn)
    print(f"\nAPP TEST SUMMARY Passed {len(passed)}/{len(tests)}")
    for p in passed: print(f"  ✓ {p}")
    for f,err in failed: print(f"  ✗ {f}: {err[:200]}")
    # Save
    pathlib.Path("logs").mkdir(exist_ok=True)
    pathlib.Path("logs/app_tests.json").write_text(json.dumps({"passed":passed,"failed":failed}, indent=2))
    if failed:
        sys.exit(1)
    print("All app tests passed")
