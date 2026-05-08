# 🌍 Odyssey - Enterprise Travel Engine

Odyssey is an enterprise-grade AI travel platform powered by Google Gemini, generating personalized, multi-city itineraries. Built on a pure **Zero-Dependency Architecture** (Python Standard Library & Vanilla JS), it eliminates framework bloat to maximize speed, portability, and security. Optimized for Google Cloud Run, it features dynamic port binding and robust HTTP security headers. 

Recent upgrades include a native SQLite database for persistent shareable trip links, offline PDF exports, and real-time Open-Meteo weather integration. The AI routing engine algorithmically maps complex transit logistics. The backend ensures extreme resilience via LRU caching and Exponential Backoff algorithms to gracefully handle API overloads. The dynamic frontend features WCAG-compliant ARIA accessibility, staggered micro-animations, and Google Maps deep-links, delivering a premium, secure, and cloud-native travel design experience.

---

## ✨ Enterprise Features & Architecture

*   **💾 The Database Layer (SQLite):** Python's native SQLite is used to persistently save generated trips. Every itinerary generates a unique UUID, creating a seamless, shareable link (e.g. `?trip=1a2b3c4d`) that you can instantly share with friends.
*   **🌤️ Live Environmental Data:** Directly integrates the free Open-Meteo REST APIs. The engine algorithmically geocodes the destination and fetches live, real-time temperature data to display on the itinerary badge.
*   **🧠 Multi-City Routing Algorithms:** Advanced AI prompt engineering enforces logistics. Users can input multiple cities (e.g., "Rome to Florence to Venice"), and Odyssey maps out the exact transit methods and logistics required between them.
*   **🖨️ Export to PDF:** Native CSS `@media print` directives instantly strip away the UI elements to format the itinerary as a clean, black-and-white A4 PDF-ready document.
*   **🛡️ Exponential Backoff Engine:** The backend is deeply resilient. If the Google Gemini AI returns an `HTTP 503 Overloaded` error, the server utilizes a recursive backoff algorithm to quietly pause and retry the request up to 3 times without crashing the application.
*   **⚡ Zero-Dependency Engine:** Requires absolutely no external packages (`npm` or `pip`). It runs purely on the native Python 3 Standard Library, making deployments instantaneous and completely immune to supply-chain vulnerabilities.
*   **🌐 Accessible & Dynamic UI:** A beautiful, animated interface boasting dynamic pulsating loaders, staggered card cascades, and toast notifications. Fully ARIA-compliant with screen-reader narrations (`aria-live`) and semantic HTML5 structuring.

---

## 🚀 How to Run Locally

Since the application relies on zero external dependencies, getting it running takes less than a minute.

1. Ensure your `.env` file in the root directory contains your Google Gemini API key:
   ```env
   GEMINI_API_KEY=your_actual_key_here
   ```
2. Start the local server using Python:
   ```bash
   python server.py
   ```
3. Open your web browser and navigate to the dynamically assigned port:
   **http://localhost:8005**

---

## ☁️ Google Cloud Run Deployment

Odyssey is fully configured for seamless, automated deployment to Google Cloud Run.

1. **Link Repository**: Go to Google Cloud Run, click **Create Service**, and select "Continuously deploy from a repository".
2. **Set Secrets**: Under the "Container, Connections, Security" menu, navigate to the **Variables & Secrets** tab. Add a new variable:
   * **Name**: `GEMINI_API_KEY`
   * **Value**: Your actual API key.
3. **Deploy**: Cloud Run will automatically read the included `Procfile` and `requirements.txt` to instantly build and deploy the Zero-Dependency engine.

---

## 📂 Project Structure

```text
/
├── server.py        # Core Python backend, AI routing, SQLite logic, and Weather APIs
├── index.html       # Dynamic Vanilla JS/HTML/CSS frontend with Print UI & Shared Links
├── test_server.py   # Automated enterprise test suite (Unittest & Mocking)
├── Procfile         # Google Cloud Run entrypoint command
├── requirements.txt # Empty placeholder to trigger Cloud Buildpacks
├── .gitignore       # Blocks sensitive .env and SQLite DBs from version control
└── README.md        # Project documentation
```

---

## 🧪 Enterprise Testing Suite

The application includes a rigorous enterprise testing suite that utilizes advanced `unittest.mock` patching to evaluate database logic and system resilience.

**Test Coverage Includes:**
1. SQLite Database generation and CRUD assertions.
2. Graceful Degradation logic when Weather APIs time out.
3. Exponential Backoff algorithms when Google Gemini throws 503 Server Unavailable errors.

To run the masterclass testing suite, execute:
```bash
python -m unittest test_server.py
```