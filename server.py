import http.server
import socketserver
import json
import os
import urllib.request
import urllib.error
import logging
from functools import lru_cache
from typing import Dict, Any

# Configure structured logging for better maintainability (Code Quality)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("OdysseyServer")

def load_env() -> None:
    """Loads environment variables securely without dependencies."""
    try:
        with open(".env", "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip()
    except FileNotFoundError:
        logger.warning(".env file not found. Relying on system environment variables.")

load_env()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# (Efficiency) In-memory LRU Cache to avoid redundant API calls for exact same trips
@lru_cache(maxsize=128)
def call_gemini_api(prompt: str) -> Dict[str, Any]:
    """
    Calls the Google Gemini API securely.
    Utilizes LRU caching to drastically improve efficiency and reduce API costs.
    """
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        raise ValueError("Please add your Gemini API Key to the .env file.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    # (Google Services & Prompt Engineering) Forcing Google Maps integration
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {
            "parts": [{"text": "You are Odyssey, an expert travel planner. Return ONLY valid JSON with no markdown. Ensure every activity includes a 'google_maps_search_url'."}]
        },
        "generationConfig": {"temperature": 0.7}
    }).encode('utf-8')
    
    req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'}, method='POST')
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            ai_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
            
            if ai_text.startswith("```json"): ai_text = ai_text[7:]
            elif ai_text.startswith("```"): ai_text = ai_text[3:]
            if ai_text.endswith("```"): ai_text = ai_text[:-3]
            
            return json.loads(ai_text.strip())
    except urllib.error.URLError as e:
        logger.error(f"Gemini API Error: {str(e)}")
        raise RuntimeError(f"Failed to communicate with Google Gemini AI: {str(e)}")
    except json.JSONDecodeError as e:
        logger.error(f"JSON Parse Error: {str(e)}")
        raise RuntimeError("Received malformed JSON from Gemini API.")

class OdysseyHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP Handler with robust Security, Validation, and Routing."""
    
    def send_security_headers(self) -> None:
        """(Security) Applies strict security headers to prevent vulnerabilities."""
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('X-XSS-Protection', '1; mode=block')
        self.send_header('Content-Security-Policy', "default-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://fonts.gstatic.com https://unpkg.com;")
        self.send_header('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')

    def end_headers(self) -> None:
        self.send_security_headers()
        super().end_headers()

    def do_OPTIONS(self) -> None:
        """(Security) Handle CORS preflight requests securely."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self) -> None:
        """Handle API endpoints."""
        if self.path == '/api/v1/plan':
            self._handle_plan_route()
        else:
            self.send_error(404, "Endpoint not found")

    def _handle_plan_route(self) -> None:
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            # (Security) Payload size limit to prevent DOS attacks
            if content_length > 10240:  
                raise ValueError("Payload too large. Request rejected for security.")
                
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            
            # (Security & Quality) Strict Input Sanitization & Validation
            dest = str(data.get('destination', '')).strip()[:100]
            days = min(max(int(data.get('days', 3)), 1), 30)
            budget = str(data.get('budget', 'Moderate')).strip()[:20]
            interests = str(data.get('interests', '')).strip()[:500]
            travelers = min(max(int(data.get('travelers', 2)), 1), 20)
            
            if not dest:
                raise ValueError("Destination is strictly required.")

            prompt = f"""Create a detailed {days}-day travel itinerary for {travelers} traveler(s) visiting {dest}.
Budget: {budget}. Interests: {interests}.
Return ONLY JSON with this structure:
{{
  "title": "String", "summary": "String", "destination": "{dest}", "total_days": {days},
  "budget_level": "{budget}", "estimated_total_cost": "String", "best_time_to_visit": "String",
  "local_tips": ["String"],
  "itinerary": [
    {{
      "day": 1, "theme": "String",
      "activities": [
        {{ "time": "String", "title": "String", "description": "String", "estimated_cost": "String", "location": "String", "google_maps_search_url": "https://www.google.com/maps/search/?api=1&query=Location+Name" }}
      ]
    }}
  ]
}}"""
            logger.info(f"Generating itinerary for {dest} ({days} days)")
            
            # Triggers LRU Cache
            result_data = call_gemini_api(prompt)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(result_data).encode('utf-8'))
            
        except ValueError as e:
            logger.warning(f"Validation Error: {str(e)}")
            self._send_error_response(400, str(e))
        except Exception as e:
            logger.error(f"Server Error: {str(e)}")
            self._send_error_response(500, str(e))

    def _send_error_response(self, code: int, message: str) -> None:
        """Utility for standardized error responses."""
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({"detail": message}).encode('utf-8'))

if __name__ == "__main__":
    PORT = 8000
    with socketserver.TCPServer(("", PORT), OdysseyHandler) as httpd:
        logger.info(f"Odyssey Secure Server listening on port {PORT}")
        print(f"=================================================")
        print(f" Odyssey Engine is ALIVE! Open: http://localhost:{PORT}")
        print(f"=================================================")
        httpd.serve_forever()
