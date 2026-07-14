import re

from dotenv import load_dotenv

from commercial_tools import (
    analizar_productos_comprados_juntos,
    calcular_frecuencia_compra_cliente,
    calcular_ticket_promedio_cliente,
    obtener_producto_mas_vendido,
    obtener_resumen_dataset,
    segmentar_clientes,
)


load_dotenv()

SESSION_MEMORY: dict[str, list[dict[str, str]]] = {}


def remember(session_id: str, role: str, content: str) -> None:
    SESSION_MEMORY.setdefault(session_id, [])
    SESSION_MEMORY[session_id].append({"role": role, "content": content})
    SESSION_MEMORY[session_id] = SESSION_MEMORY[session_id][-10:]


def extract_customer_id(text: str) -> str | None:
    match = re.search(r"\bCUST[-_A-Z0-9]*|\bC[0-9]+\b", text.upper())
    return match.group(0) if match else None


def last_customer_id(session_id: str) -> str | None:
    for item in reversed(SESSION_MEMORY.get(session_id, [])):
        found = extract_customer_id(item["content"])
        if found:
            return found
    return None


def select_tool(message: str, session_id: str) -> dict:
    text = message.lower()

    if "resumen" in text or "dataset" in text or "datos" in text:
        return {"tool": "obtener_resumen_dataset", "result": obtener_resumen_dataset()}

    if "ticket" in text or "promedio" in text:
        customer_id = extract_customer_id(message)
        return {
            "tool": "calcular_ticket_promedio_cliente",
            "result": calcular_ticket_promedio_cliente(cliente_id=customer_id),
        }

    if "producto" in text and ("mas vendido" in text or "mayor venta" in text or "más vendido" in text):
        return {"tool": "obtener_producto_mas_vendido", "result": obtener_producto_mas_vendido()}

    if "juntos" in text or "combinacion" in text or "combinación" in text:
        return {"tool": "analizar_productos_comprados_juntos", "result": analizar_productos_comprados_juntos()}

    if "frecuencia" in text or "cada cuanto" in text or "cada cuánto" in text:
        customer_id = extract_customer_id(message) or last_customer_id(session_id)
        if not customer_id:
            return {"tool": None, "result": {"error": "Necesito un customer_id para calcular frecuencia."}}
        return {
            "tool": "calcular_frecuencia_compra_cliente",
            "result": calcular_frecuencia_compra_cliente(customer_id),
        }

    if "segment" in text:
        return {"tool": "segmentar_clientes", "result": segmentar_clientes()}

    return {
        "tool": None,
        "result": {
            "mensaje": "Puedo responder sobre resumen del dataset, ticket promedio, producto mas vendido, productos comprados juntos, frecuencia de compra y segmentacion de clientes."
        },
    }


