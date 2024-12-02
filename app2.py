from flask import Flask, jsonify, request
import requests
import math

app = Flask(__name__)

def haversine(lat1, lon1, lat2, lon2):
    # 計算兩點之間的地球表面距離（公里）
    R = 6371  # 地球半徑
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

def get_nearest_aqi(lat, lon):
    api_key = "49cb22af-2b3b-4cd7-ac42-6bc73e1342be"  # 請替換為您的 API 金鑰
    url = f"https://data.moenv.gov.tw/api/v2/aqx_p_432?api_key={api_key}&format=JSON"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            min_distance = float('inf')
            nearest_station = None
            
            # 遍歷監測站以找到最近的站
            for station in data['records']:
                station_lat = float(station['latitude'])
                station_lon = float(station['longitude'])
                distance = haversine(lat, lon, station_lat, station_lon)
                
                if distance < min_distance:
                    min_distance = distance
                    nearest_station = station
            
            if nearest_station:
                return {"station": nearest_station['sitename'], "aqi": nearest_station['aqi']}
            else:
                return {"error": "無法找到最近的監測站"}
        else:
            return {"error": f"無法取得資料，狀態碼：{response.status_code}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"連線錯誤：{e}"}

@app.route('/aqi', methods=['GET'])
def aqi_route():
    try:
        latitude = float(request.args.get('latitude'))
        longitude = float(request.args.get('longitude'))
        aqi_data = get_nearest_aqi(latitude, longitude)
        return jsonify(aqi_data)
    except (TypeError, ValueError):
        return jsonify({"error": "請提供有效的經緯度"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)