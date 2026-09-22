"""
Tool Registry & Router — Canonical v1.1
Implements 7-question router [EXPLICIT]
MVV tools: read_file [REAL], write_file [REAL], bash [REAL sandboxed], system_time [REAL], web_search [MOCK], fetch_page [MOCK], generate_image [MOCK], generate_speech [MOCK]
"""
import time
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

@dataclass
class ToolSpec:
    name: str
    category: str  # read, compute, write, interactive
    effect: str
    idempotent: bool
    autonomy: str  # A0..A4
    description: str

REGISTRY = {
    "read_file": ToolSpec("read_file", "read", "read-only", True, "A0", "Read file from /home/user"),
    "write_file": ToolSpec("write_file", "write", "persistent", False, "A1", "Write file to /home/user"),
    "edit_file": ToolSpec("edit_file", "write", "persistent", False, "A1", "Edit file"),
    "bash": ToolSpec("bash", "compute", "ephemeral", False, "A1", "Run bash sandboxed"),
    "system_time": ToolSpec("system_time", "read", "read-only", True, "A0", "Get system time [RECO]"),
    "web_search": ToolSpec("web_search", "read", "read-only", True, "A2", "Search web [MOCK in MVV]"),
    "fetch_page": ToolSpec("fetch_page", "read", "read-only", True, "A2", "Fetch page [MOCK]"),
    "generate_image": ToolSpec("generate_image", "write", "persistent", False, "A1", "Generate image [MOCK]"),
    "generate_speech": ToolSpec("generate_speech", "write", "persistent", False, "A1", "Generate speech [MOCK]"),
    "ask_user": ToolSpec("ask_user", "interactive", "user-facing", False, "A0", "Ask user clarification"),
    "present_file": ToolSpec("present_file", "interactive", "user-facing", False, "A0", "Present file"),
    "dry_run": ToolSpec("dry_run", "interactive", "user-facing", True, "A0", "Dry-run preview [RECO]"),
}

# ---- Real tool implementations ----

def tool_read_file(args: Dict) -> Dict:
    path = args.get("path", "")
    # Sandbox to /home/user
    p = Path(path)
    if not p.is_absolute():
        p = Path("/home/user") / path
    # Security: must be under /home/user
    try:
        p = p.resolve()
        if not str(p).startswith("/home/user"):
            return {"status": "error", "error": "Path outside /home/user sandbox", "provenance": "read_file"}
        text = p.read_text(encoding="utf-8", errors="ignore")
        return {"status": "ok", "raw_output": text[:8000], "parsed_output": text[:500], "provenance": f"read_file:{p}", "cost": len(text)}
    except Exception as e:
        return {"status": "error", "error": str(e), "provenance": f"read_file:{p}:error"}

def tool_write_file(args: Dict) -> Dict:
    path = args.get("path", "")
    content = args.get("content", "")
    p = Path(path)
    if not p.is_absolute():
        p = Path("/home/user") / path
    try:
        p = p.resolve()
        # Allow creating under /home/user
        if not str(p).startswith("/home/user"):
            return {"status": "error", "error": "Path outside /home/user", "provenance": "write_file"}
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"status": "ok", "raw_output": f"Wrote {len(content)} chars to {p}", "parsed_output": str(p), "provenance": f"write_file:{p}", "cost": len(content)}
    except Exception as e:
        return {"status": "error", "error": str(e), "provenance": f"write_file:{p}:error"}

def tool_bash(args: Dict) -> Dict:
    command = args.get("command", "")
    # [REAL] sandboxed bash — limited to /home/user cwd
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10, cwd="/home/user")
        out = (result.stdout + result.stderr)[:8000]
        status = "ok" if result.returncode == 0 else "error"
        return {"status": status, "raw_output": out, "parsed_output": out[:500], "provenance": f"bash:{command[:60]}", "cost": len(out), "returncode": result.returncode}
    except Exception as e:
        return {"status": "error", "error": str(e), "provenance": f"bash:{command[:60]}:error"}

def tool_system_time(args: Dict) -> Dict:
    # [REAL] system_time A0 — added per R-A [RECO]
    now = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    return {"status": "ok", "raw_output": now, "parsed_output": now, "provenance": "system_time:real", "cost": 0}

# ---- Mock tools [MOCK] — simulate, not real, but flagged ----

