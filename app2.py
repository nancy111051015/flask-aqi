from flask import Flask, jsonify, request
import requests
import math

app = Flask(__name__)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
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
                return {"station": nearest_station['sitename'], 
                       "aqi": nearest_station['aqi']}
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

@app.route('/visualization')
def visualization():
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Air Flow Dance</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/react/18.2.0/umd/react.production.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/react-dom/18.2.0/umd/react-dom.production.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/tailwindcss/2.2.19/tailwind.min.js"></script>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0; padding:0;">
    <div id="root"></div>
    <script>
        function getAQIFromURL() {
            const params = new URLSearchParams(window.location.search);
            return parseInt(params.get('aqi')) || 50;
        }

        const AirFlowDance = () => {
            const canvasRef = React.useRef(null);
            const [aqi, setAqi] = React.useState(getAQIFromURL());
            const animationRef = React.useRef(null);

            const getAQIColor = (value) => {
                if (value <= 50) return '#00e800';
                if (value <= 100) return '#ffd700';
                if (value <= 150) return '#ff7e00';
                if (value <= 200) return '#ff0000';
                if (value <= 300) return '#99004c';
                return '#7e0023';
            };

            const getAQIStatus = (value) => {
                if (value <= 50) return '良好';
                if (value <= 100) return '普通';
                if (value <= 150) return '輕度污染';
                if (value <= 200) return '中度污染';
                if (value <= 300) return '重度污染';
                return '嚴重污染';
            };

            React.useEffect(() => {
                const canvas = canvasRef.current;
                if (!canvas) return;

                const ctx = canvas.getContext('2d');
                if (!ctx) return;

                class Particle {
                    constructor() {
                        this.x = Math.random() * canvas.width;
                        this.y = Math.random() * canvas.height;
                        this.speed = 0;
                        this.size = 0;
                        this.angle = 0;
                        this.wobble = 0;
                        this.wobbleSpeed = 0;
                        this.reset();
                    }

                    reset() {
                        const baseSpeed = Math.min(aqi / 50, 6);
                        this.speed = baseSpeed * (Math.random() * 0.5 + 0.5);
                        this.size = Math.random() * 2 + 1;
                        this.angle = Math.random() * Math.PI * 2;
                        this.wobble = Math.random() * Math.PI * 2;
                        this.wobbleSpeed = 0.1 + Math.random() * 0.1;
                    }

                    update() {
                        this.wobble += this.wobbleSpeed;
                        const chaos = Math.min(aqi / 100, 3);
                        const wobbleStrength = chaos * Math.sin(this.wobble) * 0.3;
                        
                        this.x += Math.cos(this.angle + wobbleStrength) * this.speed;
                        this.y += Math.sin(this.angle + wobbleStrength) * this.speed;
                        
                        if (this.x < 0) this.x = canvas.width;
                        if (this.x > canvas.width) this.x = 0;
                        if (this.y < 0) this.y = canvas.height;
                        if (this.y > canvas.height) this.y = 0;
                        
                        this.angle += (Math.random() - 0.5) * 0.1 * chaos;
                    }

                    draw() {
                        ctx.beginPath();
                        ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
                        ctx.fillStyle = getAQIColor(aqi);
                        ctx.fill();
                    }
                }

                const particles = [];
                const particleCount = Math.min(Math.floor(aqi * 1.5), 300);
                
                for (let i = 0; i < particleCount; i++) {
                    particles.push(new Particle());
                }

                const animate = () => {
                    ctx.fillStyle = 'rgba(255, 255, 255, 0.1)';
                    ctx.fillRect(0, 0, canvas.width, canvas.height);
                    
                    particles.forEach(particle => {
                        particle.update();
                        particle.draw();
                    });
                    
                    animationRef.current = requestAnimationFrame(animate);
                };

                animate();

                const checkAQIUpdate = () => {
                    const newAQI = getAQIFromURL();
                    if (newAQI !== aqi) {
                        setAqi(newAQI);
                    }
                };
                
                const intervalId = setInterval(checkAQIUpdate, 1000);

                return () => {
                    if (animationRef.current) {
                        cancelAnimationFrame(animationRef.current);
                    }
                    clearInterval(intervalId);
                };
            }, [aqi]);

            return React.createElement('div', { 
                className: 'w-full h-screen flex flex-col items-center justify-center p-4',
                style: { maxWidth: '100vw', margin: '0 auto' }
            },
                React.createElement('div', { 
                    className: 'w-full max-w-lg space-y-4'
                },
                    React.createElement('div', { 
                        className: 'flex items-center justify-between bg-white p-2 rounded-lg shadow'
                    },
                        React.createElement('span', { 
                            className: 'text-lg font-medium'
                        }, 
                            'AQI 值: ' + aqi
                        ),
                        React.createElement('span', { 
                            className: 'text-sm',
                            style: { color: getAQIColor(aqi) }
                        }, 
                            getAQIStatus(aqi)
                        )
                    ),
                    
                    React.createElement('input', {
                        type: 'range',
                        min: '0',
                        max: '500',
                        value: aqi,
                        onChange: (e) => setAqi(Number(e.target.value)),
                        className: 'w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer'
                    }),
                    
                    React.createElement('canvas', {
                        ref: canvasRef,
                        width: 400,
                        height: 300,
                        className: 'w-full border border-gray-200 rounded-lg bg-white shadow-md'
                    })
                )
            );
        };

        ReactDOM.render(
            React.createElement(AirFlowDance),
            document.getElementById('root')
        );
    </script>
</body>
</html>
    """
    return html_content

@app.route('/')
def home():
    return '''
    <h1>空氣品質視覺化服務</h1>
    <p>使用方式:</p>
    <ul>
        <li>JSON API: /aqi?latitude=緯度&longitude=經度</li>
        <li>視覺化: /visualization?aqi=AQI值</li>
    </ul>
    '''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)