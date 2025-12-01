from flask import Flask, render_template, request
from app.coordinator import generate_briefing
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for
from app.memory.memory_bank import load_memory, update_preferences
from app.coordinator import generate_briefing

app = Flask(__name__, template_folder="templates", static_folder="static")

CATEGORIES = ["tech", "business", "sports", "health", "world"]

@app.template_filter('datetimeformat')
def datetimeformat(value):
    try:
        return datetime.fromtimestamp(float(value)).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(value)

@app.route("/")
def index():
    return render_template("index.html", categories=CATEGORIES)

@app.route("/feed")
def feed():
    category = request.args.get("category", "tech")
    briefing = generate_briefing(category=category)
    return render_template("feed.html", category=category, briefing=briefing)

if __name__ == "__main__":
    app.run(debug=True)
