from flask import Flask, jsonify, request, render_template
import os
import requests
import math
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

def haversine(lat1, lon1, lat2, lon2):
    """計算兩點間的距離"""
    R = 6371
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

def get_nearest_aqi(lat, lon):
    """獲取最近監測站的 AQI 數據"""
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
                return {"aqi": nearest_station['aqi']}  # 簡化返回格式
            else:
                return {"aqi": "0"}
        else:
            return {"aqi": "0"}
    except Exception:
        return {"aqi": "0"}

def analyze_image_features(img):
    """分析圖片特徵"""
    img = img.convert('RGB')
    img = img.resize((150, 150))
    img_array = np.array(img)
    
    # 提取主要顏色
    pixels = img_array.reshape(-1, 3)
    kmeans = KMeans(n_clusters=5)
    kmeans.fit(pixels)
    dominant_colors = kmeans.cluster_centers_.astype(int)
    
    # 計算整體亮度
    gray = img.convert('L')
    brightness = float(np.array(gray).mean()) / 255.0
    
    # 計算對比度
    contrast = float(np.array(gray).std()) / 255.0
    
    # 計算色彩豐富度
    hsv_colors = [colorsys.rgb_to_hsv(r/255, g/255, b/255) for r, g, b in dominant_colors]
    saturation = np.mean([hsv[1] for hsv in hsv_colors])
    
    return {
        'brightness': brightness,
        'contrast': contrast,
        'saturation': saturation
    }

def select_visualization(image_features):
    """基於圖片特徵選擇視覺化效果"""
    if image_features['brightness'] < 0.3:
        return "blackhole"
    elif image_features['contrast'] > 0.5:
        return "waves"
    else:
        return "airflow"

@app.route('/api/aqi', methods=['GET'])
def get_aqi_endpoint():
    """第一步：獲取 AQI 值的端點"""
    try:
        latitude = float(request.args.get('latitude'))
        longitude = float(request.args.get('longitude'))
        return jsonify(get_nearest_aqi(latitude, longitude))
    except (TypeError, ValueError):
        return jsonify({"aqi": "0"})

@app.route('/app-inventor', methods=['POST'])
def app_inventor_endpoint():
    """第二步：處理圖片並返回合適的視覺化類型"""
    try:
        if 'image' not in request.files:
            return jsonify({"visualization": "airflow"})  # 預設值
            
        image = request.files['image']
        img = Image.open(image)
        image_features = analyze_image_features(img)
        selected_viz = select_visualization(image_features)
        
        return jsonify({"visualization": selected_viz})
        
    except Exception as e:
        return jsonify({"visualization": "airflow"})  # 發生錯誤時返回預設值

@app.route('/visualization')
def visualization():
    """第三步：返回視覺化效果"""
    style = request.args.get('style', 'airflow')  # 預設使用 airflow
    aqi = request.args.get('aqi', '0')  # 預設 AQI 值為 0
    
    # 根據 style 選擇對應的模板
    template_mapping = {
        'airflow': 'air_flow.html',
        'waves': 'waves.html',
        'blackhole': 'black_hole.html'
    }
    
    template_name = template_mapping.get(style, 'air_flow.html')
    
    try:
        return render_template(template_name, aqi=aqi)
    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)