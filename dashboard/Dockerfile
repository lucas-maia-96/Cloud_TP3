FROM python:3.10-slim

RUN pip install --no-cache-dir streamlit redis

WORKDIR /app
COPY dashboard.py .

EXPOSE 52011

ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_PORT=52011

ENTRYPOINT ["streamlit", "run", "dashboard.py", "--server.port=52011", "--server.address=0.0.0.0"]
