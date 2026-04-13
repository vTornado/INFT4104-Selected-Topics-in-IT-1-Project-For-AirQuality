import time
import json
import random
import requests
import serial
from azure.iot.device import IoTHubDeviceClient, ProvisioningDeviceClient, Message

# ==========================================
# 1. SETUP YOUR VARIABLES HERE
# ==========================================
# Serial / Arduino Configuration
COM_PORT = 'COM6'  # Change to match your Arduino port
BAUD_RATE = 9600

# IoT Central Credentials
ID_SCOPE = "0ne01189F47"
DEVICE_ID = "ArduinoMQ"
PRIMARY_KEY = "07ZeLb5ygOOZOo5ABXhWhLnhOzk63km54oYCqCeKdOg="

# Azure Machine Learning Credentials
ML_URL = "https://airquality-final.qatarcentral.inference.ml.azure.com/score"
ML_KEY = "1jJqyDIOq8akFAzQTAN485rtTI91rsF2buBBMurYXtTxlx4GrKQaJQQJ99CDAAAAAAAAAAAAINFRAZML1f3y"

# ==========================================
# 2. CONNECT TO AZURE IOT CENTRAL
# ==========================================
def connect_to_azure():
    print("Provisioning device...")
    provisioning_client = ProvisioningDeviceClient.create_from_symmetric_key(
        provisioning_host="global.azure-devices-provisioning.net",
        registration_id=DEVICE_ID,
        id_scope=ID_SCOPE,
        symmetric_key=PRIMARY_KEY
    )
    registration_result = provisioning_client.register()
    
    print("Connecting to IoT Central...")
    client = IoTHubDeviceClient.create_from_symmetric_key(
        symmetric_key=PRIMARY_KEY,
        hostname=registration_result.registration_state.assigned_hub,
        device_id=DEVICE_ID
    )
    client.connect()
    print("Connected to IoT Central Successfully!\n")
    return client

# ==========================================
# 3. INITIALIZE SERIAL CONNECTION
# ==========================================
def init_serial():
    try:
        # Timeout is set to 2 seconds so the script doesn't hang forever
        arduino = serial.Serial(COM_PORT, BAUD_RATE, timeout=2)
        print(f"Successfully connected to Arduino on {COM_PORT}\n")
        return arduino
    except Exception as e:
        print(f"Could not connect to {COM_PORT}. Defaulting to FAKE DATA mode.\n")
        return None

# ==========================================
# 4. MAIN LOOP
# ==========================================
def main():
    azure_client = connect_to_azure()
    arduino = init_serial()
    
    print("Starting dual-send process: Data to IoT Central, Predictions from ML Endpoint...\n")
    
    try:
        while True:
            aqi_value = None
            data_source = "FAKE"
            
            # --- ATTEMPT TO READ REAL DATA ---
            if arduino and arduino.is_open:
                try:
                    # Flush the input buffer to get the most recent reading, not old cached data
                    arduino.reset_input_buffer()
                    
                    # Read the line from the Arduino
                    line = arduino.readline().decode('utf-8').strip()
                    
                    if line and "=" in line:
                        # Parse "AQI = 35.5 PPM" -> extract "35.5"
                        value_part = line.split("=")[1]
                        clean_number = value_part.replace("PPM", "").strip()
                        aqi_value = float(clean_number)
                        data_source = "REAL"
                except Exception as e:
                    # If anything goes wrong reading serial, fail silently and use fake data
                    pass
            
            # --- FALLBACK TO FAKE DATA ---
            if aqi_value is None:
                aqi_value = round(random.uniform(25.0, 45.0), 2)
                data_source = "FAKE"
            
            # --- SEND TO AZURE IOT CENTRAL ---
            iot_payload = {"AQI": aqi_value}
            msg = Message(json.dumps(iot_payload))
            azure_client.send_message(msg)
            print(f"-> Sent to IoT Central [{data_source}]: {iot_payload}")
            
            # --- GET PREDICTION FROM ML ENDPOINT ---
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {ML_KEY}"
            }
            
            # Adjust this format if you get a 400 Bad Request error
            ml_payload = {"AQI": aqi_value}
            
            try:
                response = requests.post(ML_URL, headers=headers, json=ml_payload)
                if response.status_code == 200:
                    print(f"<- ML Prediction Received: {response.text}\n")
                else:
                    print(f"<- ML Error ({response.status_code}): {response.text}\n")
            except Exception as e:
                print(f"<- Failed to reach ML endpoint: {e}\n")
            
            # Pause for 5 seconds before the next loop
            time.sleep(5) 
            
    except KeyboardInterrupt:
        print("\nStopping script...")
    finally:
        if arduino and arduino.is_open:
            arduino.close()
        azure_client.disconnect()

if __name__ == "__main__":
    main()