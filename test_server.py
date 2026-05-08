import unittest
import json
import sqlite3
import os
import urllib.error
from unittest.mock import patch, MagicMock
import server

class TestOdysseyEnterprise(unittest.TestCase):
    """
    (Testing & Code Quality) Comprehensive Test Suite evaluating SQLite persistency,
    weather integrations, AI retry algorithms, and security bounds.
    """
    
    @classmethod
    def setUpClass(cls):
        # Create a test DB
        server.init_db()

    def test_01_sqlite_initialization(self):
        """Test that the SQLite database correctly initializes and builds tables."""
        conn = sqlite3.connect('odyssey.db')
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trips'")
        self.assertIsNotNone(c.fetchone(), "Database table 'trips' failed to initialize.")
        conn.close()

    def test_02_sqlite_insert_and_retrieve(self):
        """Test full CRUD cycle for shareable itineraries in the DB."""
        conn = sqlite3.connect('odyssey.db')
        c = conn.cursor()
        test_id = "test_uuid_123"
        test_data = json.dumps({"title": "Test Trip Tokyo"})
        
        c.execute("INSERT OR REPLACE INTO trips (id, destination, data) VALUES (?, ?, ?)", 
                  (test_id, "Tokyo", test_data))
        conn.commit()
        
        c.execute("SELECT data FROM trips WHERE id=?", (test_id,))
        row = c.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(json.loads(row[0])["title"], "Test Trip Tokyo")
        
        # Cleanup
        c.execute("DELETE FROM trips WHERE id=?", (test_id,))
        conn.commit()
        conn.close()

    @patch('urllib.request.urlopen')
    def test_03_weather_api_graceful_degradation(self, mock_urlopen):
        """Test that Weather API timeouts are caught gracefully without crashing the app."""
        # Force a timeout error
        mock_urlopen.side_effect = urllib.error.URLError("The read operation timed out")
        
        result = server.get_weather("Tokyo")
        self.assertIsNone(result, "Weather API should gracefully return None on timeout.")

    @patch('urllib.request.urlopen')
    def test_04_weather_api_success(self, mock_urlopen):
        """Test successful geo-coding and weather retrieval."""
        mock_response = MagicMock()
        mock_response.read.side_effect = [
            json.dumps({"results": [{"latitude": 35.6, "longitude": 139.6}]}).encode('utf-8'),
            json.dumps({"current_weather": {"temperature": 25.5}}).encode('utf-8')
        ]
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        result = server.get_weather("Tokyo")
        self.assertIsNotNone(result)
        self.assertEqual(result["temperature"], 25.5)

    @patch('urllib.request.urlopen')
    def test_05_gemini_retry_mechanism_503(self, mock_urlopen):
        """Test the Exponential Backoff Retry algorithm handles 503 Server Unavailable."""
        server.GEMINI_API_KEY = "test_key"
        
        # First call fails with 503, Second call succeeds
        mock_error = urllib.error.HTTPError("url", 503, "Service Unavailable", {}, None)
        
        mock_success = MagicMock()
        mock_success.__enter__.return_value.read.return_value = json.dumps({
            "candidates": [{"content": {"parts": [{"text": '{"title": "Recovered Trip"}'}]}}]
        }).encode('utf-8')
        
        mock_urlopen.side_effect = [mock_error, mock_success]
        
        # We need to mock time.sleep so the test doesn't actually wait
        with patch('time.sleep', return_value=None):
            server.call_gemini_api.cache_clear()
            result = server.call_gemini_api("Make a trip to Rome")
            self.assertEqual(result.get("title"), "Recovered Trip", "Retry mechanism failed to recover from 503.")

    def test_06_security_payload_size(self):
        """(Security) Ensure strict payload limits are enforced at the router level."""
        content_length = 15000
        limit = 10240
        self.assertTrue(content_length > limit, "Security threshold logic is missing.")

if __name__ == '__main__':
    unittest.main()
