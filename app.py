from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime
import json
import os
import sys


sys.path.append(os.path.dirname(__file__))
from detector import BehavioralDetector

app = Flask(__name__)
CORS(app)

# Initialize ML 
detector = BehavioralDetector()

# Store behavioral data
DATA_FILE = 'behavioral_data.json'
sessions = {}

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
        
            for session_id, session in data.items():
                if 'interventions' not in session:
                    session['interventions'] = []
                if 'locked' not in session:
                    session['locked'] = False
                if 'copy_events' not in session:
                    session['copy_events'] = []
            return data
    return {}

def save_data():
    with open(DATA_FILE, 'w') as f:
        json.dump(sessions, f, indent=2)

sessions = load_data()

@app.route('/')
def index():
    return send_from_directory('static', 'login.html')

@app.route('/login')
def login_page():
    return send_from_directory('static', 'login.html')

@app.route('/assessment')
def assessment():
    return send_from_directory('static', 'assessment.html')

@app.route('/dashboard')
def dashboard():
    return send_from_directory('static', 'dashboard.html')

# Demo users 
DEMO_USERS = {
    'Vedika': {'password': 'vedika123', 'role': 'student', 'name': 'Vedika'},
    'Vishnukeerthy': {'password': 'vkr123', 'role': 'proctor', 'name': 'Vishnukeerthy'},
    'Abhinav': {'password': 'Abhinav123', 'role': 'student', 'name': 'Abhinav'},
    'Keertan': {'password': 'Keertan123', 'role': 'proctor', 'name': 'Keertan'}
}

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    role = data.get('role')
    
    # Check credentials
    if username in DEMO_USERS:
        user = DEMO_USERS[username]
        if user['password'] == password and user['name'] == username:
            return jsonify({
                'success': True,
                'user': {
                    'username': username,
                    'name': user['name'],
                    'role': user['role']
                }
            })
    
    return jsonify({
        'success': False,
        'message': 'Invalid username, password, or role'
    })

@app.route('/api/session/start', methods=['POST'])
def start_session():
    data = request.json
    session_id = data.get('session_id', str(datetime.now().timestamp()))
    
    sessions[session_id] = {
        'session_id': session_id,
        'start_time': datetime.now().isoformat(),
        'user_id': data.get('user_id', 'anonymous'),
        'user_name': data.get('username', 'name'),
        'role': data.get('role', 'student'),
        'mouse_events': [],
        'keyboard_events': [],
        'window_events': [],
        'paste_events': [],
        'copy_events': [],
        'risk_scores': [],
        'flags': [],
        'interventions': [],
        'locked': False
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
            'type': data.get('type')
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
            'event_type': data.get('event_type'),
            'duration': data.get('duration')
        }
        sessions[session_id]['window_events'].append(event)
        
        # Flag window switching
        if data.get('event_type') == 'blur':
            sessions[session_id]['flags'].append({
                'type': 'window_switch',
                'timestamp': datetime.now().isoformat(),
                'severity': 'medium'
            })
        
        save_data()
        
        # Check if intervention needed
        risk_data = get_ml_risk_score(session_id)
        return jsonify({
            'status': 'recorded',
            'risk_score': risk_data['risk_score'],
            'interventions': risk_data.get('interventions', [])
        })
    
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
        
        sessions[session_id]['flags'].append({
            'type': 'paste_detected',
            'timestamp': datetime.now().isoformat(),
            'severity': 'high',
            'length': data.get('length')
        })
        
        save_data()
        
        # Check if intervention needed
        risk_data = get_ml_risk_score(session_id)
        return jsonify({
            'status': 'recorded',
            'warning': 'Paste detected',
            'risk_score': risk_data['risk_score'],
            'interventions': risk_data.get('interventions', [])
        })
    
    return jsonify({'error': 'Invalid session'}), 400

@app.route('/api/track/copy', methods=['POST'])
def track_copy():
    data = request.json
    session_id = data.get('session_id')
    
    if session_id in sessions:
        event = {
            'timestamp': datetime.now().isoformat(),
            'length': data.get('length', 0)
        }
        sessions[session_id]['copy_events'].append(event)
        
        sessions[session_id]['flags'].append({
            'type': 'copy_detected',
            'timestamp': datetime.now().isoformat(),
            'severity': 'low'
        })
        
        save_data()
        return jsonify({'status': 'recorded'})
    
    return jsonify({'error': 'Invalid session'}), 400

