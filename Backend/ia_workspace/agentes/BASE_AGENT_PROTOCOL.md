# Protocolo Base para Agentes
Cada agente debe exponer:
- spec.py: AGENT_NAME, VERSION, SUPPORTED_INTENTS
- handler.py: Clase <Nombre>Agent con método async handle(request: AgentRequest) -> AgentResult
- __init__.py
Opcional: prompts/
Prohibido: importar otros agentes directamente.
