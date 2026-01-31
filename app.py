# app.py
import json
import streamlit as st
import pandas as pd

st.set_page_config(page_title="KV Store Simulator", layout="wide")
st.title("🗄️ KV Store Simulator (Clave–Valor)")
st.caption("Simulación de una base de datos clave–valor usando `st.session_state`.")

# 1) Inicializar el kv_store en session_state
if "kv_store" not in st.session_state:
    st.session_state["kv_store"] = {}  # dict: { key (str) : value (dict) }

kv_store = st.session_state["kv_store"]

left, right = st.columns(2, gap="large")

# -------------------------
# SET: Guardar (formulario)
# -------------------------
with left:
    st.subheader("1) SET — Guardar registro")

    # JSON de ejemplo para ayudar al usuario
    example_value = {
        "productos": [
            {"sku": "A-100", "nombre": "Teclado", "cantidad": 1, "precio_unitario": 25.0},
            {"sku": "B-200", "nombre": "Mouse", "cantidad": 2, "precio_unitario": 12.5}
        ],
        "precio_total": 50.0
    }

    with st.form("set_form", clear_on_submit=False):
        key = st.text_input("Clave (ID Cliente)", placeholder="Ej: CUST-001")
        value_text = st.text_area(
            "Valor (JSON: productos + precio_total)",
            height=220,
            value=json.dumps(example_value, indent=2, ensure_ascii=False),
            help="Debe ser un objeto JSON válido. Ej: {\"productos\": [...], \"precio_total\": 123.45}"
        )

        col_a, col_b = st.columns(2)
        submit_set = col_a.form_submit_button("Guardar (SET)")
        delete_key = col_b.form_submit_button("Borrar clave (DEL)")

    if submit_set:
        if not key.strip():
            st.error("La **Clave (ID Cliente)** no puede estar vacía.")
        else:
            try:
                parsed_value = json.loads(value_text)

                if not isinstance(parsed_value, dict):
                    st.error("El **Valor** debe ser un **objeto JSON** (diccionario), no una lista.")
                else:
                    # Validación suave: esperamos productos y precio_total
                    if "productos" not in parsed_value or "precio_total" not in parsed_value:
                        st.warning(
                            "Guardado, pero nota: el JSON idealmente debería incluir `productos` y `precio_total`."
                        )

                    kv_store[key.strip()] = parsed_value
                    st.success(f"✅ Guardado: clave `{key.strip()}`")
            except json.JSONDecodeError as e:
                st.error(
                    "❌ JSON inválido. Revisa comillas, comas y llaves.\n\n"
                    f"Detalle técnico: {e}"
                )

    if delete_key:
        k = key.strip()
        if not k:
            st.error("Indica una clave para borrar.")
        elif k not in kv_store:
            st.warning(f"La clave `{k}` no existe.")
        else:
            del kv_store[k]
            st.success(f"🗑️ Borrada la clave `{k}`")

    st.divider()
    st.subheader("Estado del KV Store")
    st.write(f"Claves almacenadas: **{len(kv_store)}**")
    if kv_store:
        st.write(list(kv_store.keys()))
    else:
        st.info("Aún no hay datos guardados.")

# -------------------------
# GET: Buscar (instantáneo)
# -------------------------
with right:
    st.subheader("2) GET — Recuperar valor (instantáneo)")

    search_key = st.text_input(
        "Buscar por Clave (ID Cliente)",
        placeholder="Empieza a escribir… (ej: CUST-001)",
        key="get_key_input"
    )

    if search_key.strip():
        k = search_key.strip()
        if k in kv_store:
            record = kv_store[k]

            st.success(f"✅ Encontrado: `{k}`")
            st.json(record)

            # Vista tabular opcional si hay productos
            productos = record.get("productos")
            if isinstance(productos, list) and len(productos) > 0:
                try:
                    df = pd.json_normalize(productos)
                    st.markdown("**Productos**")
                    st.dataframe(df, use_container_width=True)
                except Exception:
                    pass

            total = record.get("precio_total")
            if total is not None:
                st.metric("Precio total", total)
        else:
            st.warning(f"⚠️ No existe la clave `{k}` en el store.")
            # Sugerencia: autocompletar mental con claves parecidas
            if kv_store:
                st.caption("Claves disponibles (referencia):")
                st.write(list(kv_store.keys()))
    else:
        st.info("Escribe una clave para ver su valor al instante.")

