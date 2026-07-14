import uuid

import streamlit as st

from agent_core import run_agent
from commercial_tools import obtener_resumen_dataset


st.set_page_config(
    page_title="Asistente de analitica comercial",
    layout="wide",
)


st.title("Asistente de analitica comercial")
st.caption("Analisis de ventas, clientes y productos con dataset real de ecommerce.")


if "session_id" not in st.session_state:
    st.session_state.session_id = "session-" + str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_trace" not in st.session_state:
    st.session_state.last_trace = None


with st.sidebar:
    st.subheader("Sesion")
    st.code(st.session_state.session_id)

    if st.button("Reiniciar conversacion"):
        st.session_state.session_id = "session-" + str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.last_trace = None
        st.rerun()

    st.subheader("Preguntas sugeridas")
    st.markdown(
        """
        - Dame un resumen del dataset
        - Cual es el producto de mayor venta?
        - Cual es el ticket promedio?
        - Que productos se venden mas juntos?
        - Segmenta los clientes
        """
    )


with st.expander("Resumen del dataset", expanded=True):
    try:
        st.json(obtener_resumen_dataset())
    except Exception as exc:
        st.error(f"No se pudo cargar el dataset: {exc}")


for item in st.session_state.messages:
    with st.chat_message(item["role"]):
        st.markdown(item["content"])


prompt = st.chat_input("Haz una pregunta comercial")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analizando datos comerciales..."):
            try:
                result = run_agent(prompt, st.session_state.session_id)
                st.markdown(result["answer"])
                st.session_state.last_trace = result["trace"]
                st.session_state.messages.append({"role": "assistant", "content": result["answer"]})
            except Exception as exc:
                error_message = f"Ocurrio un error: {exc}"
                st.error(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})


if st.session_state.last_trace:
    with st.expander("Evidencia y tools usadas"):
        st.json(st.session_state.last_trace)
