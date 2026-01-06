from flask import Flask, jsonify
from main import solve_v3

app = Flask(__name__)

@app.route('/get_captcha_token', methods=['GET'])
def get_captcha_token():
    """
    API endpoint để lấy captcha token cho Google Flow
    """
    try:
        # Gọi hàm solve_v3 với is_google_flow=True
        result = solve_v3(is_google_flow=True)

        # Trả về captcha_token
        return jsonify({
            'success': True,
            'captcha_token': result.get('captcha_token'),
            'sitekey': result.get('sitekey'),
            'page_action': result.get('page_action'),
            'timestamp': result.get('timestamp', None)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/', methods=['GET'])
def home():
    """
    Trang chủ API
    """
    return jsonify({
        'message': 'Captcha Token API',
        'endpoints': {
            'get_captcha_token': '/get_captcha_token (GET)'
        },
        'description': 'API để lấy reCAPTCHA token cho Google Flow'
    })

if __name__ == '__main__':
    print("🚀 Starting Captcha Token API Server...")
    print("📍 Available at: http://localhost:5000")
    print("🔗 Get token: http://localhost:5000/get_captcha_token")
    app.run(debug=True, host='0.0.0.0', port=5000)
