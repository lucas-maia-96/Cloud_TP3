import os
import time
import redis
import json
import importlib.util
import zipfile
import tempfile
from typing import Any, Dict


class Context:
    def __init__(self):
        self.env = {}

    def update_env(self, new_env: Dict[str, Any]):
        self.env.update(new_env)


def connect_redis():
    redis_host = os.getenv('REDIS_HOST', 'localhost')
    redis_port = os.getenv('REDIS_PORT', 6379)
    return redis.StrictRedis(host=redis_host, port=redis_port, db=0)


def monitor_redis(redis_client, input_key: str, monitoring_period: int):
    last_value = None
    while True:
        data = redis_client.get(input_key)
        if data != last_value:
            last_value = data
            yield json.loads(data)
        time.sleep(monitoring_period)


def load_function_from_config(pyfile_code: str, entry_point: str):
    try:
        spec = importlib.util.spec_from_loader("user_function", loader=None)
        user_module = importlib.util.module_from_spec(spec)
        exec(pyfile_code, user_module.__dict__)
        if not hasattr(user_module, entry_point):
            raise AttributeError(f"Entry point '{entry_point}' not found in user module")
        return getattr(user_module, entry_point)
    except Exception as e:
        raise RuntimeError(f"Error loading user function: {e}")


def load_zip_and_function(zip_path: str, entry_point: str):
    try:
        # Usar o caminho local do arquivo ZIP
        temp_dir = tempfile.TemporaryDirectory()

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir.name)

        # Supondo que o script Python esteja em 'main.py' dentro do ZIP
        spec = importlib.util.spec_from_file_location("user_function", os.path.join(temp_dir.name, "main.py"))
        user_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(user_module)

        if not hasattr(user_module, entry_point):
            raise AttributeError(f"Entry point '{entry_point}' not found in user module")
        return getattr(user_module, entry_point)
    except Exception as e:
        raise RuntimeError(f"Error loading ZIP function: {e}")


def main():
    redis_input_key = os.getenv('REDIS_INPUT_KEY', 'metrics')
    redis_output_key = os.getenv('REDIS_OUTPUT_KEY', 'metrics-output')
    redis_monitoring_period = int(os.getenv('REDIS_MONITORING_PERIOD', 5))
    function_entry_point = os.getenv('FUNCTION_ENTRY_POINT', 'handler')
    zip_file_url = os.getenv('ZIP_FILE_URL', '/mnt/shared/function.zip')  # Caminho do arquivo ZIP montado pelo PVC

    if zip_file_url and os.path.exists(zip_file_url):
        print("Usando função a partir do arquivo ZIP")
        handler = load_zip_and_function(zip_file_url, function_entry_point)
    else:
        print("Usando função a partir do código do ConfigMap (pyfile.yaml)")
        pyfile_code = os.getenv('PYFILE', '')
        handler = load_function_from_config(pyfile_code, function_entry_point)

    redis_client = connect_redis()
    context = Context()

    for input_data in monitor_redis(redis_client, redis_input_key, redis_monitoring_period):
        result = handler(input_data, context)
        redis_client.set(redis_output_key, json.dumps(result))


if __name__ == '__main__':
    main()
