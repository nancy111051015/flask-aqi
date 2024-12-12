import os
import requests
import math
import random
from flask import Flask, jsonify, request, render_template
from PIL import Image
import numpy as np
from sklearn.cluster import KMeans
import colorsys

app = Flask(__name__)

# CORS 支持
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
    return response

VISUALIZATIONS = {
    'airflow': {
        'name': '空氣流動',
        'template': 'air_flow.html',
        'color_weight': 0.4,
        'brightness_weight': 0.3,
        'contrast_weight': 0.3
    },
    'waves': {
        'name': '波紋擴散',
        'template': 'waves.html',
        'color_weight': 0.5,
        'brightness_weight': 0.3,
        'contrast_weight': 0.2
    },
    'blackhole': {
        'name': '宇宙黑洞',
        'template': 'black_hole.html',
        'color_weight': 0.3,
        'brightness_weight': 0.4,
        'contrast_weight': 0.3
    }
}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c

def get_nearest_aqi(lat, lon):
    api_key = "49cb22af-2b3b-4cd7-ac42-6bc73e1342be"
    url = f"https://data.moenv.gov.tw/api/v2/aqx_p_432?api_key={api_key}&format=JSON"

    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            min_distance = float('inf')
            nearest_station = None

            for station in data['records']:
                station_lat = float(station['latitude'])
                station_lon = float(station['longitude'])
                distance = haversine(lat, lon, station_lat, station_lon)

                if distance < min_distance:
                    min_distance = distance
                    nearest_station = station

            if nearest_station:
                return {
                    "status": "success",
                    "station": nearest_station['sitename'],
                    "aqi": nearest_station['aqi']
                }
            else:
                return {"status": "error", "message": "無法找到最近的監測站"}
        else:
            return {"status": "error", "message": f"無法取得資料，狀態碼：{response.status_code}"}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"連線錯誤：{e}"}

def analyze_image_features(img):
    img = img.convert('RGB')
    img = img.resize((150, 150))
    img_array = np.array(img)

    pixels = img_array.reshape(-1, 3)
    kmeans = KMeans(n_clusters=5)
    kmeans.fit(pixels)
    dominant_colors = kmeans.cluster_centers_.astype(int)

    gray = img.convert('L')
    brightness = float(np.array(gray).mean()) / 255.0
    contrast = float(np.array(gray).std()) / 255.0

    hsv_colors = [colorsys.rgb_to_hsv(r/255, g/255, b/255) for r, g, b in dominant_colors]
    saturation = np.mean([hsv[1] for hsv in hsv_colors])

    return {
        'dominant_colors': [{'r': int(c[0]), 'g': int(c[1]), 'b': int(c[2])} for c in dominant_colors],
        'brightness': brightness,
        'contrast': contrast,
        'saturation': saturation
    }

def select_visualization(image_features):
    scores = {}

    for viz_id, viz_info in VISUALIZATIONS.items():
        score = 0

        if image_features['brightness'] < 0.3 and viz_id == 'blackhole':
            score += viz_info['brightness_weight']
        elif image_features['brightness'] > 0.7 and viz_id == 'airflow':
            score += viz_info['brightness_weight']

        if image_features['contrast'] > 0.5 and viz_id == 'waves':
            score += viz_info['contrast_weight']

        if image_features['saturation'] > 0.5:
            if viz_id == 'airflow':
                score += viz_info['color_weight']
            elif viz_id == 'waves':
                score += viz_info['color_weight'] * 0.8

        scores[viz_id] = score

    max_score = max(scores.values())
    return max(scores.items(), key=lambda x: x[1])[0] if max_score > 0.5 else random.choice(list(VISUALIZATIONS.keys()))

@app.route('/api/aqi', methods=['GET'])
def get_aqi():
    try:
        latitude = float(request.args.get('latitude'))
        longitude = float(request.args.get('longitude'))
        return jsonify(get_nearest_aqi(latitude, longitude))
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "無效的經緯度參數"}), 400

@app.route('/app-inventor', methods=['POST'])
def app_inventor_endpoint():
    try:
        if 'image' not in request.files:
            return jsonify({'status': 'error', 'message': '未提供圖片'}), 400

        image = request.files['image']
        aqi = request.form.get('aqi', type=int)
        if not aqi:
            return jsonify({'status': 'error', 'message': '未提供 AQI 值'}), 400

        img = Image.open(image)
        image_features = analyze_image_features(img)
        selected_viz = select_visualization(image_features)

        return jsonify({
            'status': 'success',
            'visualization': selected_viz,
            'dominant_color': image_features['dominant_colors'][0]
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
