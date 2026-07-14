from itertools import combinations

import pandas as pd

from data_loader import load_commercial_tables


def _tables():
    return load_commercial_tables()


def filter_by_date(df: pd.DataFrame, fecha_inicio: str | None = None, fecha_fin: str | None = None) -> pd.DataFrame:
    result = df.copy()
    if fecha_inicio:
        result = result[result["fecha"] >= pd.to_datetime(fecha_inicio)]
    if fecha_fin:
        result = result[result["fecha"] <= pd.to_datetime(fecha_fin)]
    return result


def calcular_ticket_promedio_cliente(
    cliente_id: str | None = None,
    segmento: str | None = None,
    fecha_inicio: str | None = None,
    fecha_fin: str | None = None,
) -> dict:
    tables = _tables()
    ventas = filter_by_date(tables["ventas"], fecha_inicio, fecha_fin)
    clientes = tables["clientes"]

    if cliente_id:
        ventas = ventas[ventas["cliente_id"].astype(str) == str(cliente_id)]

    if segmento:
        ids = clientes[clientes["segmento"].astype(str).str.lower() == segmento.lower()]["cliente_id"]
        ventas = ventas[ventas["cliente_id"].isin(ids)]

    if ventas.empty:
        return {"error": "No hay ventas para los filtros indicados."}

    ventas_por_compra = ventas.groupby("venta_id")["total"].sum()

    return {
        "ticket_promedio": round(float(ventas_por_compra.mean()), 2),
        "total_ventas": round(float(ventas["total"].sum()), 2),
        "numero_compras": int(ventas["venta_id"].nunique()),
        "cliente_id": cliente_id,
        "segmento": segmento,
    }


def obtener_producto_mas_vendido(criterio: str = "monto") -> dict:
    tables = _tables()
    ventas = tables["ventas"]
    productos = tables["productos"]

    if ventas.empty:
        return {"error": "No hay ventas disponibles."}

    grouped = ventas.groupby("producto_id").agg(
        unidades=("cantidad", "sum"),
        monto=("total", "sum"),
    ).reset_index()

    sort_col = "monto" if criterio == "monto" else "unidades"
    top = grouped.sort_values(sort_col, ascending=False).iloc[0]
    producto = productos[productos["producto_id"].astype(str) == str(top["producto_id"])].iloc[0]

    return {
        "producto_id": str(top["producto_id"]),
        "nombre": producto["nombre"],
        "categoria": producto["categoria"],
        "unidades": round(float(top["unidades"]), 2),
        "monto_total": round(float(top["monto"]), 2),
        "criterio": criterio,
    }


def analizar_productos_comprados_juntos(top_n: int = 10) -> dict:
    tables = _tables()
    ventas = tables["ventas"]
    productos = tables["productos"]

    pair_counts: dict[tuple[str, str], int] = {}

    # Metodo 1: productos dentro de la misma orden.
    for _, group in ventas.groupby("venta_id"):
        product_ids = sorted(group["producto_id"].astype(str).unique())
        for pair in combinations(product_ids, 2):
            pair_counts[pair] = pair_counts.get(pair, 0) + 1

    metodo = "misma_orden"

    # Metodo 2: si no hay ordenes multiproducto, usar historial por cliente.
    if not pair_counts:
        metodo = "mismo_cliente"
        for _, group in ventas.groupby("cliente_id"):
            product_ids = sorted(group["producto_id"].astype(str).unique())
            for pair in combinations(product_ids, 2):
                pair_counts[pair] = pair_counts.get(pair, 0) + 1

    if not pair_counts:
        return {
            "error": "No hay suficientes datos para detectar productos relacionados."
        }

    nombres = productos.set_index(productos["producto_id"].astype(str))["nombre"].to_dict()
    top_pairs = sorted(pair_counts.items(), key=lambda item: item[1], reverse=True)[:top_n]

    pares = [
        {
            "producto_a": a,
            "nombre_a": nombres.get(a, a),
            "producto_b": b,
            "nombre_b": nombres.get(b, b),
            "frecuencia": freq,
        }
        for (a, b), freq in top_pairs
    ]

    interpretacion = (
        "Los pares se detectaron dentro de la misma orden."
        if metodo == "misma_orden"
        else "El dataset no tiene ordenes con multiples productos; los pares se detectaron por productos comprados por el mismo cliente en su historial."
    )

    return {
        "metodo": metodo,
        "interpretacion": interpretacion,
        "pares": pares,
    }


def calcular_frecuencia_compra_cliente(cliente_id: str) -> dict:
    tables = _tables()
    ventas = tables["ventas"]
    data = ventas[ventas["cliente_id"].astype(str) == str(cliente_id)].sort_values("fecha")

    if data.empty:
        return {"error": f"No hay ventas para el cliente {cliente_id}."}

    fechas = data.groupby("venta_id")["fecha"].min().sort_values()
    if len(fechas) == 1:
        dias_promedio = None
        frecuencia = "Compra unica en el periodo."
    else:
        dias_promedio = round(float(fechas.diff().dropna().dt.days.mean()), 2)
        frecuencia = f"Compra aproximadamente cada {dias_promedio} dias."

    return {
        "cliente_id": str(cliente_id),
        "numero_compras": int(data["venta_id"].nunique()),
        "primera_compra": str(fechas.min().date()),
        "ultima_compra": str(fechas.max().date()),
        "dias_promedio_entre_compras": dias_promedio,
        "frecuencia": frecuencia,
    }


def segmentar_clientes() -> dict:
    tables = _tables()
    ventas = tables["ventas"]
    clientes = tables["clientes"]

    metricas = ventas.groupby("cliente_id").agg(
        monto_total=("total", "sum"),
        compras=("venta_id", "nunique"),
    ).reset_index()

    monto_alto = metricas["monto_total"].quantile(0.70)
    frecuencia_alta = metricas["compras"].quantile(0.70)

    def clasificar(row):
        if row["monto_total"] >= monto_alto and row["compras"] >= frecuencia_alta:
            return "Alto valor"
        if row["monto_total"] >= monto_alto:
            return "Alto potencial"
        if row["compras"] >= frecuencia_alta:
            return "Frecuente"
        return "Bajo valor"

    metricas["segmento_calculado"] = metricas.apply(clasificar, axis=1)
    resultado = metricas.merge(clientes, on="cliente_id", how="left").sort_values("monto_total", ascending=False)

    return {
        "criterios": {
            "monto_alto_desde": round(float(monto_alto), 2),
            "frecuencia_alta_desde": round(float(frecuencia_alta), 2),
        },
        "clientes": resultado.head(20).to_dict(orient="records"),
    }


def obtener_resumen_dataset() -> dict:
    tables = _tables()
    ventas = tables["ventas"]
    clientes = tables["clientes"]
    productos = tables["productos"]

    return {
        "numero_ordenes": int(ventas["venta_id"].nunique()),
        "numero_clientes": int(clientes["cliente_id"].nunique()),
        "numero_productos": int(productos["producto_id"].nunique()),
        "ventas_totales": round(float(ventas["total"].sum()), 2),
        "fecha_minima": str(ventas["fecha"].min().date()),
        "fecha_maxima": str(ventas["fecha"].max().date()),
    }
