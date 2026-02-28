import importlib

print("=== Import smoke test starting ===")

modules = [
    "app",
    "agents.job_agent",
    "agents.persistent_graph",
    "tools.linkedin_search_tool",
    "tools.naukri_search_tool",
    "tools.company_research_tool",
    "tools.skill_analyzer_tool",
]

for m in modules:
    try:
        importlib.import_module(m)
        print(f"OK  - {m}")
    except Exception as e:
        print(f"FAIL- {m}: {e}")

print("\n=== Creating standard agent executor ===")
from agents.job_agent import create_job_agent

agent = create_job_agent()
print("Standard agent executor created.")

print("\n=== Creating persistent LangGraph graph ===")
from agents.persistent_graph import get_persistent_graph

graph = get_persistent_graph()
print("Persistent graph created.")

print("\n=== Running a tiny dry-run via persistent graph (no network tools) ===")
state = {
    "input": "Say hello briefly and do not call any tools.",
    "resume_context": "",
    "response": "",
}
res = graph.invoke(state, config={"configurable": {"thread_id": "test-thread"}})
print("Graph response prefix:", res.get("response", "").strip()[:200])

print("\n=== Running skill analyzer truncation heuristic on synthetic long resume ===")
from tools.skill_analyzer_tool import _truncate_text_for_analysis

fake_resume = """SUMMARY
Senior engineer with 10+ years of experience.

EXPERIENCE
2012-2014: VeryOldCorp
2014-2018: OldCorp
2019-2021: MidCorp
2022-2025: NewCorp

SKILLS
Python, LangChain, LangGraph, Streamlit
"""

truncated = _truncate_text_for_analysis(fake_resume, max_chars=200)
print("Truncated resume length:", len(truncated))
print("Truncated resume contents:\n", truncated)

print("\n=== Smoke tests completed ===")

