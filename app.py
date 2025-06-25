from flask import Flask, session, render_template, request, jsonify
from supabase import create_client, Client
import requests
import os

# --- Import your model function ---
from model import recommend_product_from_environment

app = Flask(__name__)

# Supabase configuration
SUPABASE_URL = "https://wfpzhgqqtayplxztptbm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInJlZiI6InN1cGFiYXNlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDc5MTA5OTEsImV4cCI6MjA2MzQ4Njk5MX0.lN1rRKRbrOzcSpPCIvEVfpiVvZCHDh-3QIwB6Yz8mqk"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# OpenWeather API key
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY', 'd9df6985d7249b40ac2d2f71bbd9bd42')


# ========== Helper Functions ==========

def get_coordinates(zip_code, country_code='IN'):
    url = f'http://api.openweathermap.org/geo/1.0/zip?zip={zip_code},{country_code}&appid={OPENWEATHER_API_KEY}'
    resp = requests.get(url)
    if resp.status_code == 200:
        data = resp.json()
        return data.get('lat'), data.get('lon')
    return None, None

def get_season_from_temp(temp_celsius):
    if temp_celsius > 25:
        return "Summer"
    elif 15 <= temp_celsius <= 25:
        return "Spring"
    elif 5 <= temp_celsius < 15:
        return "Autumn"
    else:
        return "Winter"

def get_season_from_month(month):
    if month in [3, 4, 5]:
        return 'Spring'
    elif month in [6, 7, 8]:
        return 'Summer'
    elif month in [9, 10, 11]:
        return 'Autumn'
    else:
        return 'Winter'

def get_season_by_lat_lon(lat, lon):
    url = f'https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}'
    resp = requests.get(url)
    if resp.status_code == 200:
        data = resp.json()
        from datetime import datetime
        ts = data.get('dt')
        if ts:
            return get_season_from_month(datetime.utcfromtimestamp(ts).month)
    return None


# ========== Existing Routes ==========

@app.route("/")
def home():
    return render_template('home.html')

@app.route("/browse")
def browse():
    return render_template("browse.html")

@app.route('/save_location', methods=['POST'])
def save_location():
    data = request.get_json()
    if not data or 'zip' not in data or 'description' not in data:
        return jsonify({'error': 'Invalid data'}), 400
    zip_code = data['zip']
    country_code = data.get('country', 'IN')
    description = data['description']
    lat, lon = get_coordinates(zip_code, country_code)
    if lat is None or lon is None:
        return jsonify({'error': 'Could not fetch coordinates'}), 400
    resp = supabase.table('locations').insert({
        'zip': zip_code,
        'country': country_code,
        'description': description,
        'latitude': lat,
        'longitude': lon
    }).execute()
    if resp.status_code not in (200, 201):
        return jsonify({'error': 'Failed to save location'}), 500
    return jsonify({'message': 'Location saved successfully'}), 200

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
    resp = supabase.table('locations').select('*').execute()
    return jsonify(resp.data), 200

@app.route('/products_by_location/<int:location_id>', methods=['GET'])
def get_products_by_location(location_id):
    loc_resp = supabase.table('locations').select('*').eq('id', location_id).execute()
    if not loc_resp.data:
        return jsonify({'error': 'Location not found'}), 404
    loc = loc_resp.data[0]
    season = get_season_by_lat_lon(loc['latitude'], loc['longitude'])
    if not season:
        return jsonify({'error': 'Could not determine season'}), 500
    prod_resp = supabase.table('products').select('*').eq('season', season).execute()
    return jsonify({'season': season, 'products': prod_resp.data}), 200

