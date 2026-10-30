# TrafficGPT

A beginner-friendly Flask chatbot starter project with:
- Gemini-powered answers to general questions
- WeatherAPI current weather lookup
- TomTom route and traffic-aware travel-time estimates

## Setup (Windows)

1. Install Python and Visual Studio Code.
2. Open this folder in VS Code.
3. Open the terminal and run:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

4. Copy `.env.example` and rename the copy to `.env`.
5. Add your own API keys in `.env`:
   - `GEMINI_API_KEY`
   - `WEATHER_API_KEY`
   - `TOMTOM_API_KEY`
6. Start the app:

```bash
python app.py
```

7. Open http://127.0.0.1:5000 in your browser.

## Example questions

- What is the weather in Kakinada?
- What is the traffic from Kakinada to Rajahmundry?
- Explain artificial intelligence.

## Important

Live weather and route information require working API keys and internet access.
Traffic results are estimates from the routing service, not guaranteed predictions.
Without `TOMTOM_API_KEY`, the Kakinada-to-Rajahmundry question returns a clearly
labeled sample estimate; it is illustrative and does not reflect current traffic.
Do not upload `.env` or share your API keys. `.gitignore` excludes `.env`.

This starter currently routes weather and traffic questions using simple keywords.
A later version can add more flexible intent detection, chat memory, alternative routes,
and deployment.
