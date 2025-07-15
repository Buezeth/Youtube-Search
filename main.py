import os
import yt_dlp
import google.generativeai as genai
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found. Please set it in your .env file.")

genai.configure(api_key=api_key)

app = FastAPI(
    title="AI Learning Path Generator",
    description="Generates a complete, structured learning path with YouTube videos based on a topic.",
    version="4.0.0-robust"
)


# --- AI SCHEMA MODELS (for structured AI output) ---
# Schema to get just the module titles first
class AIModuleTitle(BaseModel):
    module_title: str = Field(description="The title of a single learning module.")

class AIModuleListSchema(BaseModel):
    modules: List[AIModuleTitle]

# Schema to get the lessons for a single module
class AILessonTitle(BaseModel):
    lesson_title: str = Field(description="A concise, YouTube-searchable title for a single lesson.")

class AILessonListSchema(BaseModel):
    lessons: List[AILessonTitle]


# --- FINAL API RESPONSE MODELS ---
class VideoInfo(BaseModel):
    title: str
    url: str
    thumbnail: Optional[str] = None
    duration_string: Optional[str] = None

class Lesson(BaseModel):
    lesson_title: str
    videos: List[VideoInfo]

class Module(BaseModel):
    module_title: str
    lessons: List[Lesson]

class LearningRequest(BaseModel):
    topic: str = Field(..., min_length=5, example="I want to learn how to bake sourdough bread")

class LearningPathResponse(BaseModel):
    learning_topic: str
    modules: List[Module]


# --- CORE FUNCTIONS ---
def call_gemini_with_schema(prompt: str, response_schema: BaseModel):
    """A generic helper function to call the Gemini API with a given schema."""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(
            contents=prompt,
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": response_schema,
            },
        )
        if not response.parts or not response.parts[0].text:
             raise ValueError("AI response was empty.")
        
        # Use model_validate_json for robust parsing
        return response_schema.model_validate_json(response.parts[0].text)

    except Exception as e:
        print(f"An error occurred during Gemini API call: {e}")
        # Re-raise the exception to be handled by the main endpoint
        raise e

def search_youtube(keywords: str, max_results: int = 3) -> List[dict]:
    """Searches YouTube for videos."""
    ydl_opts = {
        'quiet': True,
        'extract_flat': 'in_playlist',
        'force_generic_extractor': True,
        'skip_download': True,
    }
    search_query = f"ytsearch{max_results}:{keywords}"
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            result = ydl.extract_info(search_query, download=False)
            return [entry for entry in result.get('entries', []) if entry]
        except Exception as e:
            print(f"An error occurred during YouTube search for '{keywords}': {e}")
            return []


# --- API ENDPOINT ---
@app.post("/generate-learning-path", response_model=LearningPathResponse)
async def generate_learning_path(request: LearningRequest):
    """
    Generates a full learning path using a robust two-step AI process.
    """
    print(f"Received request for topic: '{request.topic}'")
    
    try:
        # STEP 1: Get only the module titles from the AI
        print("Step 1: Fetching module titles from AI...")
        module_prompt = f"You are an expert curriculum designer. For the topic '{request.topic}', generate a list of 3 to 5 logical module titles for a beginner's learning path."
        module_list_response = call_gemini_with_schema(module_prompt, AIModuleListSchema)
        
        if not module_list_response or not module_list_response.modules:
            raise HTTPException(status_code=404, detail="AI failed to generate any module titles.")

        final_modules = []
        # STEP 2: For each module, get its lessons and then search for videos
        for module_title_obj in module_list_response.modules:
            module_title = module_title_obj.module_title
            print(f"Step 2: Processing module '{module_title}'...")

            # STEP 2a: Get lessons for this specific module
            print(f"  - Fetching lessons for '{module_title}'...")
            lesson_prompt = f"You are a curriculum expert. For the learning module '{module_title}' on the main topic '{request.topic}', generate a list of 3 to 5 concise lesson titles. These titles should be perfect for YouTube searches."
            lesson_list_response = call_gemini_with_schema(lesson_prompt, AILessonListSchema)

            if not lesson_list_response or not lesson_list_response.lessons:
                print(f"  - Warning: AI did not return lessons for module '{module_title}'. Skipping.")
                continue
            
            final_lessons = []
            # STEP 2b: For each lesson, search YouTube
            for lesson_title_obj in lesson_list_response.lessons:
                lesson_title = lesson_title_obj.lesson_title
                print(f"    - Searching videos for lesson: '{lesson_title}'")
                
                video_results = search_youtube(lesson_title, max_results=3)
                lesson_videos = [
                    VideoInfo(
                        title=video.get('title', 'N/A'),
                        url=video.get('webpage_url') or video.get('url', 'N/A'),
                        thumbnail=video.get('thumbnail'),
                        duration_string=video.get('duration_string')
                    ) for video in video_results
                ]
                final_lessons.append(Lesson(lesson_title=lesson_title, videos=lesson_videos))
            
            if final_lessons:
                final_modules.append(Module(module_title=module_title, lessons=final_lessons))

        if not final_modules:
            raise HTTPException(status_code=404, detail="Could not generate a complete course structure.")
            
        return LearningPathResponse(learning_topic=request.topic, modules=final_modules)

    except Exception as e:
        # Catch any errors from the AI calls or other processing
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"A failure occurred while generating the learning path: {e}"
        )