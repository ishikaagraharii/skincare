from flask import Flask, session, render_template, request, jsonify
from supabase import create_client, Client
import requests
import os
import joblib
import pandas as pd
import numpy as np
from datetime import datetime
import logging

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Add a secret key for sessions

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supabase configuration
SUPABASE_URL = "https://wfpzhgqqtayplxztptbm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndmcHpoZ3FxdGF5cGx4enRwdGJtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDc5MTA5OTEsImV4cCI6MjA2MzQ4Njk5MX0.lN1rRKRbrOzcSpPCIvEVfpiVvZCHDh-3QIwB6Yz8mqk"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# API Keys
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY', 'd9df6985d7249b40ac2d2f71bbd9bd42')
OPENWEATHER_POLLUTION_URL = "http://api.openweathermap.org/data/2.5/air_pollution"

# Load ML Model and Components
try:
    model = joblib.load('skincare_recommendation_model.pkl')
    label_encoders = joblib.load('label_encoders.pkl')
    model_metadata = joblib.load('model_metadata.pkl')
    logger.info("ML model loaded successfully")
except FileNotFoundError as e:
    logger.error(f"Model files not found: {e}")
    model = None
    label_encoders = None
    model_metadata = None

# ========== ML Model Functions ==========

def create_skincare_features(df):
    """Create features more relevant to skincare recommendations"""
    df_enhanced = df.copy()

    # Pollution severity categories (based on EPA standards)
    df_enhanced['pollution_level'] = pd.cut(df_enhanced['AQI'], 
                                          bins=[0, 50, 100, 150, 200, 300, float('inf')],
                                          labels=['Good', 'Moderate', 'USG', 'Unhealthy', 'Very_Unhealthy', 'Hazardous'])

    # Weather conditions for skin health
    df_enhanced['humidity_category'] = pd.cut(df_enhanced['Humidity'],
                                            bins=[0, 30, 70, 100],
                                            labels=['Dry', 'Normal', 'Humid'])

    # Temperature categories
    df_enhanced['temp_category'] = pd.cut(df_enhanced['Temperature'],
                                        bins=[0, 10, 25, 35, float('inf')],
                                        labels=['Cold', 'Cool', 'Warm', 'Hot'])

    # Combined skin stress score (weighted by importance)
    df_enhanced['skin_stress_score'] = (
        df_enhanced['AQI'] * 0.4 + 
        df_enhanced['PM2_5'] * 0.3 + 
        df_enhanced['PM10'] * 0.2 + 
        abs(df_enhanced['Humidity'] - 50) * 0.1  # Deviation from ideal humidity
    )

    # Additional features
    df_enhanced['pm_ratio'] = df_enhanced['PM2_5'] / (df_enhanced['PM10'] + 1e-6)  # Avoid division by zero
    df_enhanced['temp_humidity_interaction'] = df_enhanced['Temperature'] * df_enhanced['Humidity'] / 100

    return df_enhanced

