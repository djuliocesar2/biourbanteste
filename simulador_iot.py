import requests
import time
import random
from datetime import datetime

# Configurações
URL_API = "http://127.0.0.1:8080/api/sensor_hidrico"
FAZENDA_ID = 1  # Verifique o ID da sua fazenda no banco

def simular_envio():
    print(f"--- Iniciando Simulação de Sensor IoT para Fazenda #{FAZENDA_ID} ---")
    
    try:
        while True:
            # Simula um consumo entre 0.5 e 3.0 litros
            consumo_atual = round(random.uniform(0.5, 3.0), 2)
            
            payload = {
                "consumo": consumo_atual,
                "fazenda_id": FAZENDA_ID
            }
            
            response = requests.post(URL_API, json=payload)
            
            if response.status_code == 201:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Sensor: {consumo_atual}L enviado com sucesso!")
            else:
                print(f"Erro ao enviar: {response.status_code}")
            
            # Espera 5 segundos para o próximo "envio"
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\nSimulação finalizada pelo usuário.")

if __name__ == "__main__":
    simular_envio()