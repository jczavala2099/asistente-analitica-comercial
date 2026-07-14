import os
import re
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv


load_dotenv()


def normalize_column_name(name: str) -> str:
    name = str(name).strip().lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    return name.strip("_")


def load_raw_data() -> pd.DataFrame:
    data_path = Path(os.getenv("DATA_PATH", "data/ecommerceordersdataset.csv"))
    df = pd.read_csv(data_path, sep=None, engine="python")
    df.columns = [normalize_column_name(c) for c in df.columns]
    return df


def build_product_description(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    needed = ["brand", "product_category", "product_subcategory", "product_id"]
    missing = [col for col in needed if col not in df.columns]

    if missing:
        df["product_description"] = df["product_id"].astype(str)
    else:
        df["product_description"] = (
            df["brand"].astype(str)
            + " - "
            + df["product_category"].astype(str)
            + " - "
            + df["product_subcategory"].astype(str)
            + " - "
            + df["product_id"].astype(str)
        )

    return df


def load_commercial_tables() -> dict[str, pd.DataFrame]:
    df = build_product_description(load_raw_data())

    required = [
        "order_id",
        "customer_id",
        "order_date",
        "product_id",
        "product_description",
        "product_category",
        "quantity",
        "unit_price",
        "order_amount",
    ]

    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas requeridas en el dataset: {missing}")

    work = df.copy()
    work["order_date"] = pd.to_datetime(work["order_date"], errors="coerce")
    work = work.dropna(subset=["order_date"])

    clientes_cols = ["customer_id", "customer_segment", "city", "country"]
    existing_clientes_cols = [col for col in clientes_cols if col in work.columns]

    clientes = (
        work[existing_clientes_cols]
        .sort_values("customer_id")
        .groupby("customer_id", as_index=False)
        .first()
        .rename(
            columns={
                "customer_id": "cliente_id",
                "customer_segment": "segmento",
                "city": "ciudad",
                "country": "pais",
            }
        )
    )

    if "segmento" not in clientes.columns:
        clientes["segmento"] = "Sin segmento"

    productos = (
        work[
            [
                "product_id",
                "product_description",
                "product_category",
                "product_subcategory",
                "brand",
            ]
        ]
        .drop_duplicates()
        .rename(
            columns={
                "product_id": "producto_id",
                "product_description": "nombre",
                "product_category": "categoria",
                "product_subcategory": "subcategoria",
                "brand": "marca",
            }
        )
    )

    ventas = (
        work[
            [
                "order_id",
                "order_date",
                "customer_id",
                "product_id",
                "quantity",
                "unit_price",
                "order_amount",
            ]
        ]
        .rename(
            columns={
                "order_id": "venta_id",
                "order_date": "fecha",
                "customer_id": "cliente_id",
                "product_id": "producto_id",
                "quantity": "cantidad",
                "unit_price": "precio_unitario",
                "order_amount": "total",
            }
        )
    )

    inventario = productos[["producto_id", "nombre"]].copy()
    inventario["stock_actual"] = pd.NA
    inventario["stock_minimo"] = pd.NA
    inventario["nota"] = "El dataset contiene ordenes, pero no inventario real."

    return {
        "raw": df,
        "clientes": clientes,
        "productos": productos,
        "ventas": ventas,
        "inventario": inventario,
    }
