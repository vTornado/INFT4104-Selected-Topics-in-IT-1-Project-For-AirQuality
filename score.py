import json
import pickle
import os

def init():
    global model
    # Tell Azure where to find the model we registered in Phase 1
    model_path = os.path.join(os.getenv('AZUREML_MODEL_DIR'), 'arima_model.pkl')
    with open(model_path, 'rb') as f:
        model = pickle.load(f)

def run(raw_data):
    try:
        # Read the incoming sensor data from IoT Central
        data = json.loads(raw_data)
        
        # Generate the next AQI prediction
        prediction = model.forecast(steps=1)
        
        # Send the prediction back as a JSON response
        return {"predicted_aqi": prediction.tolist()[0]}
    except Exception as e:
        return {"error": str(e)}