def recommend_skincare_product(aqi, pm25, pm10, temp, humidity, wind_speed, return_details=False):
    """
    Recommend skincare product based on environmental conditions
    """
    if not model:
        return {"error": "ML model not available"}

    try:
        # Input validation
        if not all(isinstance(x, (int, float)) for x in [aqi, pm25, pm10, temp, humidity, wind_speed]):
            raise ValueError("All inputs must be numeric")

        # Create input dataframe
        input_data = pd.DataFrame({
            'AQI': [aqi],
            'PM2_5': [pm25], 
            'PM10': [pm10],
            'Temperature': [temp],
            'Humidity': [humidity],
            'WindSpeed': [wind_speed]
        })

        # Apply same feature engineering
        input_enhanced = create_skincare_features(input_data)

        # Feature columns (same as in training)
        feature_cols = [
            'AQI', 'PM2_5', 'PM10', 'Temperature', 'Humidity', 'WindSpeed', 
            'skin_stress_score', 'pm_ratio', 'temp_humidity_interaction'
        ]

        # Encode categorical features
        for cat_col, le in label_encoders.items():
            if cat_col in input_enhanced.columns:
                try:
                    input_enhanced[f'{cat_col}_encoded'] = le.transform(input_enhanced[cat_col].astype(str))
                    feature_cols.append(f'{cat_col}_encoded')
                except ValueError:
                    # Handle unseen categories
                    input_enhanced[f'{cat_col}_encoded'] = 0
                    feature_cols.append(f'{cat_col}_encoded')
                    logger.warning(f"Unseen category in {cat_col}, using default encoding")

        # Select features
        X_input = input_enhanced[feature_cols]

        # Make prediction
        prediction = model.predict(X_input)[0]
        probabilities = model.predict_proba(X_input)[0]
        confidence = max(probabilities)

        result = {
            'recommendation': prediction,
            'confidence': confidence,
            'all_probabilities': dict(zip(model.classes_, probabilities))
        }

        if return_details:
            result['environmental_analysis'] = {
                'pollution_level': str(input_enhanced['pollution_level'].iloc[0]),
                'humidity_category': str(input_enhanced['humidity_category'].iloc[0]),
                'temp_category': str(input_enhanced['temp_category'].iloc[0]),
                'skin_stress_score': float(input_enhanced['skin_stress_score'].iloc[0])
            }

        return result

    except Exception as e:
        logger.error(f"Error in prediction: {str(e)}")
        return {"error": f"Prediction failed: {str(e)}"}

# ========== Helper Functions ==========

def get_coordinates(zip_code, country_code='IN'):
    """Get latitude and longitude for given zip and country code"""
    url = f'http://api.openweathermap.org/geo/1.0/zip?zip={zip_code},{country_code}&appid={OPENWEATHER_API_KEY}'
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get('lat'), data.get('lon')
    except requests.RequestException as e:
        logger.error(f"Error getting coordinates: {e}")
    return None, None

def get_air_pollution_data(lat, lon):
    """Get air pollution data from OpenWeather API"""
    url = f"{OPENWEATHER_POLLUTION_URL}?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if 'list' in data and len(data['list']) > 0:
                pollution_data = data['list'][0]
                components = pollution_data.get('components', {})
                aqi = pollution_data.get('main', {}).get('aqi', 1)

                # Convert AQI from 1-5 scale to US EPA scale (approximate)
                aqi_conversion = {1: 25, 2: 75, 3: 125, 4: 175, 5: 225}
                aqi_us = aqi_conversion.get(aqi, 100)

                return {
                    'aqi': aqi_us,
                    'pm2_5': components.get('pm2_5', 10),
                    'pm10': components.get('pm10', 20),
                    'co': components.get('co', 200),
                    'no2': components.get('no2', 20),
                    'o3': components.get('o3', 60),
                    'so2': components.get('so2', 5)
                }
    except requests.RequestException as e:
        logger.error(f"Error getting pollution data: {e}")

    # Return default values if API fails
    return {
        'aqi': 100,
        'pm2_5': 25,
        'pm10': 35,
        'co': 200,
        'no2': 20,
        'o3': 60,
        'so2': 5
    }

# ========== Routes ==========

@app.route("/")
def home():
    return render_template('home.html')

@app.route("/browse")
def browse():
    return render_template("browse.html")

@app.route('/set_location', methods=['POST'])
def set_location():
    data = request.get_json()
    session['location'] = {
        'id': data.get('id'),
        'zip': data.get('zip'),
        'city': data.get('description'),
        'latitude': data.get('latitude'),
        'longitude': data.get('longitude')
    }
    return jsonify({'success': True})

@app.route('/locations', methods=['GET'])
def get_locations():
    response = supabase.table('locations').select('*').execute()
    return jsonify(response.data), 200

