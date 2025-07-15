import os
import asyncio
import json
import yt_dlp
import google.generativeai as genai
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Optional, AsyncGenerator
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found.")
genai.configure(api_key=api_key)

app = FastAPI(
    title="Real-time AI Learning Path Generator",
    description="Streams a learning path with asynchronously fetched YouTube videos.",
    version="5.1.0-caching"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/ui", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# --- CACHING ---
# A simple in-memory dictionary to store results for topics we've already processed.
# In a real production app, you might use Redis or another caching database.
CACHE = {}

# --- PYDANTIC MODELS (Unchanged) ---
class AIModuleTitle(BaseModel):
    module_title: str
class AIModuleListSchema(BaseModel):
    modules: List[AIModuleTitle]
class AILessonTitle(BaseModel):
    lesson_title: str
class AILessonListSchema(BaseModel):
    lessons: List[AILessonTitle]
class VideoInfo(BaseModel):
    """Defines the structure for a single video result, optimized for speed."""
    title: str
    url: str
    thumbnail: Optional[str] = None
class Lesson(BaseModel):
    lesson_title: str
    videos: List[VideoInfo]
class Module(BaseModel):
    module_title: str
    lessons: List[Lesson]
class LearningRequest(BaseModel):
    topic: str = Field(..., min_length=5, example="I want to learn about Black Holes")


# --- CORE FUNCTIONS (Unchanged) ---
# ... (all the functions like search_youtube_async and call_gemini_with_schema are the same) ...
def search_youtube_sync(keywords: str, max_results: int = 3) -> List[dict]:
    """
    The FASTEST YouTube search function using 'extract_flat'.
    It doesn't reliably get duration, but it's perfect now that we don't need it.
    """
    print(f"      - Starting FAST YouTube search for: '{keywords}'")
    
    # We are back to the super-fast 'extract_flat' method.
    ydl_opts = {
        'quiet': True,
        'extract_flat': 'in_playlist',
        'force_generic_extractor': True,
    }
    
    # The search query format for 'extract_flat' is slightly different.
    search_query = f"ytsearch{max_results}:{keywords}"
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(search_query, download=False)
            print(f"      - Finished FAST YouTube search for: '{keywords}'")
            # The entries are directly available in the result.
            return [entry for entry in result.get('entries', []) if entry]
    except Exception as e:
        print(f"An error occurred during YouTube search for '{keywords}': {e}")
        return []

async def search_youtube_async(keywords: str, max_results: int = 3) -> List[dict]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, search_youtube_sync, keywords, max_results)

async def call_gemini_with_schema(prompt: str, response_schema: BaseModel):
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    response = await model.generate_content_async(
        contents=prompt,
        generation_config={"response_mime_type": "application/json", "response_schema": response_schema},
    )
    return response_schema.model_validate_json(response.text)


# --- THE STREAMING API ENDPOINT (Modified with Caching Logic) ---
@app.post("/generate-learning-path-stream")
async def generate_learning_path_stream(request: LearningRequest):
    
    # Check cache first
    topic_key = request.topic.lower().strip()
    if topic_key in CACHE:
        print(f"CACHE HIT for topic: '{topic_key}'")
        async def cached_stream_generator():
            for chunk in CACHE[topic_key]:
                yield json.dumps(chunk) + "\n"
                await asyncio.sleep(0.1)
        return StreamingResponse(cached_stream_generator(), media_type="application/x-ndjson")
    
    print(f"CACHE MISS for topic: '{topic_key}'. Processing live.")
    
    async def stream_generator() -> AsyncGenerator[str, None]:
        processed_chunks = [] # Store chunks to add to cache later

        # ... (the rest of the function is the same logic as before) ...
        print(f"Stream started for topic: '{request.topic}'")
        module_prompt = f"Generate 3-5 module titles for a course on '{request.topic}'."
        try:
            module_list_response = await call_gemini_with_schema(module_prompt, AIModuleListSchema)
        except Exception as e:
            error_message = {"error": f"Failed to generate modules: {e}"}
            yield json.dumps(error_message) + "\n"
            return

        for module_title_obj in module_list_response.modules:
            module_title = module_title_obj.module_title
            print(f"  Processing module: '{module_title}'")
            lesson_prompt = f"Generate 3-5 lesson titles for the module '{module_title}'."
            try:
                lesson_list_response = await call_gemini_with_schema(lesson_prompt, AILessonListSchema)
            except Exception:
                continue

            search_tasks = [search_youtube_async(lesson.lesson_title) for lesson in lesson_list_response.lessons]
            print(f"    - Starting parallel video search for {len(search_tasks)} lessons...")
            video_search_results = await asyncio.gather(*search_tasks)
            print(f"    - Finished parallel video search.")
            
            final_lessons = []
            for i, lesson_title_obj in enumerate(lesson_list_response.lessons):
                videos = [VideoInfo(**video) for video in video_search_results[i] if video.get('url')]
                final_lessons.append(Lesson(lesson_title=lesson_title_obj.lesson_title, videos=videos))
            
            final_module = Module(module_title=module_title, lessons=final_lessons)
            
            chunk_to_send = final_module.model_dump()
            processed_chunks.append(chunk_to_send) # Add to our list for caching

            yield json.dumps(chunk_to_send) + "\n"
            await asyncio.sleep(0.1)

        # After the stream is finished, save the full result to the cache
        CACHE[topic_key] = processed_chunks
        print(f"Saved results for '{topic_key}' to cache.")

    return StreamingResponse(stream_generator(), media_type="application/x-ndjson")

# http://127.0.0.1:8000/ui/index.html