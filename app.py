import gradio as gr
import pandas as pd
import numpy as np
import os
import urllib.request
import zipfile
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ========================================
# TRAFFICGPT: LOAD DATASET
# ========================================

def load_dataset():
    url = (
        "https://archive.ics.uci.edu/static/public/"
        "492/metro+interstate+traffic+volume.zip"
    )

    zip_path = "/tmp/traffic_dataset.zip"
    folder = "/tmp/traffic_dataset"

    os.makedirs(folder, exist_ok=True)

    urllib.request.urlretrieve(url, zip_path)

    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(folder)

    csv_files = [
        os.path.join(root, f)
        for root, _, files in os.walk(folder)
        for f in files
        if f.lower().endswith(".csv")
    ]

    if not csv_files:
        raise RuntimeError("Dataset CSV file was not found.")

    return pd.read_csv(csv_files[0])


# ========================================
# TRAIN MACHINE LEARNING MODEL
# ========================================

df = load_dataset()

df["date_time"] = pd.to_datetime(
    df["date_time"], errors="coerce"
)

df = df.dropna(
    subset=["date_time", "traffic_volume"]
).copy()

df["hour"] = df["date_time"].dt.hour
df["day_of_week"] = df["date_time"].dt.dayofweek
df["month"] = df["date_time"].dt.month
df["is_weekend"] = (
    df["day_of_week"] >= 5
).astype(int)

numeric_features = [
    "hour",
    "day_of_week",
    "month",
    "is_weekend",
    "temp",
    "rain_1h",
    "snow_1h",
    "clouds_all"
]

categorical_features = ["weather_main"]

features = numeric_features + categorical_features

df = df.dropna(
    subset=features + ["traffic_volume"]
).sort_values("date_time")

preprocessor = ColumnTransformer([
    (
        "numbers",
        "passthrough",
        numeric_features
    ),
    (
        "weather",
        OneHotEncoder(handle_unknown="ignore"),
        categorical_features
    )
])

model = Pipeline([
    ("preprocessor", preprocessor),
    (
        "regressor",
        RandomForestRegressor(
            n_estimators=50,
            random_state=42,
            min_samples_leaf=2,
            n_jobs=-1
        )
    )
])

model.fit(df[features], df["traffic_volume"])


# ========================================
# TRAFFIC PREDICTION FUNCTION
# ========================================

def predict_traffic(hour=17, weather="Clear"):

    hour = max(0, min(23, int(hour)))

    weather_map = {
        "clear": "Clear",
        "rain": "Rain",
        "drizzle": "Drizzle",
        "clouds": "Clouds",
        "cloudy": "Clouds",
        "snow": "Snow",
        "mist": "Mist",
        "fog": "Fog"
    }

    weather_name = weather_map.get(
        weather.lower(), weather.title()
    )

    sample = pd.DataFrame([{
        "hour": hour,
        "day_of_week": 2,
        "month": 10,
        "is_weekend": 0,
        "temp": 288.0,
        "rain_1h": (
            1.0
            if weather_name in ["Rain", "Drizzle"]
            else 0.0
        ),
        "snow_1h": 0.0,
        "clouds_all": (
            80
            if weather_name in ["Clouds", "Rain"]
            else 20
        ),
        "weather_main": weather_name
    }])

    volume = max(
        0,
        round(float(model.predict(sample)[0]))
    )

    if volume < 1500:
        level = "Low"
    elif volume < 4000:
        level = "Moderate"
    else:
        level = "High"

    return {
        "predicted_vehicles_per_hour": volume,
        "traffic_level": level
    }


# ========================================
# RAG KNOWLEDGE BASE
# ========================================

road_documents = [
    "Compare routes using estimated travel time, distance, road conditions and verified closures. The shortest route is not always the fastest.",
    "Traffic changes with time of day, weekdays, weather and local events. Historical data cannot guarantee current traffic conditions.",
    "Rain can affect visibility and road grip. Check official weather and road advisories before travelling.",
    "Traffic volume is not the same as travel time. To identify the fastest route, compare travel-time estimates for alternative routes.",
    "The traffic dataset used here describes I-94 in the United States. Predictions are not validated for Indian highways.",
    "Check reliable sources for current road closures, toll information and traffic advisories before a journey."
]

