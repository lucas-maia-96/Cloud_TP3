import streamlit as st
import redis
import json
import os
import time
import pandas as pd
import numpy as np
import re

def extract_cpu(input_string): 
    match = re.search(r"cpu\d+", input_string)  # Matches "cpu" followed by one or more digits
    if match:
        return match.group(0)
    else:
        return "Unknown"


def order_cpu_columns(df):

    cpu_cols = [col for col in df.columns if col.startswith('cpu')]
    cpu_cols.sort(key=lambda x: int(re.search(r'\d+', x).group(0))) # Extract and convert to int for sorting

    return df[cpu_cols]


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
    cpu_metrics = {extract_cpu(key): value for key, value in metrics.items() if "cpu" in key}
    
    other_metrics = {key: value for key, value in metrics.items() if "cpu" not in key}

    cpu_df = pd.DataFrame(cpu_metrics.items(), columns=["CPU", "Utilização (%)"])
    other_df = pd.DataFrame(other_metrics.items(), columns=["Métrica", "Valor"])
    
    return cpu_df, other_df

def main():
    os.environ["STREAMLIT_SERVER_PORT"] = "52046"

    st.header("Dashboard de Monitoramento de Recursos")


    st.subheader("Taxa da Atualização")
    refresh_rate = st.slider(label="Taxa de atualização (segundos)", 
                                   min_value=1,
                                   max_value=30,
                                   value=5,
                                   step=1,
                                   label_visibility="collapsed")

    placeholder = st.empty()

    redis_client = connect_redis()
    redis_output_key = os.getenv("REDIS_OUTPUT_KEY", "metrics-output")


    while True:
        metrics = fetch_metrics(redis_client, redis_output_key)

        with placeholder.container():
            if metrics:
                

                col1, col2 = st.columns(2)

                with col1:
                        if "percent-memory-cache" in metrics:
                            memory_metric = f"{metrics['percent-memory-cache']:.2f} %"
                            st.subheader("Percentage of Memory Caching Content")
                            st.metric(label="Uso de Memória Cache", value=memory_metric, border=True, label_visibility="collapsed")
                    
                with col2:
                    if "percent-network-egress" in metrics:
                        network_metric = f"{metrics['percent-network-egress']:.2f} %"
                        st.subheader("Percentage of Outgoing Traffic Bytes")
                        st.metric(label="Uso de Rede", value=network_metric, border=True, label_visibility="collapsed")

                cpu_df, other_df = process_metrics(metrics)
                cpu_df["CPU"] = cpu_df["CPU"].str.extract(r"(\d+)").astype(int)
                cpu_df = cpu_df.sort_values("CPU")

                st.subheader("Utilização da CPU por Núcleo (média móvel)")

                st.bar_chart(data=cpu_df, x="CPU", y="Utilização (%)", use_container_width=True, horizontal=True)

            else:
                st.warning("Nenhuma métrica encontrada no Redis.")

        time.sleep(refresh_rate)

if __name__ == "__main__":
    main()
