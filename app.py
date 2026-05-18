from flask import Flask, jsonify, render_template
from apscheduler.schedulers.background import BackgroundScheduler
from scraper import scrape_all
import json
import os
import atexit

app = Flask(__name__)

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scores.json')

def load_scores():
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, 'r') as f:
            return json.load(f)
    return {}

# ---- Run scraper on startup ----
print("Running initial scrape...")
scrape_all()

# ---- Schedule scraper every 2 minutes ----
scheduler = BackgroundScheduler()
scheduler.add_job(func=scrape_all, trigger="interval", minutes=2)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

# ---- Routes ----
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/scores')
def scores():
    data = load_scores()
    return jsonify(data)

@app.route('/api/scores/<conference>')
def conference_scores(conference):
    data = load_scores()
    if conference in data:
        return jsonify(data[conference])
    return jsonify({'error': 'Conference not found'}), 404

@app.route('/api/debug/<conference>')
def debug(conference):
    data = load_scores()
    if conference in data:
        debug_lines = data[conference].get('debug', [])
        return '<br>'.join(debug_lines)
    return 'Conference not found', 404

if __name__ == '__main__':
    app.run(debug=True)