vectorizer = TfidfVectorizer(stop_words="english")

document_vectors = vectorizer.fit_transform(
    road_documents
)


def retrieve_documents(question, top_k=2):

    query_vector = vectorizer.transform([question])

    scores = cosine_similarity(
        query_vector,
        document_vectors
    )[0]

    indices = scores.argsort()[::-1]

    results = [
        road_documents[i]
        for i in indices[:top_k]
        if scores[i] > 0
    ]

    return results


# ========================================
# CHATBOT
# ========================================

def trafficgpt_chat(message, history):

    try:
        question = message.lower()

        import re

        match = re.search(
            r"\b(?:at|hour)\s*(\d{1,2})(?::\d{2})?\b",
            question
        )

        hour = int(match.group(1)) if match else 17

        weather = "Clear"

        for word in [
            "rain", "drizzle", "cloudy",
            "clouds", "snow", "mist", "fog"
        ]:
            if word in question:
                weather = word
                break

        prediction = predict_traffic(
            hour=hour,
            weather=weather
        )

        documents = retrieve_documents(message)

        rag_answer = "\n\n".join(documents)

        if not rag_answer:
            rag_answer = (
                "No matching information was found "
                "in the road knowledge base."
            )

        route_note = ""

        if any(word in question for word in [
            "route", "highway", "kakinada", "vijayawada"
        ]):
            route_note = """
**Route recommendation:** This prototype does not
have live route data. A routing API is required
to compare actual travel times between routes.
"""

        return f"""
# 🚦 TrafficGPT Prediction

### 📊 Traffic Prediction

- **Requested time:** {hour}:00
- **Weather input:** {weather.title()}
- **Predicted traffic volume:** {prediction['predicted_vehicles_per_hour']:,} vehicles/hour
- **Traffic level:** {prediction['traffic_level']}

---

### 📚 RAG Road Information

{rag_answer}

---

{route_note}

### ⚠️ Important limitation

This model uses historical US I-94 traffic data.
It does not provide live Indian traffic predictions.
The time, weather and other inputs include assumptions.
"""

    except Exception as e:
        return (
            "Sorry, prediction failed. Error: "
            + str(e)
        )


# ========================================
# WEBSITE DESIGN
# ========================================

css = """
.gradio-container {
    background: #f3f6fb !important;
}

#title {
    text-align: center;
    color: #123b67 !important;
    font-size: 36px !important;
    font-weight: bold !important;
}

#subtitle {
    text-align: center;
    color: #475569 !important;
}

.gradio-container h1,
.gradio-container h2,
.gradio-container h3,
.gradio-container p {
    color: #1e293b !important;
}

button.primary {
    background: #2563eb !important;
    color: white !important;
}
"""


with gr.Blocks(
    theme=gr.themes.Soft(
        primary_hue="blue",
        secondary_hue="cyan"
    ),
    css=css,
    title="TrafficGPT"
) as demo:

    gr.Markdown(
        "# 🚦 TrafficGPT",
        elem_id="title"
    )

    gr.Markdown(
        "AI Traffic Prediction & Route Recommendation Chatbot",
        elem_id="subtitle"
    )

    gr.Markdown("""
    ### Welcome to TrafficGPT!

    Ask about traffic predictions, road information
    and travel planning.

    🤖 Machine Learning Prediction

    📚 RAG Road Information

    🛣️ Route Planning Guidance
    """)

    gr.ChatInterface(
        fn=trafficgpt_chat,
        chatbot=gr.Chatbot(height=430),
        textbox=gr.Textbox(
            placeholder="Ask about your journey...",
            label="Your Question"
        ),
        examples=[
            "Predict traffic at 17:00 with rain",
            "How should I compare two routes?",
            "How can rain affect travel time?",
            "Which route should I take from Kakinada to Vijayawada?"
        ]
    )


if __name__ == "__main__":
    demo.launch()
