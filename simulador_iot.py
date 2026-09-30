import requests
import time
import random
from datetime import datetime

# Configurações base
URL_API = "http://127.0.0.1:8080/api/sensor_hidrico"

# Calibração do Sensor Capacitivo Físico (Pino ADC do ESP32)
ADC_NO_AR_0_PCT = 3180      # Reading em 0% (Ar / Solo muito seco)
ADC_NA_AGUA_100_PCT = 1150  # Reading em 100% (Água / Solo saturado)

def converter_adc_para_porcentagem(adc_val):
    """
    Fórmula de mapeamento inverso idêntica ao map() do C++ no ESP32:
    Quanto menor o valor analógico, maior a umidade.
    """
    pct = (ADC_NO_AR_0_PCT - adc_val) / (ADC_NO_AR_0_PCT - ADC_NA_AGUA_100_PCT) * 100.0
    # Limita o resultado na faixa de 0.0% a 100.0%
    return round(max(0.0, min(100.0, pct)), 1)

def simular_envio():
    print("="*55)
    print("      BIOURBAN - SIMULADOR IOT REALISTA (ESP32)")
    print("="*55)
    
    # Solicita o ID da fazenda dinamicamente
    try:
        fazenda_id = int(input("Digite o ID da fazenda (veja na URL do navegador): "))
    except ValueError:
        print("Erro: O ID deve ser um número inteiro.")
        return

    print(f"\nSimulando lecturas de hardware real para a Fazenda #{fazenda_id}...")
    print(f"Parâmetros de calibração: 0% = {ADC_NO_AR_0_PCT} | 100% = {ADC_NA_AGUA_100_PCT}")
    print("Pressione CTRL+C para interromper a simulação.\n")
    
    try:
        while True:
            # Simula a leitura analógica bruta do ADC do ESP32.
            # Faixa variando entre Terra Seca (2945) e Terra Muito Úmida (1400)
            adc_simulado = random.randint(1400, 2945)
            
            # Converte a leitura analógica para porcentagem com base na calibração
            porcentagem = converter_adc_para_porcentagem(adc_simulado)
            
            payload = {
                "consumo": porcentagem,
                "fazenda_id": fazenda_id
            }
            
            try:
                response = requests.post(URL_API, json=payload)
                
                if response.status_code == 201:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] RAW ADC: {adc_simulado} -> Enviado: {porcentagem}%")
                else:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Erro na API: Status {response.status_code}")
            
            except requests.exceptions.ConnectionError:
                print("Erro: Não foi possível conectar ao servidor. O app.py está rodando?")
            
            # ESPERA 1 MINUTO (60 SEGUNDOS) PARA O PRÓXIMO ENVIO
            time.sleep(60)
            
    except KeyboardInterrupt:
        print("\n\nSimulação finalizada pelo usuário.")

if __name__ == "__main__":
    simular_envio()