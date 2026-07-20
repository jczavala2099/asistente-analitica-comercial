import asyncio
import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI


load_dotenv()

SESSION_MEMORY: dict[str, list[dict[str, str]]] = {}
AGENT_CACHE = {"agent": None, "tools": None}

SYSTEM_PROMPT = """
Eres un asistente de analitica comercial para un dataset real de ecommerce.

Reglas:
1. Usa las tools MCP cuando la pregunta dependa de datos del negocio.
2. No inventes cifras, productos, clientes, segmentos ni fechas.
3. Si falta un dato necesario, pide una aclaracion breve.
4. Responde siempre en espanol.
5. Organiza la respuesta con Respuesta, Evidencia e Interpretacion comercial cuando aplique.
6. Si usas una tool, resume la evidencia principal devuelta por esa tool.
"""


def remember(session_id: str, role: str, content: str) -> None:
    SESSION_MEMORY.setdefault(session_id, [])
    SESSION_MEMORY[session_id].append({"role": role, "content": content})
    SESSION_MEMORY[session_id] = SESSION_MEMORY[session_id][-10:]


def get_recent_history(session_id: str) -> list[dict[str, str]]:
    return SESSION_MEMORY.get(session_id, [])[-8:]


async def discover_mcp_tools():
    mcp_url = os.getenv(
        "MCP_SERVER_URL",
        "https://asistente-analitica-comercial-production.up.railway.app/mcp",
    )

    client = MultiServerMCPClient(
        {
            "asistente_comercial": {
                "transport": "streamable_http",
                "url": mcp_url,
            }
        }
    )

    return await client.get_tools()


async def get_agent():
    if AGENT_CACHE["agent"] is not None:
        return AGENT_CACHE["agent"], AGENT_CACHE["tools"]

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Falta OPENAI_API_KEY en variables de entorno o Streamlit Secrets.")

    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    model = ChatOpenAI(
        model=model_name,
        temperature=0,
        api_key=api_key,
    )

    tools = await discover_mcp_tools()

    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
    )

    AGENT_CACHE["agent"] = agent
    AGENT_CACHE["tools"] = tools

    return agent, tools


def normalize_content(content) -> str:
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                parts.append(str(item["text"]))
            else:
                parts.append(str(item))
        return "\n".join(parts)

    return str(content)


def extract_trace(messages) -> dict:
    tool_calls = []
    tool_outputs = []

    for message in messages:
        if getattr(message, "tool_calls", None):
            for call in message.tool_calls:
                tool_calls.append(
                    {
                        "name": call.get("name"),
                        "args": call.get("args"),
                        "id": call.get("id"),
                    }
                )

        if getattr(message, "type", None) == "tool":
            tool_outputs.append(
                {
                    "name": getattr(message, "name", None),
                    "content": normalize_content(getattr(message, "content", "")),
                }
            )

    return {
        "tool_calls": tool_calls,
        "tool_outputs": tool_outputs,
    }


async def run_agent_async(user_message: str, session_id: str) -> dict:
    agent, tools = await get_agent()

    history = get_recent_history(session_id)
    input_messages = history + [{"role": "user", "content": user_message}]

    result = await agent.ainvoke(
        {"messages": input_messages},
        config={"configurable": {"thread_id": session_id}},
    )

    messages = result.get("messages", [])
    final_message = messages[-1] if messages else None
    answer = normalize_content(final_message.content) if final_message else "No pude generar una respuesta."

    remember(session_id, "user", user_message)
    remember(session_id, "assistant", answer)

    trace = extract_trace(messages)
    trace["session_id"] = session_id
    trace["mcp_server_url"] = os.getenv("MCP_SERVER_URL")
    trace["available_tools"] = [tool.name for tool in tools]

    return {
        "answer": answer,
        "trace": trace,
    }


def run_agent(user_message: str, session_id: str) -> dict:
    try:
        return asyncio.run(run_agent_async(user_message, session_id))
    except Exception as error:
        return {
            "answer": f"No pude completar la consulta: {error}",
            "trace": {
                "session_id": session_id,
                "error": str(error),
            },
        }
