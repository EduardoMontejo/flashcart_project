import json
import time
import pandas as pd
import streamlit as st

TTL_SECONDS = 60

st.set_page_config(page_title="KV Store Simulator (TTL + Infra)", layout="wide")
st.title("🗄️ KV Store Simulator (Clave–Valor) + TTL + Infra Analytics")
st.caption(f"KV Store en `st.session_state` con TTL={TTL_SECONDS}s y analítica de consumo (bytes).")

# ---- Init store ----
# kv_store[key] = {"value": <dict>, "created_at": <epoch_seconds>}
if "kv_store" not in st.session_state:
    st.session_state["kv_store"] = {}

kv_store = st.session_state["kv_store"]

def now() -> float:
    return time.time()

def is_expired(created_at: float, ttl: int = TTL_SECONDS) -> bool:
    return (now() - created_at) > ttl

def value_size_bytes(value: dict) -> int:
    """
    Tamaño aproximado en bytes del valor guardado.
    Se mide como tamaño del JSON serializado (UTF-8).
    """
    try:
        return len(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    except Exception:
        # Fallback ultra defensivo
        return len(str(value).encode("utf-8"))

def cleanup_expired(ttl: int = TTL_SECONDS) -> int:
    expired_keys = [k for k, v in kv_store.items() if is_expired(v["created_at"], ttl)]
    for k in expired_keys:
        del kv_store[k]
    return len(expired_keys)

def build_status_table(ttl: int = TTL_SECONDS) -> pd.DataFrame:
    """Tabla con estado (Activa/Expirada) + edad + bytes por clave."""
    rows = []
    t = now()
    for k, payload in kv_store.items():
        created_at = float(payload["created_at"])
        age = t - created_at
        expired = age > ttl

        val = payload.get("value", {})
        size_b = value_size_bytes(val)

        rows.append(
            {
                "cliente_id": k,
                "estado": "Expirada" if expired else "Activa",
                "edad_seg": int(age),
                "restante_seg": max(0, int(ttl - age)),
                "size_bytes": int(size_b),
                "created_at_epoch": int(created_at),
            }
        )

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(["estado", "size_bytes"], ascending=[True, False]).reset_index(drop=True)
    return df

left, right = st.columns(2, gap="large")

# -------------------------
# SET: Guardar (formulario)
# -------------------------
with left:
    st.subheader("1) SET — Guardar registro (con timestamp)")

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
            help="Debe ser un objeto JSON válido (dict)."
        )
        col_a, col_b = st.columns(2)
        submit_set = col_a.form_submit_button("Guardar (SET)")
        delete_key = col_b.form_submit_button("Borrar clave (DEL)")

    if submit_set:
        k = key.strip()
        if not k:
            st.error("La **Clave (ID Cliente)** no puede estar vacía.")
        else:
            try:
                parsed_value = json.loads(value_text)
                if not isinstance(parsed_value, dict):
                    st.error("El **Valor** debe ser un **objeto JSON** (diccionario), no una lista.")
                else:
                    kv_store[k] = {"value": parsed_value, "created_at": now()}
                    st.success(f"✅ Guardado: clave `{k}` (TTL {TTL_SECONDS}s)")
                    st.caption(f"Tamaño aprox del valor: {value_size_bytes(parsed_value)} bytes (JSON UTF-8)")
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
    st.subheader("Mantenimiento TTL")

    col_c, col_d = st.columns([1, 2])
    if col_c.button("🧹 Limpiar expiradas"):
        removed = cleanup_expired(TTL_SECONDS)
        if removed > 0:
            st.success(f"Se borraron **{removed}** claves expiradas (> {TTL_SECONDS}s).")
        else:
            st.info("No había claves expiradas para borrar.")
    col_d.caption("La limpieza solo ocurre al pulsar el botón (simula un job/cron).")

    st.write(f"Claves almacenadas actualmente: **{len(kv_store)}**")

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
            payload = kv_store[k]
            created_at = payload["created_at"]
            expired = is_expired(created_at, TTL_SECONDS)
            val = payload["value"]

            if expired:
                st.warning(f"⚠️ La clave `{k}` está **EXPIRADA** (más de {TTL_SECONDS}s).")
            else:
                st.success(f"✅ Encontrado: `{k}` (Activa)")

            st.json(val)

            # Métricas rápidas “infra”
            age = int(now() - created_at)
            st.caption(f"Edad del registro: **{age}s** | TTL: **{TTL_SECONDS}s**")
            st.metric("Tamaño del valor (bytes)", value_size_bytes(val))

        else:
            st.warning(f"⚠️ No existe la clave `{k}` en el store.")
    else:
        st.info("Escribe una clave para ver su valor al instante.")

# -------------------------
# Estado + Infra Analytics
# -------------------------
st.divider()
st.subheader("📋 Estado del KV Store (Activa vs Expirada)")

status_df = build_status_table(TTL_SECONDS)

if status_df.empty:
    st.info("No hay claves en el store todavía.")
else:
    # 1) Tabla estado + bytes
    st.dataframe(status_df, use_container_width=True)

    # Métricas (conteos + tamaño total)
    expired_count = int((status_df["estado"] == "Expirada").sum())
    active_count = int((status_df["estado"] == "Activa").sum())
    total_cache_bytes = int(status_df["size_bytes"].sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Activas", active_count)
    c2.metric("Expiradas", expired_count)
    c3.metric("TTL (s)", TTL_SECONDS)
    # 3) Métrica total caché (bytes)
    c4.metric("Peso total caché (bytes)", total_cache_bytes)

    st.divider()
    st.subheader("📊 Infra Analytics: consumo de memoria por cliente (aprox.)")

    # 2) Bar chart: bytes por cliente
    # st.bar_chart espera serie o df con índice; dejamos cliente_id como índice
    mem_df = status_df[["cliente_id", "size_bytes"]].set_index("cliente_id")
    st.bar_chart(mem_df)

    st.caption(
        "Nota: este cálculo es una **aproximación** basada en el tamaño del JSON serializado (UTF-8). "
        "No representa exactamente el overhead interno de Python, pero es excelente para comparar consumo relativo por clave."
    )