def get_ml_risk_score(session_id):
    """Get ML-based risk score"""
    if session_id not in sessions:
        return {'risk_score': 0, 'severity': 'low'}
    
    session = sessions[session_id]
    
    # Use ML 
    risk_analysis = detector.calculate_risk_score(session)
    
    # Check for interventions
    interventions = detector.should_intervene(
        risk_analysis['risk_score'],
        risk_analysis['severity']
    )
    
    # Ensure interventions key exists (for old sessions)
    if 'interventions' not in session:
        session['interventions'] = []
    
    # Store interventions
    if interventions:
        for intervention in interventions:
            if intervention not in session['interventions']:
                session['interventions'].append(intervention)
                
                # Lock assessment if very suspicious
                if intervention.get('action') == 'immediate_lock':
                    session['locked'] = True
    
    save_data()
    
    return {
        'risk_score': risk_analysis['risk_score'],
        'severity': risk_analysis['severity'],
        'risk_factors': risk_analysis['risk_factors'],
        'interventions': interventions,
        'locked': session['locked']
    }

@app.route('/api/risk_score/<session_id>', methods=['GET'])
def get_risk_score(session_id):
    if session_id not in sessions:
        return jsonify({'error': 'Invalid session'}), 400
    
    risk_data = get_ml_risk_score(session_id)
    
    return jsonify({
        'session_id': session_id,
        'risk_score': risk_data['risk_score'],
        'severity': risk_data['severity'],
        'risk_level': risk_data['severity'], 
        'risk_factors': risk_data.get('risk_factors', []),
        'flags': sessions[session_id]['flags'],
        'interventions': risk_data.get('interventions', []),
        'locked': risk_data.get('locked', False)
    })

@app.route('/api/report/<session_id>', methods=['GET'])
def get_report(session_id):
    """Generate detailed integrity report"""
    if session_id not in sessions:
        return jsonify({'error': 'Invalid session'}), 400
    
    session = sessions[session_id]
    risk_analysis = detector.calculate_risk_score(session)
    report = detector.generate_report(session, risk_analysis)
    
    return jsonify(report)

@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    print(f"DEBUG: Total sessions in memory: {len(sessions)}")
    session_summary = {}
    for sid, data in sessions.items():
        # Get ML risk score
        risk_data = get_ml_risk_score(sid)
        print(f"DEBUG: Session {sid[:10]} - Risk: {risk_data['risk_score']}, Severity: {risk_data['severity']}")
        
        session_summary[sid] = {
            'user_id': data['user_id'],
            'user_name': data.get('user_name', 'Unknown'),
            'start_time': data['start_time'],
            'event_counts': {
                'mouse': len(data['mouse_events']),
                'keyboard': len(data['keyboard_events']),
                'window': len(data['window_events']),
                'paste': len(data['paste_events']),
                'copy': len(data.get('copy_events', []))
            },
            'flags': len(data['flags']),
            'risk_score': risk_data['risk_score'],
            'severity': risk_data['severity'],
            'locked': data.get('locked', False)
        }
    return jsonify(session_summary)

@app.route('/api/intervention/<session_id>', methods=['POST'])
def manual_intervention(session_id):
    """Allow admin to manually intervene"""
    if session_id not in sessions:
        return jsonify({'error': 'Invalid session'}), 400
    
    data = request.json
    action = data.get('action')
    
    if action == 'unlock':
        sessions[session_id]['locked'] = False
        sessions[session_id]['interventions'].append({
            'type': 'manual_unlock',
            'message': 'Manually unlocked by admin',
            'timestamp': datetime.now().isoformat()
        })
    elif action == 'lock':
        sessions[session_id]['locked'] = True
        sessions[session_id]['interventions'].append({
            'type': 'manual_lock',
            'message': 'Manually locked by admin',
            'timestamp': datetime.now().isoformat()
        })
    
    save_data()
    return jsonify({'status': 'success', 'locked': sessions[session_id]['locked']})

if __name__ == '__main__':
    os.makedirs('static', exist_ok=True)
    app.run(debug=True, port=5000)
