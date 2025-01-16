import streamlit as st
import redis
import json
import os
import time
import pandas as pd
import numpy as np

def connect_redis():
    """Conecta ao Redis usando variáveis de ambiente."""
    redis_host = os.getenv('REDIS_HOST', 'localhost')
    redis_port = int(os.getenv('REDIS_PORT', 6379))
    return redis.StrictRedis(host=redis_host, port=redis_port, db=0, decode_responses=True)

def fetch_metrics(redis_client, key):
    """Busca métricas do Redis."""
    try:
        data = redis_client.get(key)
        if data:
            return json.loads(data)
        return {}
    except Exception as e:
        st.error(f"Erro ao buscar dados do Redis: {e}")
        return {}

def process_metrics(metrics):
    """Converte as métricas em um DataFrame para visualização."""
    cpu_metrics = {key: value for key, value in metrics.items() if "cpu" in key}
    
    other_metrics = {key: value for key, value in metrics.items() if "cpu" not in key}

    cpu_df = pd.DataFrame(cpu_metrics.items(), columns=["CPU", "Utilização (%)"])
    other_df = pd.DataFrame(other_metrics.items(), columns=["Métrica", "Valor"])
    
    return cpu_df, other_df

def main():
    os.environ["STREAMLIT_SERVER_PORT"] = "52011"

    st.title("Dashboard de Monitoramento")
    st.markdown("Exibe métricas computadas pelo servidor.")

    redis_client = connect_redis()
    redis_output_key = os.getenv("REDIS_OUTPUT_KEY", "metrics-output")

    st.sidebar.markdown("### Opções")
    refresh_rate = st.sidebar.slider("Taxa de atualização (segundos)", 1, 30, 5)

    st.header("Métricas")
    placeholder = st.empty()

    while True:
        metrics = fetch_metrics(redis_client, redis_output_key)

        with placeholder.container():
            if metrics:
                cpu_df, other_df = process_metrics(metrics)

                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("Utilização da CPU")
                    st.line_chart(cpu_df.set_index("CPU")["Utilização (%)"])

                with col2:
                    st.subheader("Uso de CPU por núcleo")
                    st.bar_chart(cpu_df.set_index("CPU")["Utilização (%)"])

                col3, col4 = st.columns(2)

                with col3:
                    if "percent-memory-cache" in metrics:
                        memory_metric = {"percent-memory-cache": metrics["percent-memory-cache"]}
                        st.subheader("Uso de Memória Cache (percent-memory-cache)")
                        st.bar_chart(pd.DataFrame(memory_metric.items(), columns=["Métrica", "Valor"]).set_index("Métrica")["Valor"])

            else:
                st.warning("Nenhuma métrica encontrada no Redis.")

        time.sleep(refresh_rate)

if __name__ == "__main__":
    main()