@app.route('/get_products_by_city', methods=['GET', 'POST'])
def get_products_by_city():
    if request.method == 'POST':
        city = request.json.get('city') if request.is_json else request.form.get('city')
    else:
        city = request.args.get('city')
    if not city:
        return jsonify({"error": "City not provided"}), 400
    weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&units=metric&appid={OPENWEATHER_API_KEY}"
    try:
        wr = requests.get(weather_url); wr.raise_for_status()
        wd = wr.json()
        current_temp = wd['main']['temp']
        season = get_season_from_temp(current_temp)
        pr = supabase.table('products').select('*').ilike('season', season).execute()
    except Exception as e:
        return jsonify({"error": f"Failed to get weather data: {e}"}), 500
    return jsonify({
        "city": city,
        "current_temp": current_temp,
        "season": season,
        "latitude": wd['coord']['lat'],
        "longitude": wd['coord']['lon'],
        "products": pr.data or []
    })


# ========== New: Model-backed Recommendation Route ==========

@app.route('/get_recommendation_by_location', methods=['GET'])
def get_recommendation_by_location():
    city = request.args.get('city')
    country = request.args.get('country', 'IN')
    if not city:
        return jsonify({"error": "City name is required"}), 400

    try:
        # 1) Geocoding
        geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city},{country}&limit=1&appid={OPENWEATHER_API_KEY}"
        geo = requests.get(geo_url); geo.raise_for_status()
        geo_data = geo.json()
        if not geo_data:
            return jsonify({"error": "City not found"}), 404
        lat, lon = geo_data[0]['lat'], geo_data[0]['lon']

        # 2) Weather
        w_url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&units=metric&appid={OPENWEATHER_API_KEY}"
        w = requests.get(w_url).json()
        temp = w['main']['temp']
        humidity = w['main']['humidity']
        wind_speed = w['wind']['speed']

        # 3) Pollution
        p_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}"
        p = requests.get(p_url).json()
        comp = p['list'][0]['components']
        aqi_index = p['list'][0]['main']['aqi']
        aqi_map = {1: 50, 2:100, 3:150, 4:200, 5:300}
        aqi = aqi_map.get(aqi_index, 150)
        pm25 = comp.get('pm2_5', 30)
        pm10 = comp.get('pm10', 50)

        # 4) Model Prediction
        inp = {
            'AQI': aqi,
            'PM2_5': pm25,
            'PM10': pm10,
            'Temperature': temp,
            'Humidity': humidity,
            'WindSpeed': wind_speed
        }
        rec = recommend_product_from_environment(inp)

        return jsonify({
            "city": city,
            "coordinates": {"lat": lat, "lon": lon},
            "weather": {"temperature": temp, "humidity": humidity, "wind_speed": wind_speed},
            "pollution": {"aqi": aqi, "pm25": pm25, "pm10": pm10},
            "recommendation": rec
        })

    except Exception as e:
        return jsonify({"error": f"Failed to process request: {str(e)}"}), 500


# ========== Remaining Category & Season Pages ==========

@app.route('/all-products')
def all_products():
    result = supabase.table('products').select('*').execute()
    return render_template('products.html', products=result.data)

@app.route('/serum')
def serum():
    result = supabase.table('products').select('*').eq('category','Serum').execute()
    return render_template('serum.html', products=result.data)

@app.route('/sunscreen')
def sunscreen():
    result = supabase.table('products').select('*').eq('category','Sunscreen').execute()
    return render_template('sunscreen.html', products=result.data)

@app.route('/moisturizer')
def moisturizer():
    result = supabase.table('products').select('*').eq('category','Moisturizer').execute()
    return render_template('moisturizer.html', products=result.data)

@app.route('/bundle')
def bundle():
    result = supabase.table('products').select('*').eq('category','Bundle').execute()
    return render_template('bundle.html', products=result.data)

@app.route('/winter')
def winter():
    result = supabase.table('products').select('*').eq('season','Winter').execute()
    return render_template('winter.html', products=result.data)

@app.route('/summer')
def summer():
    result = supabase.table('products').select('*').eq('season','Summer').execute()
    return render_template('summer.html', products=result.data)

@app.route('/spring')
def spring():
    result = supabase.table('products').select('*').eq('season','Spring').execute()
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
