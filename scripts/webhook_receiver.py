#!/usr/bin/env python3
"""
Serveur webhook simple pour recevoir les alertes d'AlertManager
Utile pour tester le système de notifications
"""

from flask import Flask, request, jsonify
from datetime import datetime
import json

app = Flask(__name__)

# Stockage des alertes reçues
alerts_received = []

@app.route('/alerts/<severity>', methods=['POST'])
def receive_alert(severity):
    """Endpoint pour recevoir les alertes"""
    data = request.get_json()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("\n" + "=" * 70)
    print(f"[{timestamp}] ALERTE RECUE - Severity: {severity.upper()}")
    print("=" * 70)

    if 'alerts' in data:
        for alert in data['alerts']:
            alert_name = alert.get('labels', {}).get('alertname', 'Unknown')
            status = alert.get('status', 'N/A')
            description = alert.get('annotations', {}).get('description', 'N/A')

            print(f"  Alert: {alert_name}")
            print(f"  Status: {status}")
            print(f"  Description: {description}")
            print(f"  Labels: {json.dumps(alert.get('labels', {}), indent=4)}")
            print("-" * 70)

            # Sauvegarder l'alerte
            alerts_received.append({
                'timestamp': timestamp,
                'severity': severity,
                'alert_name': alert_name,
                'status': status,
                'description': description,
                'labels': alert.get('labels', {}),
                'full_data': alert
            })

    print("=" * 70 + "\n")

    return jsonify({"status": "success", "received": len(data.get('alerts', []))}), 200

@app.route('/alerts/history', methods=['GET'])
def get_history():
    """Voir l'historique des alertes reçues"""
    return jsonify({
        "total": len(alerts_received),
        "alerts": alerts_received
    }), 200

@app.route('/alerts/clear', methods=['POST'])
def clear_history():
    """Effacer l'historique"""
    global alerts_received
    count = len(alerts_received)
    alerts_received = []
    return jsonify({"status": "success", "cleared": count}), 200

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({"status": "healthy", "alerts_count": len(alerts_received)}), 200

@app.route('/', methods=['GET'])
def index():
    """Page d'accueil"""
    return f"""
    <html>
    <head>
        <title>Webhook Receiver</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            h1 {{ color: #333; }}
            .stats {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
            .alert {{ background: #fff; border-left: 4px solid #ff6b6b; padding: 10px; margin: 10px 0; }}
        </style>
    </head>
    <body>
        <h1>AlertManager Webhook Receiver</h1>
        <div class="stats">
            <p><strong>Status:</strong> Running</p>
            <p><strong>Total Alerts Received:</strong> {len(alerts_received)}</p>
        </div>
        <h2>Endpoints:</h2>
        <ul>
            <li>POST /alerts/critical - Receive critical alerts</li>
            <li>POST /alerts/warning - Receive warning alerts</li>
            <li>GET /alerts/history - View alert history</li>
            <li>POST /alerts/clear - Clear history</li>
        </ul>
    </body>
    </html>
    """

if __name__ == '__main__':
    print("=" * 70)
    print("WEBHOOK RECEIVER STARTING".center(70))
    print("=" * 70)
    print("Listening on: http://localhost:5001")
    print("Critical alerts: http://localhost:5001/alerts/critical")
    print("Warning alerts:  http://localhost:5001/alerts/warning")
    print("=" * 70)
    print("")

    app.run(host='0.0.0.0', port=5001, debug=False)
