import http.server
import socketserver
import json
import os
import urllib.request
import urllib.error
import urllib.parse
import logging
import sqlite3
import uuid
import time
from functools import lru_cache
from typing import Dict, Any, Optional

# Configure structured logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("OdysseyServer")

def load_env() -> None:
    try:
        with open(".env", "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip()
    except FileNotFoundError:
        pass

load_env()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# 1. Database Initialization (SQLite)
def init_db():
    """Initializes the SQLite database for persistent, shareable trips."""
    conn = sqlite3.connect('odyssey.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS trips
                 (id TEXT PRIMARY KEY, destination TEXT, data TEXT)''')
    conn.commit()
    conn.close()

init_db()

# 2. Live Environmental Data (Weather)
def get_weather(destination: str) -> Optional[Dict[str, Any]]:
    """Fetches real-time weather data using free open-meteo APIs."""
    try:
        first_city = destination.split(',')[0].split(' to ')[0].strip()
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(first_city)}&count=1"
        geo_req = urllib.request.Request(geo_url, headers={'User-Agent': 'Odyssey'})
        with urllib.request.urlopen(geo_req, timeout=5) as response:
            geo_data = json.loads(response.read().decode('utf-8'))
            if not geo_data.get('results'):
                return None
            lat, lon = geo_data['results'][0]['latitude'], geo_data['results'][0]['longitude']
            
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        w_req = urllib.request.Request(weather_url, headers={'User-Agent': 'Odyssey'})
        with urllib.request.urlopen(w_req, timeout=5) as w_response:
            w_data = json.loads(w_response.read().decode('utf-8'))
            return w_data.get('current_weather')
    except Exception as e:
        logger.error(f"Weather API error: {e}")
        return None

# 3. AI Routing Engine
@lru_cache(maxsize=128)
def call_gemini_api(prompt: str) -> Dict[str, Any]:
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        raise ValueError("Please add your Gemini API Key to the .env file.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {
            "parts": [{"text": "You are Odyssey, an elite travel engineer. Return ONLY valid JSON with no markdown. Ensure every activity includes a 'google_maps_search_url'. You map out elegant multi-city routing and transit logistics."}]
        },
        "generationConfig": {"temperature": 0.7}
    }).encode('utf-8')
    
    req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'}, method='POST')
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                ai_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
                
                if ai_text.startswith("```json"): ai_text = ai_text[7:]
                elif ai_text.startswith("```"): ai_text = ai_text[3:]
                if ai_text.endswith("```"): ai_text = ai_text[:-3]
                
                return json.loads(ai_text.strip())
        except urllib.error.HTTPError as e:
            if e.code in [503, 429] and attempt < max_retries - 1:
                logger.warning(f"Google Gemini overloaded (HTTP {e.code}). Retrying in {2**attempt}s...")
                time.sleep(2**attempt)
                continue
            logger.error(f"Gemini API Error: {str(e)}")
            raise RuntimeError(f"Google AI is currently overloaded (HTTP {e.code}). Please try again in a moment.")
        except urllib.error.URLError as e:
            logger.error(f"Gemini API Error: {str(e)}")
            raise RuntimeError(f"Network error while reaching Google AI: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON Parse Error: {str(e)}")
            raise RuntimeError("Received malformed JSON from Gemini API.")

class OdysseyHandler(http.server.SimpleHTTPRequestHandler):
    
    def send_security_headers(self) -> None:
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'SAMEORIGIN')
        self.send_header('X-XSS-Protection', '1; mode=block')
        self.send_header('Content-Security-Policy', "default-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://fonts.gstatic.com https://unpkg.com https://geocoding-api.open-meteo.com https://api.open-meteo.com https://maps.google.com;")

    def end_headers(self) -> None:
        self.send_security_headers()
        super().end_headers()

    def do_GET(self) -> None:
        """(Security) Strict routing to prevent Path Traversal and Sensitive File Exposure."""
        if self.path.startswith('/api/v1/trip/'):
            trip_id = self.path.split('/')[-1]
            conn = sqlite3.connect('odyssey.db')
            c = conn.cursor()
            c.execute("SELECT data FROM trips WHERE id=?", (trip_id,))
            row = c.fetchone()
            conn.close()
            
            if row:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(row[0].encode('utf-8'))
            else:
                self._send_error_response(404, "Trip not found in database.")
        elif self.path == '/' or self.path == '/index.html':
            self.path = '/index.html'
            super().do_GET()
        else:
            self.send_error(403, "Forbidden: Access is denied.")

    def do_POST(self) -> None:
        if self.path == '/api/v1/plan':
            self._handle_plan_route()
        else:
            self.send_error(404, "Endpoint not found")

    def _handle_plan_route(self) -> None:
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 10240:  
                raise ValueError("Payload too large. Request rejected for security.")
                
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            
            dest = str(data.get('destination', '')).strip()[:200]
            days = min(max(int(data.get('days', 3)), 1), 30)
            budget = str(data.get('budget', 'Moderate')).strip()[:20]
            interests = str(data.get('interests', '')).strip()[:500]
            travelers = min(max(int(data.get('travelers', 2)), 1), 20)
            
            if not dest:
                raise ValueError("Destination is strictly required.")

            prompt = f"""Create a detailed {days}-day travel itinerary for {travelers} traveler(s) visiting {dest}.
Important: If "{dest}" contains multiple cities (e.g. Rome to Paris), you MUST map out the logistics and routing between them efficiently within the {days} days.
Budget: {budget}. Interests: {interests}.
Return ONLY JSON with this structure:
{{
  "title": "String", "summary": "String", "destination": "{dest}", "total_days": {days},
  "budget_level": "{budget}", "estimated_total_cost": "String", "best_time_to_visit": "String",
  "local_tips": ["String"],
  "transit_logic": "String (explain the overarching transit/routing plan)",
  "itinerary": [
    {{
      "day": 1, "theme": "String", "city": "String (current city)",
      "activities": [
        {{ "time": "String", "title": "String", "description": "String", "estimated_cost": "String", "location": "String", "google_maps_search_url": "https://www.google.com/maps/search/?api=1&query=..." }}
      ]
    }}
  ]
}}"""
            logger.info(f"Generating itinerary for {dest} ({days} days)")
            
            weather = get_weather(dest)
            result_data = call_gemini_api(prompt)
            
            if weather:
                result_data['current_weather'] = weather

            trip_id = str(uuid.uuid4())[:8]
            result_data['shareable_id'] = trip_id
            
            conn = sqlite3.connect('odyssey.db')
            c = conn.cursor()
            c.execute("INSERT INTO trips (id, destination, data) VALUES (?, ?, ?)", 
                      (trip_id, dest, json.dumps(result_data)))
            conn.commit()
            conn.close()

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result_data).encode('utf-8'))
            
        except ValueError as e:
            logger.warning(f"Validation Error: {str(e)}")
            self._send_error_response(400, str(e))
        except Exception as e:
            logger.error(f"Server Error: {str(e)}")
            self._send_error_response(500, str(e))

    def _send_error_response(self, code: int, message: str) -> None:
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"detail": message}).encode('utf-8'))

if __name__ == "__main__":
    import sys
    PORT = int(os.environ.get("PORT", 8005))
    try:
        with socketserver.TCPServer(("", PORT), OdysseyHandler) as httpd:
            logger.info(f"Odyssey Enterprise Server listening on port {PORT}")
            print(f"=================================================")
            print(f" Odyssey Engine is ALIVE! Open: http://localhost:{PORT}")
            print(f"=================================================")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n=================================================")
        print(" Odyssey Server gracefully shut down. Goodbye!")
        print("=================================================")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server crashed: {e}")
        sys.exit(1)
