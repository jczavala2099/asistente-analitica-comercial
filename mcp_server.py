from fastmcp import FastMCP

from commercial_tools import (
    analizar_productos_comprados_juntos,
    calcular_frecuencia_compra_cliente,
    calcular_ticket_promedio_cliente,
    obtener_producto_mas_vendido,
    obtener_resumen_dataset,
    segmentar_clientes,
)


mcp = FastMCP("asistente-analitica-comercial")


@mcp.tool()
def tool_resumen_dataset() -> dict:
    """Devuelve resumen general del dataset comercial."""
    return obtener_resumen_dataset()


@mcp.tool()
def tool_ticket_promedio(cliente_id: str | None = None, segmento: str | None = None) -> dict:
    """Calcula el ticket promedio por cliente o segmento."""
    return calcular_ticket_promedio_cliente(cliente_id=cliente_id, segmento=segmento)


@mcp.tool()
def tool_producto_mas_vendido(criterio: str = "monto") -> dict:
    """Obtiene el producto mas vendido por monto o unidades."""
    return obtener_producto_mas_vendido(criterio=criterio)


@mcp.tool()
def tool_productos_juntos(top_n: int = 10) -> dict:
    """Detecta productos que se compran juntos en la misma orden."""
    return analizar_productos_comprados_juntos(top_n=top_n)


@mcp.tool()
def tool_frecuencia_cliente(cliente_id: str) -> dict:
    """Calcula la frecuencia de compra de un cliente."""
    return calcular_frecuencia_compra_cliente(cliente_id=cliente_id)


@mcp.tool()
def tool_segmentar_clientes() -> dict:
    """Segmenta clientes por monto total y frecuencia de compra."""
    return segmentar_clientes()


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000, path="/mcp")