def tool_web_search_mock(args: Dict) -> Dict:
    query = args.get("query", "")
    # [MOCK] — canned results for MVV demo; real would call web_search API
    # We simulate EU AI Act enforcement dates for the L3 simulation
    canned = {
        "eu ai act enforcement": {
            "results": [
                {"title": "EU AI Act — Enforcement Timeline (2024-2026)", "url": "https://artificialintelligenceact.eu/enforcement", "snippet": "Prohibited practices: Feb 2025. GPAI obligations: Aug 2025. High-risk systems: Aug 2026. General-purpose AI transparency: Aug 2025."},
                {"title": "European Commission — AI Act Implementation", "url": "https://commission.europa.eu/ai-act", "snippet": "The Act entered into force 1 Aug 2024. Phased: 6 months (prohibited), 12 months (GPAI), 24 months (high-risk), 36 months (certain obligations)."},
            ],
            "provenance": "web_search:MOCK"
        },
        "helios": {
            "results": [{"title": "Helios Project — Mock", "url": "https://example.com/helios", "snippet": "Helios is a solar tracker project; mock search."}],
            "provenance": "web_search:MOCK"
        }
    }
    q_lower = query.lower()
    for key, val in canned.items():
        if key in q_lower:
            return {"status": "ok", "raw_output": json.dumps(val, indent=2), "parsed_output": val["results"][0]["snippet"][:300], "provenance": val["provenance"], "cost": 100, "mock": True}
    # Default mock
    return {"status": "ok", "raw_output": json.dumps({"results": [{"title": f"Mock results for {query}", "url": "https://example.com/mock", "snippet": f"Mock snippet for '{query}' — MVV mock, not real search."}], "provenance": "web_search:MOCK"}), "parsed_output": f"Mock results for '{query}'", "provenance": "web_search:MOCK", "cost": 50, "mock": True}

def tool_fetch_page_mock(args: Dict) -> Dict:
    url = args.get("url", "")
    # [MOCK] — simulate fetch, with one URL that times out for testing partial execution
    if "timeout" in url or "bad" in url:
        return {"status": "error", "error": "Timeout — mock fetch failure", "provenance": f"fetch_page:{url}:error", "mock": True}
    snippets = {
        "artificialintelligenceact.eu": "EU AI Act enforcement: Prohibited AI practices effective Feb 2, 2025. GPAI providers: Aug 2, 2025. High-risk systems (Annex III): Aug 2, 2026. Transparency obligations: Aug 2, 2025. Full application Aug 2, 2026 with some 2027 extensions.",
        "commission.europa.eu": "Commission guidance: AI Act entered into force 1 Aug 2024. Phased application ensures preparation time. Penalties up to 35M EUR or 7% turnover.",
    }
    for key, snippet in snippets.items():
        if key in url:
            return {"status": "ok", "raw_output": snippet, "parsed_output": snippet[:300], "provenance": f"fetch_page:{url}", "cost": len(snippet), "mock": True}
    return {"status": "ok", "raw_output": f"Mock page content for {url} — MVV mock.", "parsed_output": f"Mock page for {url}", "provenance": f"fetch_page:{url}:MOCK", "cost": 50, "mock": True}

def tool_generate_image_mock(args: Dict) -> Dict:
    prompt = args.get("prompt", "")
    # [MOCK] — does not actually generate image; simulates
    fake_path = f"/home/user/generated_timeline_{int(time.time())}.png"
    # Create a placeholder text file to simulate (not a real image)
    try:
        Path(fake_path.replace(".png",".txt")).write_text(f"[MOCK IMAGE] Prompt: {prompt}\nGenerated at {time.time()}\nThis is a mock — not a real generated image.", encoding="utf-8")
    except:
        pass
    return {"status": "ok", "raw_output": f"[MOCK] Image generated: {fake_path} for prompt: {prompt[:80]}", "parsed_output": fake_path, "provenance": "generate_image:MOCK", "cost": 100, "mock": True}

def tool_generate_speech_mock(args: Dict) -> Dict:
    # [MOCK] — not implemented in MVV
    return {"status": "error", "error": "[NOT IMPLEMENTED] generate_speech in MVV — requires external TTS", "provenance": "generate_speech:NOT_IMPLEMENTED", "mock": True}

TOOL_IMPL = {
    "read_file": tool_read_file,
    "write_file": tool_write_file,
    "edit_file": tool_write_file,
    "bash": tool_bash,
    "system_time": tool_system_time,
    "web_search": tool_web_search_mock,
    "fetch_page": tool_fetch_page_mock,
    "generate_image": tool_generate_image_mock,
    "generate_speech": tool_generate_speech_mock,
    "ask_user": lambda args: {"status": "ok", "raw_output": f"[MOCK ask_user] Question: {args.get('question','')}", "parsed_output": "awaiting user", "provenance": "ask_user:MOCK", "mock": True},
    "present_file": lambda args: {"status": "ok", "raw_output": f"[MOCK present_file] {args.get('path','')}", "parsed_output": args.get("path",""), "provenance": "present_file:MOCK", "mock": True},
    "dry_run": lambda args: {"status": "ok", "raw_output": f"[MOCK dry_run] {args}", "parsed_output": "dry-run preview", "provenance": "dry_run:MOCK", "mock": True},
}

