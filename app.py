from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime
import json
import os

app = Flask(__name__)
CORS(app)

# Store behavioral data in memory (use JSON file for persistence)
DATA_FILE = 'behavioral_data.json'
sessions = {}

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_data():
    with open(DATA_FILE, 'w') as f:
        json.dump(sessions, f, indent=2)

sessions = load_data()

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/assessment')
def assessment():
    return send_from_directory('static', 'assessment.html')

@app.route('/dashboard')
def dashboard():
    return send_from_directory('static', 'dashboard.html')

@app.route('/api/session/start', methods=['POST'])
def start_session():
    data = request.json
    session_id = data.get('session_id', str(datetime.now().timestamp()))
    
    sessions[session_id] = {
        'start_time': datetime.now().isoformat(),
        'user_id': data.get('user_id', 'anonymous'),
        'mouse_events': [],
        'keyboard_events': [],
        'window_events': [],
        'paste_events': [],
        'risk_scores': [],
        'flags': []
    }
    
    save_data()
    return jsonify({'session_id': session_id, 'status': 'started'})

@app.route('/api/track/mouse', methods=['POST'])
def track_mouse():
    data = request.json
    session_id = data.get('session_id')
    
    if session_id in sessions:
        sessions[session_id]['mouse_events'].append({
            'timestamp': datetime.now().isoformat(),
            'x': data.get('x'),
            'y': data.get('y'),
            'type': data.get('type')  # move, click, scroll
        })
        save_data()
        return jsonify({'status': 'recorded'})
    
    return jsonify({'error': 'Invalid session'}), 400

@app.route('/api/track/keyboard', methods=['POST'])
def track_keyboard():
    data = request.json
    session_id = data.get('session_id')
    
    if session_id in sessions:
        sessions[session_id]['keyboard_events'].append({
            'timestamp': datetime.now().isoformat(),
            'key_count': data.get('key_count'),
            'typing_speed': data.get('typing_speed'),
            'backspace_count': data.get('backspace_count')
        })
        save_data()
        return jsonify({'status': 'recorded'})
    
    return jsonify({'error': 'Invalid session'}), 400

@app.route('/api/track/window', methods=['POST'])
def track_window():
    data = request.json
    session_id = data.get('session_id')
    
    if session_id in sessions:
        event = {
            'timestamp': datetime.now().isoformat(),
            'event_type': data.get('event_type'),  # blur, focus
            'duration': data.get('duration')
        }
        sessions[session_id]['window_events'].append(event)
        
        # Flag suspicious window switching
        if data.get('event_type') == 'blur':
            sessions[session_id]['flags'].append({
                'type': 'window_switch',
                'timestamp': datetime.now().isoformat(),
                'severity': 'medium'
            })
        
        save_data()
        return jsonify({'status': 'recorded'})
    
    return jsonify({'error': 'Invalid session'}), 400

@app.route('/api/track/paste', methods=['POST'])
def track_paste():
    data = request.json
    session_id = data.get('session_id')
    
    if session_id in sessions:
        event = {
            'timestamp': datetime.now().isoformat(),
            'length': data.get('length')
        }
        sessions[session_id]['paste_events'].append(event)
        
        # Flag paste event
        sessions[session_id]['flags'].append({
            'type': 'paste_detected',
            'timestamp': datetime.now().isoformat(),
            'severity': 'high',
            'length': data.get('length')
        })
        
        save_data()
        return jsonify({'status': 'recorded', 'warning': 'Paste detected'})
    
    return jsonify({'error': 'Invalid session'}), 400

@app.route('/api/risk_score/<session_id>', methods=['GET'])
def get_risk_score(session_id):
    if session_id not in sessions:
        return jsonify({'error': 'Invalid session'}), 400
    
    session = sessions[session_id]
    
    # Simple rule-based risk calculation
    risk_score = 0
    risk_factors = []
    
    # Window switching penalty
    window_switches = len([e for e in session['window_events'] if e['event_type'] == 'blur'])
    if window_switches > 3:
        risk_score += 30
        risk_factors.append(f'Excessive window switching ({window_switches} times)')
    elif window_switches > 0:
        risk_score += 10 * window_switches
    
    # Paste detection penalty
    paste_count = len(session['paste_events'])
    if paste_count > 0:
        risk_score += 40 * paste_count
        risk_factors.append(f'Paste detected ({paste_count} times)')
    
    # Mouse inactivity (too few movements might indicate automation)
    mouse_events = len(session['mouse_events'])
    if mouse_events < 10:
        risk_score += 20
        risk_factors.append('Suspiciously low mouse activity')
    
    # Cap risk score at 100
    risk_score = min(risk_score, 100)
    
    return jsonify({
        'session_id': session_id,
        'risk_score': risk_score,
        'risk_level': 'high' if risk_score > 60 else 'medium' if risk_score > 30 else 'low',
        'risk_factors': risk_factors,
        'flags': session['flags']
    })

@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    session_summary = {}
    for sid, data in sessions.items():
        session_summary[sid] = {
            'user_id': data['user_id'],
            'start_time': data['start_time'],
            'event_counts': {
                'mouse': len(data['mouse_events']),
                'keyboard': len(data['keyboard_events']),
                'window': len(data['window_events']),
                'paste': len(data['paste_events'])
            },
            'flags': len(data['flags'])
        }
    return jsonify(session_summary)

if __name__ == '__main__':
    os.makedirs('static', exist_ok=True)
    app.run(debug=True, port=5000)