# Asistente de analitica comercial

## Descripcion

Aplicacion Streamlit para analizar un dataset real de ordenes ecommerce. El sistema ayuda a un analista o equipo de management a responder preguntas comerciales sobre ventas, clientes y productos.

## Usuario principal

Analista comercial / Management.

## Problema que resuelve

Analiza informacion de ventas para apoyar la toma de decisiones al buscar nuevos clientes, detectar productos relevantes y segmentar clientes.

## Fuente de datos

Se usa el archivo `data/ecommerceordersdataset.csv`.

El dataset contiene ordenes ecommerce con columnas como:

- order_id
- customer_id
- order_date
- customer_segment
- product_id
- product_category
- product_subcategory
- brand
- unit_price
- quantity
- order_amount
- profit_amount

## Arquitectura

Streamlit -> Agente -> Tools comerciales -> Dataset real

Adicionalmente, el proyecto incluye `mcp_server.py` para exponer las tools como servidor MCP.

## Tools implementadas

| Tool | Proposito |
| --- | --- |
| obtener_resumen_dataset | Resume ordenes, clientes, productos, ventas y rango de fechas. |
| calcular_ticket_promedio_cliente | Calcula ticket promedio general, por cliente o por segmento. |
| obtener_producto_mas_vendido | Identifica el producto con mayor venta por monto. |
| analizar_productos_comprados_juntos | Detecta productos que aparecen juntos en la misma orden. |
| calcular_frecuencia_compra_cliente | Calcula frecuencia de compra de un cliente. |
| segmentar_clientes | Segmenta clientes por monto total y frecuencia. |

## Memoria

La app usa `session_id` con `st.session_state` para conservar contexto durante la conversacion.

## Ejecucion local

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app_streamlit.py
```

## Servidor MCP local

```bash
python mcp_server.py
```

Endpoint local:

```text
https://asistente-analitica-comercial-production.up.railway.app/mcp
```

## Limitaciones

El dataset contiene ordenes, clientes y productos, pero no contiene inventario real. Por eso el inventario se documenta como una extension futura.

## Entrega

- Repositorio GitHub: https://github.com/jczavala2099/asistente-analitica-comercial
- App Streamlit: https://asistente-anlitic-jcz.streamlit.app/

## Nota sobre productos comprados juntos

El dataset contiene una orden por producto, por lo que no siempre es posible detectar productos comprados juntos dentro de la misma orden.

Por esta razon, la tool `analizar_productos_comprados_juntos` primero intenta encontrar pares dentro de la misma orden. Si no encuentra ordenes multiproducto, usa una aproximacion basada en historial del cliente: productos comprados por el mismo cliente en diferentes ordenes.

Esta decision evita inventar informacion y mantiene la trazabilidad del analisis.

## Link publico de la app

La aplicacion Streamlit esta disponible en:

https://apzqrgnguimixpf8dfvudr.streamlit.app/
