from flask import Flask, render_template, request, redirect, jsonify
from pymongo import MongoClient
from datetime import datetime, timezone
import random
import string

# Flask Configuration
app = Flask(__name__)

# MongoDB Connection
MONGO_URI = "mongodb://localhost:27017"
client = MongoClient(MONGO_URI)
db = client.url_shortener
collection = db.urls

# Ensure unique index on short_url field
collection.create_index("short_url", unique=True)

# Generate Unique Short URL
def generate_short_url(length=6):
    """Generate a unique short URL"""
    characters = string.ascii_letters + string.digits
    while True:
        short_url = ''.join(random.choice(characters) for _ in range(length))
        try:
            collection.insert_one({"short_url": short_url})  # Temporary insert check
            collection.delete_one({"short_url": short_url})  # Remove test entry
            return short_url
        except:
            continue  # Retry if short URL already exists

@app.route('/urls', methods=['GET'])
def get_all_urls():
    """Fetch all stored URLs"""
    urls = list(collection.find({}, {"_id": 0}))  # Exclude MongoDB ID
    return jsonify(urls), 200

@app.route('/')
def index():
    """Render the main webpage"""
    return render_template('index.html')

@app.route('/shorten', methods=['POST'])
def shorten_url():
    """Create a short URL"""
    long_url = request.json.get("longUrl")
    if not long_url:
        return jsonify({"error": "Missing URL"}), 400

    existing_entry = collection.find_one({"long_url": long_url})
    if existing_entry:
        return jsonify({"short_url": f"http://localhost:5000/{existing_entry['short_url']}"})

    short_url = generate_short_url()
    entry = {
        "short_url": short_url,
        "long_url": long_url,
        "clicks": 0,
        "creation_date": datetime.now(timezone.utc),
        "is_active": True
    }
    
    collection.insert_one(entry)

    return jsonify({"short_url": f"http://localhost:5000/{short_url}"}), 201

@app.route('/<short_url>')
def redirect_url(short_url):
    """Redirect to the original URL"""
    url_entry = collection.find_one({"short_url": short_url})

    if not url_entry:
        return jsonify({"error": "URL not found"}), 404

    if not url_entry["is_active"]:
        return jsonify({"error": "URL is inactive"}), 410

    # Increment Click Count
    collection.update_one({"short_url": short_url}, {"$inc": {"clicks": 1}})

    return redirect(url_entry["long_url"], 301)

if __name__ == '__main__':
    app.run(debug=True)