@app.route('/get_products_by_city', methods=['GET', 'POST'])
def get_products_by_city():
    city = None
    if request.method == 'POST':
        if request.is_json:
            city = request.get_json().get('city')
        else:
            city = request.form.get('city')
    else:
        city = request.args.get('city')

    if not city:
        return jsonify({"error": "City not provided"}), 400

    weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&units=metric&appid={OPENWEATHER_API_KEY}"

    try:
        # Get weather data
        weather_resp = requests.get(weather_url, timeout=10)
        weather_resp.raise_for_status()
        weather_data = weather_resp.json()

        current_temp = weather_data['main']['temp']
        humidity = weather_data['main']['humidity']
        wind_speed = weather_data['wind']['speed']
        latitude = weather_data['coord']['lat']
        longitude = weather_data['coord']['lon']

        # Get air pollution data
        pollution_data = get_air_pollution_data(latitude, longitude)

        # Get ALL products from database (no season filtering)
        all_products_resp = supabase.table('products').select('*').execute()
        all_products = all_products_resp.data if all_products_resp.data else []

        # Get ML recommendation if model is available
        ml_recommendation = None
        recommended_products = all_products  # Default to all products

        if model:
            ml_result = recommend_skincare_product(
                aqi=pollution_data['aqi'],
                pm25=pollution_data['pm2_5'],
                pm10=pollution_data['pm10'],
                temp=current_temp,
                humidity=humidity,
                wind_speed=wind_speed,
                return_details=True
            )

            if 'error' not in ml_result:
                ml_recommendation = ml_result
                # No filtering here - let frontend handle the highlighting
                recommended_products = all_products
            else:
                logger.warning(f"ML model error: {ml_result['error']}")

        response_data = {
            "city": city,
            "current_temp": current_temp,
            "humidity": humidity,
            "wind_speed": wind_speed,
            "latitude": latitude,
            "longitude": longitude,
            "pollution_data": pollution_data,
            "products": recommended_products
        }

        # Add ML recommendation details if available
        if ml_recommendation:
            response_data["ml_recommendation"] = ml_recommendation

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error in get_products_by_city: {str(e)}")
        return jsonify({"error": f"Failed to get data: {str(e)}"}), 500

# ========== New Route for Direct ML Recommendation ==========

@app.route('/get_ml_recommendation', methods=['POST'])
def get_ml_recommendation():
    """Direct ML recommendation endpoint"""
    if not model:
        return jsonify({"error": "ML model not available"}), 503

    try:
        data = request.get_json()
        required_fields = ['aqi', 'pm25', 'pm10', 'temperature', 'humidity', 'wind_speed']

        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        result = recommend_skincare_product(
            aqi=data['aqi'],
            pm25=data['pm25'],
            pm10=data['pm10'],
            temp=data['temperature'],
            humidity=data['humidity'],
            wind_speed=data['wind_speed'],
            return_details=True
        )

        if 'error' in result:
            return jsonify(result), 400

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in ML recommendation: {str(e)}")
        return jsonify({"error": f"Recommendation failed: {str(e)}"}), 500

# ========== Category Routes (Static - No Season Logic) ==========

@app.route('/all-products')
def all_products():
    result = supabase.table('products').select('*').execute()
    return render_template('products.html', products=result.data)

@app.route('/serum')
def serum():
    result = supabase.table('products').select('*').eq('category', 'Serum').execute()
    return render_template('serum.html', products=result.data)

@app.route('/sunscreen')  
def sunscreen():
    result = supabase.table('products').select('*').eq('category', 'Sunscreen').execute()
    return render_template('sunscreen.html', products=result.data)

@app.route('/moisturizer')
def moisturizer():
    result = supabase.table('products').select('*').eq('category', 'Moisturizer').execute()
    return render_template('moisturizer.html', products=result.data)

@app.route('/bundle')
def bundle():
    result = supabase.table('products').select('*').eq('category', 'Bundle').execute()
    return render_template('bundle.html', products=result.data)

# ========== Static Season Routes (Optional - for browsing) ==========

@app.route('/winter')
def winter():
    result = supabase.table('products').select('*').eq('season', 'Winter').execute()
    return render_template('winter.html', products=result.data)

@app.route('/summer')
def summer():
    result = supabase.table('products').select('*').eq('season', 'Summer').execute()
    return render_template('summer.html', products=result.data)

@app.route('/spring')
def spring():
    result = supabase.table('products').select('*').eq('season', 'Spring').execute()
    return render_template('spring.html', products=result.data)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/newarrivals')
def newarrivals():
    return render_template('newarrivals.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)