def format_answer(user_message: str, tool_call: dict) -> str:
    tool = tool_call["tool"]
    result = tool_call["result"]

    if isinstance(result, dict) and "error" in result:
        return f"No pude completar la consulta: {result['error']}"

    if tool == "analizar_productos_comprados_juntos":
        pares = result.get("pares", [])
        metodo = result.get("metodo")

        if not pares:
            return "No encontre suficientes datos para detectar productos relacionados."

        lineas = []
        for idx, par in enumerate(pares[:5], start=1):
            lineas.append(
                f"**{idx}.** {par['nombre_a']} + {par['nombre_b']} "
                f"(frecuencia: {par['frecuencia']})"
            )

        nota_metodo = (
            "El dataset permite detectar productos dentro de la misma orden."
            if metodo == "misma_orden"
            else (
                "El dataset no contiene ordenes con multiples productos. "
                "Por eso use una aproximacion basada en historial de cliente: "
                "se consideran relacionados los productos que aparecen comprados "
                "por el mismo cliente en diferentes ordenes."
            )
        )

        return (
            "### Respuesta\n"
            "Estos son los productos que aparecen mas relacionados en el dataset:\n\n"
            + "\n\n".join(lineas)
            + "\n\n"
            "### Como se calculo\n"
            f"{nota_metodo}\n\n"
            "### Interpretacion comercial\n"
            "Estos pares pueden servir como punto de partida para analizar oportunidades "
            "de venta cruzada, paquetes promocionales o recomendaciones de productos. "
            "La evidencia completa se puede revisar en el panel de tools usadas."
        )

    if tool == "obtener_producto_mas_vendido":
        return (
            "### Respuesta\n"
            f"El producto con mayor venta es **{result['nombre']}**.\n\n"
            "### Evidencia\n"
            f"- Producto ID: `{result['producto_id']}`\n"
            f"- Categoria: {result['categoria']}\n"
            f"- Unidades vendidas: {result['unidades']}\n"
            f"- Monto total vendido: {result['monto_total']}\n\n"
            "### Interpretacion comercial\n"
            "Este producto puede considerarse prioritario para campañas, inventario "
            "y analisis de clientes compradores."
        )

    if tool == "calcular_ticket_promedio_cliente":
        return (
            "### Respuesta\n"
            f"El ticket promedio calculado es **{result['ticket_promedio']}**.\n\n"
            "### Evidencia\n"
            f"- Total de ventas: {result['total_ventas']}\n"
            f"- Numero de compras: {result['numero_compras']}\n\n"
            "### Interpretacion comercial\n"
            "Este valor ayuda a estimar el ingreso promedio por compra y puede usarse "
            "para comparar segmentos o clientes."
        )

    if tool == "segmentar_clientes":
        clientes = result.get("clientes", [])
        criterios = result.get("criterios", {})

        lineas = []
        for idx, cliente in enumerate(clientes[:5], start=1):
            lineas.append(
                f"**{idx}.** Cliente {cliente.get('cliente_id')} - "
                f"{cliente.get('segmento_calculado')} - "
                f"ventas: {round(cliente.get('monto_total', 0), 2)} - "
                f"compras: {cliente.get('compras')}"
            )

        return (
            "### Respuesta\n"
            "Se segmentaron los clientes segun monto total comprado y frecuencia de compra.\n\n"
            "### Top clientes segmentados\n"
            + "\n\n".join(lineas)
            + "\n\n"
            "### Criterios usados\n"
            f"- Monto alto desde: {criterios.get('monto_alto_desde')}\n"
            f"- Frecuencia alta desde: {criterios.get('frecuencia_alta_desde')}\n\n"
            "### Interpretacion comercial\n"
            "Los clientes de alto valor o alto potencial pueden priorizarse para "
            "campañas, seguimiento comercial o estrategias de retencion."
        )

    if tool == "obtener_resumen_dataset":
        return (
            "### Respuesta\n"
            "Este es el resumen general del dataset comercial.\n\n"
            "### Evidencia\n"
            f"- Ordenes: {result['numero_ordenes']}\n"
            f"- Clientes: {result['numero_clientes']}\n"
            f"- Productos: {result['numero_productos']}\n"
            f"- Ventas totales: {result['ventas_totales']}\n"
            f"- Periodo: {result['fecha_minima']} a {result['fecha_maxima']}\n\n"
            "### Interpretacion comercial\n"
            "Este resumen permite entender el alcance del dataset antes de hacer "
            "analisis mas especificos."
        )

    return (
        "### Respuesta\n"
        f"Use la tool `{tool}` para responder la consulta.\n\n"
        "### Evidencia\n"
        f"```json\n{result}\n```\n\n"
        "### Interpretacion\n"
        "La respuesta esta basada en el dataset real de ordenes ecommerce."
    )


def run_agent(user_message: str, session_id: str) -> dict:
    remember(session_id, "user", user_message)
    tool_call = select_tool(user_message, session_id)
    answer = format_answer(user_message, tool_call)
    remember(session_id, "assistant", answer)

    return {
        "answer": answer,
        "trace": {
            "session_id": session_id,
            "tool_used": tool_call["tool"],
            "tool_result": tool_call["result"],
        },
    }