class ToolRouter:
    """
    Implements 7-question router [EXPLICIT]
    Steps 1-7 per canonical §8
    """
    def route(self, plan_step: Dict, working_context: Dict, permission_verdict: Dict, deliberation_level: str, intent_frame: Dict) -> Dict:
        """
        Returns ToolCallSpec or SKIP_TOOL
        """
        tool_hint = plan_step.get("tool_hint")
        goal = plan_step.get("goal","")
        # Q1: Is tool necessary? [EXPLICIT]
        # If L0 and goal is simple chat/creation without freshness need → SKIP
        # Freshness heuristic [RECOMMENDED]: if intent requires fresh data (web_search), tool is necessary
        requires_fresh = intent_frame.get("requires_tools", False) and deliberation_level in ["L3","L4"]
        # Simple heuristic: if no tool_hint and deliberation is L0/L1 and no external data needed → SKIP
        if not tool_hint and deliberation_level in ["L0","L1"] and not requires_fresh:
            # Check if goal mentions needing file/web/time/image
            low_goal = goal.lower()
            needs_tool = any(k in low_goal for k in ["file", "search", "web", "image", "generate", "read", "write", "bash", "time", "clock"])
            if not needs_tool:
                return {"decision": "SKIP_TOOL", "justification": "No tool necessary — N7 can answer directly with high confidence (L0/L1, no freshness need) [Q1]", "tool": None}

        # Q2: Which tool? [EXPLICIT] — least-privilege
        tool = tool_hint
        if not tool:
            # Infer from goal
            low_goal = goal.lower()
            if "search" in low_goal or "web" in low_goal or "latest" in low_goal:
                tool = "web_search"
            elif "read" in low_goal:
                tool = "read_file"
            elif "write" in low_goal or "save" in low_goal:
                tool = "write_file"
            elif "time" in low_goal or "clock" in low_goal:
                tool = "system_time"
            elif "image" in low_goal or "timeline" in low_goal:
                tool = "generate_image"
            else:
                tool = "bash"

        spec = REGISTRY.get(tool)
        if not spec:
            return {"decision": "TOOL_UNAVAILABLE", "tool": tool, "justification": f"Tool {tool} not in registry [Q2]", "error": "unavailable"}

        # Q3: Why? [EXPLICIT] — justification for audit
        justification = f"Tool {tool} selected for step '{goal[:40]}' — least-privilege match for autonomy {spec.autonomy}, category {spec.category} [Q3]"

        # Q4: What info required? [EXPLICIT] — validate params
        required_params = {
            "read_file": ["path"],
            "write_file": ["path", "content"],
            "bash": ["command"],
            "web_search": ["query"],
            "fetch_page": ["url"],
            "generate_image": ["prompt"],
            "system_time": [],
            "ask_user": ["question"],
        }
        req = required_params.get(tool, [])
        # Check if plan_step or working_context has them; if missing → SLOT_MISSING
        provided = plan_step.get("args", {})
        # Also try to fill from working_context/entities
        for param in req:
            if param not in provided or not provided[param]:
                # Try to fill from context or intent slots
                slots = intent_frame.get("slots", {})
                if param in slots and slots[param]:
                    provided[param] = slots[param]
                elif param == "path" and "file" in working_context.get("summary","").lower():
                    # Heuristic fill [MOCK]
                    pass
                else:
                    if param not in provided:
                        return {"decision": "SLOT_MISSING", "tool": tool, "missing": param, "justification": justification + f" [Q4 missing:{param}]"}

        # Q5: What permissions? [EXPLICIT] — query N10 (handled outside router, but we check autonomy level)
        # Router constructs spec; permission is checked by N10 separately. We note autonomy here.
        # Q6 & Q7 are after execution — not router's job, but we mark verification_needed
        verification_needed = not spec.idempotent or deliberation_level in ["L2","L3","L4"] or tool in ["write_file","generate_image"]

        return {
            "decision": "TOOL_CALL",
            "tool": tool,
            "args": provided,
            "justification": justification,
            "idempotency_key": f"{tool}:{hash(json.dumps(provided, sort_keys=True))%1000000}",
            "verification_needed": verification_needed,
            "autonomy": spec.autonomy,
            "category": spec.category,
            "idempotent": spec.idempotent
        }

ROUTER = ToolRouter()

def execute_tool(tool: str, args: Dict) -> Dict:
    impl = TOOL_IMPL.get(tool)
    if not impl:
        return {"status": "error", "error": f"Tool {tool} not implemented", "provenance": f"{tool}:NOT_IMPLEMENTED"}
    try:
        return impl(args)
    except Exception as e:
        return {"status": "error", "error": str(e), "provenance": f"{tool}:error"}

