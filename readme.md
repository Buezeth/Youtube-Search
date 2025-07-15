
---

# AI Real-time Learning Path Generator

This project is a web application that generates a complete, structured learning path on any topic provided by the user. It leverages the Google Gemini AI to create a curriculum of modules and lessons, then fetches relevant YouTube videos for each lesson, and streams the entire course back to the user in real-time.

The user interface is designed for interactivity, embedding the primary video for each lesson directly on the page for immediate viewing.

 <!-- This is a placeholder for a real screenshot -->

## Features

-   **AI-Powered Curriculum:** Uses the Google Gemini API to generate a logical course structure with modules and lessons.
-   **Real-time Streaming:** The backend uses FastAPI's `StreamingResponse` to send modules to the frontend as soon as they are ready, providing an interactive and responsive user experience.
-   **Asynchronous Backend:** YouTube searches for all lessons within a module are performed concurrently using `asyncio`, dramatically speeding up processing time.
-   **Interactive Frontend:** The UI dynamically renders the learning path, embedding the top video for each lesson in a YouTube iframe for instant playback.
-   **Optimized for Speed:** Utilizes `yt-dlp`'s fast `extract_flat` search method, perfectly balancing performance with the required data.
-   **Robust and Reliable:** Implements a two-step AI interaction (get modules, then get lessons) to ensure reliable curriculum generation.
-   **Developer-Friendly Caching:** Includes an in-memory cache to prevent hitting API rate limits during development and testing.

## Technology Stack

-   **Backend:** Python 3.7+, FastAPI, Uvicorn
-   **AI Model:** Google Gemini API (`gemini-1.5-flash-latest`)
-   **YouTube Integration:** `yt-dlp`
-   **Environment Management:** `python-dotenv`
-   **Data Validation:** Pydantic
-   **Frontend:** Vanilla HTML, CSS, and JavaScript

## Setup and Installation

Follow these steps to set up and run the project locally.

### 1. Prerequisites

-   Python 3.7+ installed.
-   `pip` (Python package installer).

### 2. Get the Code

Clone this repository or download the source code into a project folder.

### 3. Create the `.env` File

This file will store your secret API key.

Create a file named `.env` in the root of your project folder and add the following line:

```
GEMINI_API_KEY="YOUR_API_KEY_HERE"
```

**How to get your API Key:**

> **Important:** The Gemini API free tier has a rate limit **per Google Cloud Project**. To ensure you have a fresh quota, it is highly recommended to create a **brand new project**.

1.  Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a **New Project**.
2.  Select your new project.
3.  In the search bar, find and **Enable** the **"Generative Language API"**.
4.  Navigate to **"APIs & Services" -> "Credentials"**.
5.  Click **"+ Create Credentials"** -> **"API key"**.
6.  Copy the newly generated key and paste it into your `.env` file.

### 4. Create the `requirements.txt` File

Create a file named `requirements.txt` in the root of your project folder with the following content:

```
fastapi
uvicorn[standard]
yt-dlp
google-generativeai
python-dotenv
pydantic
```

### 5. Set Up a Virtual Environment

This isolates your project's dependencies.

```bash
# Create a virtual environment named 'venv'
python -m venv venv

# Activate the environment
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

Your terminal prompt should now be prefixed with `(venv)`.

### 6. Install Dependencies

Run the following command in your activated terminal:

```bash
pip install -r requirements.txt
```

## Running the Application

1.  **Start the Server:**
    In your terminal (with the virtual environment activated), run the following command:
    ```bash
    uvicorn main:app --reload
    ```
    The `--reload` flag automatically restarts the server when you make code changes.

2.  **Open the Web Interface:**
    Open your web browser and navigate to:
    **http://127.0.0.1:8000/ui/index.html**

    You can now enter a topic and see your real-time learning path being generated!

## Project Structure

```
.
├── .env                  # Stores your secret API key
├── main.py               # The main FastAPI backend application
├── requirements.txt      # Lists all Python dependencies
└── static/
    └── index.html        # The frontend web page (HTML, CSS, JS)
```

## Troubleshooting

-   **`404 Not Found` when visiting `/ui`:**
    -   Ensure your project structure is correct and the `static` folder is at the same level as `main.py`.
    -   Confirm the `app.mount(...)` line in `main.py` is correct.

-   **`429 Rate Limit Exceeded` Error:**
    -   You have exhausted the free tier daily limit for your Google Cloud **Project**.
    -   The only solution is to create a **brand new Google Cloud Project** and a new API key, as described in the setup instructions.
    -   The built-in cache will help prevent this during development for repeated search terms.

-   **App uses an old API key even after changing `.env`:**
    -   This is a common environment caching issue.
    -   Completely **close and terminate your terminal and your code editor (e.g., VS Code)**.
    -   Re-open a fresh terminal, activate the virtual environment, and restart the server. This forces your system to read the new value from the `.env` file.