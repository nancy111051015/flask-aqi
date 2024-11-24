from flask import Flask, jsonify, request
import requests

app = Flask(__name__)

def get_aqi(city_name):
    # 將您的 API 金鑰代入
    api_key = "49cb22af-2b3b-4cd7-ac42-6bc73e1342be"  # 請將此替換為您的實際 API 金鑰
    url = f"https://data.moenv.gov.tw/api/v2/aqx_p_432?api_key={api_key}&format=JSON"

    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            # 遍歷回傳的資料以找到指定的城市
            for item in data['records']:
                if item['longitude'] == str(city_name):
                    aqi = item['aqi']
                    return {"city": city_name, "aqi": aqi}
            return {"error": "未找到該城市的 AQI 資料"}
        else:
            return {"error": f"無法取得資料，狀態碼：{response.status_code}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"連線錯誤：{e}"}

@app.route('/')
def home():
    return "Hello, Flask!"

# 新增一個 /aqi 路由，來提供指定城市的 AQI 數據
@app.route('/aqi', methods=['GET'])
def aqi_route():
    city = request.args.get('city', default="121.760056")  # 預設城市為基隆
    aqi_data = get_aqi(city)
    return jsonify(aqi_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)