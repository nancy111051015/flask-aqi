import os
import requests
import math
import random
from flask import Flask, jsonify, request, send_from_directory
try:
    from PIL import Image
except ImportError:
    print("Unable to import PIL. Installing Pillow...")
    import subprocess
    subprocess.check_call(["pip", "install", "Pillow"])
    from PIL import Image
import numpy as np
import io
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

# 視覺化模板配置
VISUALIZATIONS = {
    'airflow': {
        'name': '空氣流動',
        'template': 'air_flow.html',
        'color_weight': 0.4,  # 顏色影響權重
        'brightness_weight': 0.3,  # 亮度影響權重
        'contrast_weight': 0.3  # 對比度影響權重
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
    """計算兩點間的距離"""
    R = 6371  # 地球半徑（公里）
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
                return {
                    "station": nearest_station['sitename'], 
                    "aqi": nearest_station['aqi']
                }
            else:
                return {"error": "無法找到最近的監測站"}
        else:
            return {"error": f"無法取得資料，狀態碼：{response.status_code}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"連線錯誤：{e}"}

def analyze_image_features(img):
    """分析圖片特徵"""
    # 轉換為RGB格式
    img = img.convert('RGB')
    
    # 縮小圖片以加快處理速度
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
    
    # 計算色彩豐富度（轉換為HSV空間）
    hsv_colors = [colorsys.rgb_to_hsv(r/255, g/255, b/255) for r, g, b in dominant_colors]
    saturation = np.mean([hsv[1] for hsv in hsv_colors])
    
    return {
        'dominant_colors': [{'r': int(c[0]), 'g': int(c[1]), 'b': int(c[2])} for c in dominant_colors],
        'brightness': brightness,
        'contrast': contrast,
        'saturation': saturation
    }

def select_visualization(image_features):
    """基於圖片特徵選擇最適合的視覺化效果"""
    scores = {}
    
    for viz_id, viz_info in VISUALIZATIONS.items():
        score = 0
        
        # 基於亮度評分
        if image_features['brightness'] < 0.3:  # 暗色圖片
            if viz_id == 'blackhole':
                score += viz_info['brightness_weight'] * 1
        elif image_features['brightness'] > 0.7:  # 明亮圖片
            if viz_id == 'airflow':
                score += viz_info['brightness_weight'] * 1
        
        # 基於對比度評分
        if image_features['contrast'] > 0.5:  # 高對比度
            if viz_id == 'waves':
                score += viz_info['contrast_weight'] * 1
        
        # 基於色彩豐富度評分
        if image_features['saturation'] > 0.5:  # 色彩豐富
            if viz_id == 'airflow':
                score += viz_info['color_weight'] * 1
            elif viz_id == 'waves':
                score += viz_info['color_weight'] * 0.8
        
        scores[viz_id] = score
    
    # 選擇得分最高的視覺化效果，如果都沒有特別高分，則隨機選擇
    max_score = max(scores.values())
    if max_score > 0.5:
        return max(scores.items(), key=lambda x: x[1])[0]
    else:
        return random.choice(list(VISUALIZATIONS.keys()))

@app.route('/process-image', methods=['POST'])
def process_image():
    """處理上傳的圖片並返回合適的視覺化效果"""
    if 'image' not in request.files:
        return jsonify({'error': '未提供圖片'}), 400
    
    try:
        # 獲取圖片和AQI值
        image = request.files['image']
        aqi = request.form.get('aqi', type=int)
        if not aqi:
            return jsonify({'error': '未提供AQI值'}), 400
        
        # 分析圖片
        img = Image.open(image)
        image_features = analyze_image_features(img)
        
        # 選擇視覺化效果
        selected_viz = select_visualization(image_features)
        
        # 讀取對應的模板
        template_path = os.path.join('templates', VISUALIZATIONS[selected_viz]['template'])
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            # 注入圖片分析結果到模板
            template_content = template_content.replace('{{aqi}}', str(aqi))
            template_content = template_content.replace('{{dominant_color}}', 
                f"rgb({image_features['dominant_colors'][0]['r']}, "
                f"{image_features['dominant_colors'][0]['g']}, "
                f"{image_features['dominant_colors'][0]['b']})")
            
            return jsonify({
                'visualization': selected_viz,
                'template': template_content,
                'features': image_features
            })
            
        except FileNotFoundError:
            return jsonify({'error': f'找不到模板文件：{selected_viz}'}), 404
            
    except Exception as e:
        return jsonify({'error': f'處理圖片時發生錯誤：{str(e)}'}), 500

@app.route('/api/aqi', methods=['GET'])
def get_aqi():
    """獲取AQI數據的API端點"""
    try:
        latitude = float(request.args.get('latitude'))
        longitude = float(request.args.get('longitude'))
        return jsonify(get_nearest_aqi(latitude, longitude))
    except (TypeError, ValueError):
        return jsonify({"error": "無效的經緯度參數"}), 400

@app.route('/')
def home():
    """首頁"""
    return '''
    <h1>空氣品質視覺化服務</h1>
    <p>API端點：</p>
    <ul>
        <li>獲取AQI數據：GET /api/aqi?latitude=緯度&longitude=經度</li>
        <li>處理圖片：POST /process-image （需要圖片文件和AQI值）</li>
    </ul>
    '''

@app.route('/app-inventor', methods=['POST'])
def app_inventor_endpoint():
    """專門處理來自 App Inventor 的請求"""
    try:
        # 取得圖片資料
        if 'image' not in request.files:
            return jsonify({'error': '未提供圖片'}), 400
            
        image = request.files['image']
        
        # 取得 AQI 值（從請求參數中）
        aqi = request.form.get('aqi')
        if not aqi:
            return jsonify({'error': '未提供 AQI 值'}), 400
            
        # 分析圖片
        img = Image.open(image)
        image_features = analyze_image_features(img)
        
        # 選擇視覺化效果
        selected_viz = select_visualization(image_features)
        
        # 返回適合 App Inventor 解析的簡化回應
        return jsonify({
            'status': 'success',
            'visualization': selected_viz,
            'dominant_color': image_features['dominant_colors'][0]
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
