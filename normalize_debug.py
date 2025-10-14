import os
import sys
ROOT = os.path.dirname(__file__)
BACKEND_ROOT = os.path.join(ROOT, "Backend")
BACKEND_SRC = os.path.join(BACKEND_ROOT, "src")
IA_WORKSPACE = os.path.join(BACKEND_ROOT, "ia_workspace")
for path in (BACKEND_SRC, IA_WORKSPACE, BACKEND_ROOT, ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)

from dotenv import load_dotenv
load_dotenv(os.path.join(BACKEND_ROOT, ".env"))

from src.infrastructure.langgraph.nodes.agente_g_node import AgenteGNode

node = AgenteGNode()
print("Agent initialized?", node._agent is not None, "error", node._agent_error)
agent = node._agent
print("Agent email:", getattr(agent, "agent_email", None))
print("Normalize recipients: ", agent._normalize_recipients(["lucasnoa94@gmail.com"]))
