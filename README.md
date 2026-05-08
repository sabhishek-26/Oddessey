# Odyssey - Intelligent Travel Design

Odyssey is an ultra-lightweight, zero-dependency travel planning engine powered by Google Gemini AI. It instantly generates personalized, hyper-detailed travel itineraries based on your specific constraints, budget, and destination.

## ✨ Key Features

*   **Lightning Fast Engine:** Utilizes an in-memory LRU Cache to instantly serve repeated or similar itinerary requests without incurring extra API latency.
*   **Deep Google Integration:** Powered by the Google Gemini REST API for generative planning, with intelligent prompt engineering that automatically deep-links every generated activity directly into Google Maps.
*   **Zero-Dependency Architecture:** Requires absolutely no external packages (`npm` or `pip`). It runs entirely on the native Python 3 Standard Library and Vanilla JavaScript.
*   **Fortified Security:** Built with robust input sanitization, strict payload size limitations to prevent memory exhaustion, and comprehensive Web Security Headers (CSP, HSTS, X-Frame-Options, XSS-Protection).
*   **Accessible UI:** A beautiful, responsive glassmorphism frontend that is fully ARIA-compliant. Features dynamic screen-reader narrations (`aria-live`), high-contrast keyboard navigation focus rings, and semantic HTML5 structuring.

## 🚀 How to Run

Since the application relies on zero external dependencies, getting it running takes less than a minute.

1. Ensure your `.env` file in the root directory contains your Google Gemini API key:
   ```env
   GEMINI_API_KEY=your_actual_key_here
   ```
2. Start the local server using Python:
   ```bash
   python server.py
   ```
3. Open your web browser and navigate to:
   **http://localhost:8000**

## ☁️ Google Cloud Run Deployment

Odyssey is fully configured for seamless, automated deployment to Google Cloud Run.

1. **Link Repository**: Go to Google Cloud Run, click **Create Service**, and select "Continuously deploy from a repository".
2. **Set Secrets**: Under the "Container, Connections, Security" menu, navigate to the **Variables & Secrets** tab. Add a new variable:
   * **Name**: `GEMINI_API_KEY`
   * **Value**: Your actual API key.
3. **Deploy**: Cloud Run will automatically read the included `Procfile` and `requirements.txt` to instantly build and deploy the Zero-Dependency engine.

## 📂 Project Structure

```text
/
├── server.py        # Core Python backend, secure API routing, and AI integration
├── index.html       # Vanilla JS/HTML/CSS frontend with dynamic rendering
├── test_server.py   # Automated test suite using Python's unittest
├── .env             # Environment variables (API Keys)
└── README.md        # Project documentation
```

## 🧪 Running Tests

The application includes a comprehensive testing suite that safely mocks API requests and verifies security/payload limitations locally.

To run the tests, execute the following in your terminal:
```bash
python -m unittest test_server.py
```