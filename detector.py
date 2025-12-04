import numpy as np
from datetime import datetime
from collections import defaultdict

class BehavioralDetector:
    """ML-based behavioral anomaly detector for academic integrity"""
    
    def __init__(self):
        self.baseline_typing_speed = 150  
        self.baseline_mouse_speed = 50 
        
    def calculate_risk_score(self, session_data):
        """Calculate comprehensive risk score using multiple behavioral signals"""
        
        risk_score = 0
        risk_factors = []
        severity = 'low'
        
        # 1. Window Switching Analysis
        window_score, window_factors = self._analyze_window_behavior(session_data)
        risk_score += window_score
        risk_factors.extend(window_factors)
        
        # 2. Paste Detection Analysis
        paste_score, paste_factors = self._analyze_paste_behavior(session_data)
        risk_score += paste_score
        risk_factors.extend(paste_factors)
        
        # 3. Typing Pattern Analysis
        typing_score, typing_factors = self._analyze_typing_patterns(session_data)
        risk_score += typing_score
        risk_factors.extend(typing_factors)
        
        # 4. Mouse Behavior Analysis
        mouse_score, mouse_factors = self._analyze_mouse_patterns(session_data)
        risk_score += mouse_score
        risk_factors.extend(mouse_factors)
        
        # 5. Temporal Analysis
        temporal_score, temporal_factors = self._analyze_temporal_patterns(session_data)
        risk_score += temporal_score
        risk_factors.extend(temporal_factors)
        
        # Cap at 100
        risk_score = min(risk_score, 100)
        
        # Determine severity
        if risk_score > 70:
            severity = 'critical'
        elif risk_score > 50:
            severity = 'high'
        elif risk_score > 30:
            severity = 'medium'
        
        return {
            'risk_score': round(risk_score, 2),
            'severity': severity,
            'risk_factors': risk_factors,
            'detailed_analysis': {
                'window_score': window_score,
                'paste_score': paste_score,
                'typing_score': typing_score,
                'mouse_score': mouse_score,
                'temporal_score': temporal_score
            }
        }
    
    def _analyze_window_behavior(self, session_data):
        """Analyze window switching patterns"""
        score = 0
        factors = []
        
        window_events = session_data.get('window_events', [])
        blur_events = [e for e in window_events if e.get('event_type') == 'blur']
        
        if len(blur_events) == 0:
            return 0, []
        
        # Frequency penalty
        if len(blur_events) > 5:
            score += 35
            factors.append(f'Excessive window switching: {len(blur_events)} times (CRITICAL)')
        elif len(blur_events) > 3:
            score += 25
            factors.append(f'Multiple window switches: {len(blur_events)} times (HIGH)')
        elif len(blur_events) > 0:
            score += 10 * len(blur_events)
            factors.append(f'Window switched {len(blur_events)} time(s)')
        
        # long absences are suspicious
        durations = [e.get('duration', 0) for e in blur_events]
        if durations:
            avg_duration = np.mean(durations)
            if avg_duration > 30000:  # 30 seconds
                score += 20
                factors.append(f'Prolonged window absence: avg {round(avg_duration/1000)}s')
        
        return score, factors
    
    def _analyze_paste_behavior(self, session_data):
        """Analyze copy-paste patterns"""
        score = 0
        factors = []
        
        paste_events = session_data.get('paste_events', [])
        
        if len(paste_events) == 0:
            return 0, []
        
        total_pasted_chars = sum(e.get('length', 0) for e in paste_events)
        
        if len(paste_events) > 3:
            score += 50
            factors.append(f'Multiple paste operations: {len(paste_events)} times (CRITICAL)')
        elif len(paste_events) > 1:
            score += 35
            factors.append(f'Multiple pastes detected: {len(paste_events)} times')
        else:
            score += 25
            factors.append('Paste operation detected')
        
        # Large paste penalty
        if total_pasted_chars > 500:
            score += 15
            factors.append(f'Large amount of pasted text: {total_pasted_chars} characters')
        
        return score, factors
    
    def _analyze_typing_patterns(self, session_data):
        """Analyze typing rhythm and patterns"""
        score = 0
        factors = []
        
        keyboard_events = session_data.get('keyboard_events', [])
        
        if len(keyboard_events) < 2:
            return 0, []
        
        # Analyze typing pace
        speeds = [e.get('typing_speed', 0) for e in keyboard_events if e.get('typing_speed')]
        
        if speeds:
            avg_speed = np.mean(speeds)
            std_speed = np.std(speeds)
            
            # Too fast is possible automation or copy-paste
            if avg_speed < 50:
                score += 20
                factors.append(f'Unusually fast typing: {round(avg_speed)}ms (possible automation)')
            
            # Too consistent is suspicious 
            if std_speed < 20 and len(speeds) > 5:
                score += 15
                factors.append('Typing rhythm too consistent (suspicious pattern)')
        
        # Backspace analysis
        total_keys = sum(e.get('key_count', 0) for e in keyboard_events)
        total_backspaces = sum(e.get('backspace_count', 0) for e in keyboard_events)
        
        if total_keys > 0:
            backspace_ratio = total_backspaces / total_keys
            
            # Too few backspaces might be pasting
            if backspace_ratio < 0.02 and total_keys > 100:
                score += 10
                factors.append('Suspiciously low error rate (possible copy-paste)')
            
            # Too many backspaces might be cheating and correcting
            if backspace_ratio > 0.3:
                score += 8
                factors.append('High correction rate (unusual editing pattern)')
        
        return score, factors
    
    def _analyze_mouse_patterns(self, session_data):
        """Analyze mouse movement patterns"""
        score = 0
        factors = []
        
        mouse_events = session_data.get('mouse_events', [])
        
        if len(mouse_events) < 5:
            score += 15
            factors.append('Very low mouse activity (possible automation)')
            return score, factors
        
        
        movements = []
        for i in range(1, len(mouse_events)):
            prev = mouse_events[i-1]
            curr = mouse_events[i]
            
            dx = curr.get('x', 0) - prev.get('x', 0)
            dy = curr.get('y', 0) - prev.get('y', 0)
            distance = np.sqrt(dx**2 + dy**2)
            movements.append(distance)
        
        if movements:
            avg_movement = np.mean(movements)
            std_movement = np.std(movements)
            
            # bot-like behavior
            if std_movement < 5 and len(movements) > 20:
                score += 12
                factors.append('Mouse movement pattern too regular (bot-like)')
            
            # Extremely erratic
            if std_movement > 200:
                score += 8
                factors.append('Erratic mouse behavior detected')
        
        return score, factors
    
    def _analyze_temporal_patterns(self, session_data):
        """Analyze time-based patterns"""
        score = 0
        factors = []
        
        # Check for suspiciously fast completion
        start_time = session_data.get('start_time')
        if start_time:
            try:
                start = datetime.fromisoformat(start_time)
                elapsed = (datetime.now() - start).total_seconds()
                
                # Completed too quickly (less than 2 minutes)
                keyboard_events = len(session_data.get('keyboard_events', []))
                if elapsed < 120 and keyboard_events > 10:
                    score += 25
                    factors.append(f'Suspiciously fast completion: {round(elapsed/60, 1)} minutes')
                
                # Idle for too long (more than 30 minutes)
                if elapsed > 1800:
                    score += 10
                    factors.append('Extended idle time detected')
            except:
                pass
        
        return score, factors
    
    def should_intervene(self, risk_score, severity):
        """Determine if intervention is needed"""
        interventions = []
        
        if severity == 'critical' or risk_score > 70:
            interventions.append({
                'type': 'lock_assessment',
                'message': 'Assessment locked due to critical integrity violations',
                'action': 'immediate_lock'
            })
        elif severity == 'high' or risk_score > 50:
            interventions.append({
                'type': 'warning',
                'message': 'High-risk behavior detected. Your session is being closely monitored.',
                'action': 'show_warning'
            })
        elif severity == 'medium' or risk_score > 30:
            interventions.append({
                'type': 'caution',
                'message': 'Please maintain focus on your assessment window.',
                'action': 'show_caution'
            })
        
        return interventions
    
    def generate_report(self, session_data, risk_analysis):
        """Generate detailed integrity report"""
        report = {
            'session_id': session_data.get('session_id'),
            'user_id': session_data.get('user_id'),
            'timestamp': datetime.now().isoformat(),
            'risk_score': risk_analysis['risk_score'],
            'severity': risk_analysis['severity'],
            'verdict': self._get_verdict(risk_analysis['risk_score']),
            'summary': risk_analysis['risk_factors'],
            'detailed_metrics': risk_analysis['detailed_analysis'],
            'recommendations': self._get_recommendations(risk_analysis)
        }
        
        return report
    
    def _get_verdict(self, risk_score):
        """Get final verdict based on risk score"""
        if risk_score > 70:
            return 'HIGH RISK - Manual review required'
        elif risk_score > 50:
            return 'MODERATE RISK - Additional verification recommended'
        elif risk_score > 30:
            return 'LOW RISK - Minor concerns noted'
        else:
            return 'MINIMAL RISK - Normal behavior pattern'
    
    def _get_recommendations(self, risk_analysis):
        """Generate recommendations based on analysis"""
        recommendations = []
        
        severity = risk_analysis['severity']
        
        if severity == 'critical':
            recommendations.append('Immediate manual review by proctor')
            recommendations.append('Consider retake under supervised conditions')
        elif severity == 'high':
            recommendations.append('Review session recording if available')
            recommendations.append('Contact student for clarification')
        elif severity == 'medium':
            recommendations.append('Flag for review')
            recommendations.append('Monitor in future assessments')
        else:
            recommendations.append('No action required')
        
        return recommendations
