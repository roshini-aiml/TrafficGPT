import os
import re
import requests
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from google import genai

load_dotenv()
app = Flask(__name__)

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WEATHER_KEY = os.getenv("WEATHER_API_KEY")
TOMTOM_KEY = os.getenv("TOMTOM_API_KEY")

ai_client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None


def get_weather(location):
    if not WEATHER_KEY:
        return "Weather API key is missing. Add WEATHER_API_KEY to your .env file."
    try:
        response = requests.get(
            "https://api.weatherapi.com/v1/current.json",
            params={"key": WEATHER_KEY, "q": location},
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        current, place = data["current"], data["location"]
        return (
            f"Weather in {place['name']}, {place['country']}:\n"
            f"Temperature: {current['temp_c']}°C\n"
            f"Condition: {current['condition']['text']}\n"
            f"Feels like: {current['feelslike_c']}°C\n"
            f"Humidity: {current['humidity']}%\n"
            f"Wind: {current['wind_kph']} km/h\n"
            f"Last updated: {current['last_updated']}"
        )
    except requests.RequestException:
        return "Unable to retrieve weather information right now. Check the location and API key."
    except (KeyError, ValueError):
        return "Weather information could not be processed."


def get_traffic(source, destination):
    if not TOMTOM_KEY:
        def normalize(place):
            return re.sub(r"[^a-z]", "", place.lower())

        source_name, destination_name = normalize(source), normalize(destination)
        if source_name in {"kakinada", "kakinda"} and destination_name in {
            "rajahmundry", "rajundary", "rajamundry"
        }:
            return (
                "Sample traffic estimate (not live data)\n"
                "Route: Kakinada to Rajahmundry\n"
                "Distance: about 65 km\n"
                "Estimated travel time: about 1 hour 30 minutes\n"
                "Typical travel time without heavy traffic: about 1 hour 15 minutes\n"
                "Sample traffic delay: about 15 minutes\n"
                "This is illustrative sample data, not a live prediction. "
                "Add TOMTOM_API_KEY to your .env file for live estimates."
            )
        return "Live traffic is not configured yet. Add TOMTOM_API_KEY to your .env file."
    try:
        def geocode(place):
            url = f"https://api.tomtom.com/search/2/geocode/{requests.utils.quote(place)}.json"
            response = requests.get(url, params={"key": TOMTOM_KEY}, timeout=15)
            response.raise_for_status()
            results = response.json().get("results", [])
            if not results:
                raise ValueError("Location not found")
            return results[0]["position"]

        start, end = geocode(source), geocode(destination)
        route_url = (
            "https://api.tomtom.com/routing/1/calculateRoute/"
            f"{start['lat']},{start['lon']}:{end['lat']},{end['lon']}/json"
        )
        response = requests.get(
            route_url,
            params={"key": TOMTOM_KEY, "traffic": "true", "routeType": "fastest"},
            timeout=20
        )
        response.raise_for_status()
        summary = response.json()["routes"][0]["summary"]
        minutes = round(summary["travelTimeInSeconds"] / 60)
        normal = round(summary["noTrafficTravelTimeInSeconds"] / 60)
        distance = round(summary["lengthInMeters"] / 1000, 1)
        delay = max(0, minutes - normal)
        return (
            f"Route: {source} to {destination}\n"
            f"Distance: {distance} km\n"
            f"Estimated travel time with traffic: {minutes} minutes\n"
            f"Normal travel time: {normal} minutes\n"
            f"Estimated traffic delay: {delay} minutes\n"
            "Note: These are API estimates, not a guarantee."
        )
    except (requests.RequestException, KeyError, ValueError, IndexError):
        return "Unable to retrieve route information. Check the locations and API key."


def get_ai_answer(question):
    if not ai_client:
        return "AI API key is missing. Add GEMINI_API_KEY to your .env file."
    try:
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=(
                "You are TrafficGPT, a helpful AI assistant. Answer general questions "
                "clearly and simply. Do not invent live weather or traffic data. "
                "For live information, explain that the relevant live-data feature "
                "must be used.\n\nUser question: " + question
            )
        )
        return response.text or "I couldn't generate an answer. Please try again."
    except Exception:
        return "AI service is temporarily unavailable. Check your Gemini API key and try again."


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    question = str(data.get("message", "")).strip()
    if not question:
        return jsonify({"reply": "Please enter a question."}), 400
    if len(question) > 1000:
        return jsonify({"reply": "Please keep your question under 1000 characters."}), 400

    lower = question.lower()
    weather_words = ["weather", "temperature", "rain", "climate"]
    traffic_words = ["traffic", "route", "travel time", "distance"]

    if any(word in lower for word in weather_words):
        match = re.search(r"\b(?:in|at|of|for)\s+(.+?)[?.!]*$", question, re.I)
        reply = get_weather(match.group(1).strip()) if match else (
            "Which city would you like to check the weather for?"
        )
    elif any(word in lower for word in traffic_words):
        match = re.search(r"\bfrom\s+(.+?)\s+to\s+(.+?)[?.!]*$", question, re.I)
        reply = get_traffic(match.group(1).strip(), match.group(2).strip()) if match else (
            "Please ask like: What is the traffic from Kakinada to Rajahmundry?"
        )
    else:
        reply = get_ai_answer(question)

    return jsonify({"reply": reply})


if __name__ == "__main__":
    app.run(debug=True)
