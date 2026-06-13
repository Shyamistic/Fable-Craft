"""
FastAPI Backend Service
Main entry point for the educational storytelling application API.
Routes requests to appropriate service modules.
"""

import base64
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from models import (
    CharacterGenerateRequest,
    CharacterGenerateResponse,
    CharacterData,
    QuestGenerateRequest,
    QuestGenerateResponse,
    QuestData,
    Scene,
    TTSSynthesizeRequest,
    TTSSynthesizeResponse,
    LessonValidateRequest,
    LessonValidateResponse,
    ParentDashboardResponse,
    ErrorResponse,
    ErrorCode,
)
from file_validator import validate_drawing
from vision_analyzer import VisionAnalyzer, ContentBlockedError, VisionAnalysisError
from character_generator import (
    CharacterGenerator,
    GenerationFailedError,
    ContentFilteredError,
)
from storage_service import StorageService, StorageError
from quest_engine import QuestEngine, QuestGenerationError
from scene_illustrator import SceneIllustrator
from content_moderator import ContentModerator, ModerationError
from tts_service import TTSService
from collab_manager import collab_manager

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# Load predefined lessons for custom lesson detection
_LESSONS_PATH = os.path.join(os.path.dirname(__file__), "data", "lessons.json")
try:
    with open(_LESSONS_PATH, "r", encoding="utf-8") as f:
        _lessons_data = json.load(f)
    PREDEFINED_LESSON_IDS = {lesson["id"] for lesson in _lessons_data.get("lessons", [])}
except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError):
    PREDEFINED_LESSON_IDS = {
        "sharing", "kindness", "honesty", "inclusion", "patience",
        "helping", "gratitude", "listening", "apologizing", "courage",
        "responsibility", "emotions",
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    logger.info(f"Starting {settings.app_name} on port {settings.port}")
    logger.info(f"AWS Region: {settings.aws_region}")
    logger.info(f"Debug mode: {settings.debug}")
    yield
    logger.info("Shutting down")


# Initialize FastAPI app
app = FastAPI(
    title="Fablecraft API",
    description="AI-powered educational storytelling backend with AWS services",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with specific frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Health Check Endpoints ---


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": "2.0.0",
    }


@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "region": settings.aws_region,
        "debug": settings.debug,
    }


# --- Character Generation ---


@app.post(
    "/api/characters/generate",
    response_model=CharacterGenerateResponse,
    responses={
        400: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def generate_character(request: CharacterGenerateRequest):
    """
    Analyze a drawing and generate an animated character.
    Validates the drawing, analyzes it with vision AI, and generates an animated character image.
    """
    # Step 1: Validate the drawing
    validation_result = validate_drawing(request.drawing_data)
    if not validation_result.is_valid:
        error_code = validation_result.error_code or ErrorCode.VALIDATION_ERROR
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "code": error_code.value,
                "message": validation_result.error_message,
            },
        )

    # Step 2: Analyze the drawing with Vision AI
    vision_analyzer = VisionAnalyzer()
    try:
        # Convert image bytes back to base64 for vision analysis
        image_b64 = base64.b64encode(validation_result.image_bytes).decode("utf-8")
        analysis = await vision_analyzer.analyze_drawing(
            image_data=image_b64,
            session_id=request.session_id,
        )
    except ContentBlockedError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "status": "error",
                "code": ErrorCode.CONTENT_BLOCKED.value,
                "message": str(e),
            },
        )
    except VisionAnalysisError:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "code": ErrorCode.SERVICE_UNAVAILABLE.value,
                "message": "Oops! Our art helper is taking a break. Please try again in a moment!",
            },
        )

    # Step 3: Generate the animated character image
    character_generator = CharacterGenerator()
    try:
        generation_result = await character_generator.generate_character(
            character_description=analysis["character_description"],
            character_type=analysis["character_type"],
            colors=analysis["colors_used"],
            artistic_style=analysis["artistic_style"],
            mood=analysis["mood"],
            session_id=request.session_id,
        )
    except ContentFilteredError:
        raise HTTPException(
            status_code=422,
            detail={
                "status": "error",
                "code": ErrorCode.CONTENT_BLOCKED.value,
                "message": "Let's try drawing something different! Your character needs to be friendly and fun.",
            },
        )
    except GenerationFailedError:
        # Fallback: use the original drawing as the "generated" character image
        # This allows the flow to continue even when image generation is unavailable
        logger.warning("Image generation failed, using original drawing as fallback")
        storage_fallback = StorageService()
        try:
            fallback_url = await storage_fallback.upload_bytes(
                data=validation_result.image_bytes,
                filename=f"{uuid.uuid4()}_generated.png",
                content_type="image/png",
                session_id=request.session_id,
            )
            generation_result = {
                "image_url": fallback_url,
                "image_id": str(uuid.uuid4()),
            }
        except Exception:
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "code": ErrorCode.GENERATION_FAILED.value,
                    "message": "Oops! Let's try that again. Our character maker needs another chance.",
                },
            )

    # Step 4: Store original drawing in S3
    storage = StorageService()
    try:
        original_drawing_url = await storage.upload_bytes(
            data=validation_result.image_bytes,
            filename=f"{uuid.uuid4()}.png",
            content_type=validation_result.detected_format or "image/png",
            session_id=request.session_id,
        )
    except StorageError:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "code": ErrorCode.SERVICE_UNAVAILABLE.value,
                "message": "Something went wrong saving your picture. Let's try again!",
            },
        )

    # Step 5: Build and return the full character response
    character_id = generation_result["image_id"]
    created_at = datetime.now(timezone.utc).isoformat()

    character_data = CharacterData(
        id=character_id,
        name=request.character_name,
        character_type=analysis["character_type"],
        character_description=analysis["character_description"],
        colors_used=analysis["colors_used"],
        artistic_style=analysis["artistic_style"],
        mood=analysis["mood"],
        generated_image_url=generation_result["image_url"],
        original_drawing_url=original_drawing_url,
        created_at=created_at,
    )

    return CharacterGenerateResponse(
        status="success",
        character=character_data,
    )


# --- Quest Generation ---


@app.post(
    "/api/quests/generate",
    response_model=QuestGenerateResponse,
    responses={
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def generate_quest(request: QuestGenerateRequest):
    """
    Generate an 8-scene interactive quest.
    Creates a story quest with scenes, illustrations, and answer options.
    
    Flow:
    1. If custom lesson (not predefined), validate via ContentModerator
    2. Generate quest scenes via QuestEngine
    3. Generate scene illustrations via SceneIllustrator (batch 1-4, then 5-8)
    4. Combine scene data with image URLs
    5. Return QuestGenerateResponse
    """
    lesson = request.lesson
    session_id = request.session_id

    # Step 1: Content moderation for custom lessons
    if lesson not in PREDEFINED_LESSON_IDS:
        moderator = ContentModerator()
        try:
            moderation_result = await moderator.validate_lesson(
                text=lesson, session_id=session_id
            )
            if not moderation_result["is_appropriate"]:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "status": "error",
                        "code": ErrorCode.CUSTOM_LESSON_REJECTED.value,
                        "message": "Let's pick a different topic! How about one of these fun lessons instead?",
                    },
                )
            # Use the sanitized lesson text
            lesson = moderation_result["sanitized_lesson"]
        except ModerationError:
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "code": ErrorCode.SERVICE_UNAVAILABLE.value,
                    "message": "Our story helper is taking a break. Please try again in a moment!",
                },
            )

    # Step 2: Generate quest scenes via QuestEngine
    quest_engine = QuestEngine()
    try:
        scenes = await quest_engine.generate_quest(
            character_name=request.character_name,
            character_description=request.character_description,
            lesson=lesson,
            genre=request.genre,
            session_id=session_id,
        )
    except QuestGenerationError:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "code": ErrorCode.GENERATION_FAILED.value,
                "message": "Oops! Our story maker needs another try. Please tap the button again!",
            },
        )

    # Step 3: Generate scene illustrations via SceneIllustrator
    # Prepare scene dicts for the illustrator
    scene_dicts = [
        {
            "scene_number": scene.scene_number,
            "narrative": scene.narrative,
        }
        for scene in scenes
    ]

    # Extract character_type from description (first word or default)
    character_type = request.character_description.split()[0].lower() if request.character_description else "character"

    illustrator = SceneIllustrator()
    try:
        illustration_results = await illustrator.illustrate_scenes(
            scenes=scene_dicts,
            character_description=request.character_description,
            character_type=character_type,
            genre=request.genre,
            session_id=session_id,
        )
    except Exception as e:
        # Illustration failure is partial - use placeholders for all scenes
        logger.warning(f"Scene illustration failed entirely: {e}. Using placeholders.")
        from scene_illustrator import PLACEHOLDER_IMAGE_URL
        illustration_results = [
            {"scene_number": i + 1, "image_url": PLACEHOLDER_IMAGE_URL}
            for i in range(8)
        ]

    # Step 4: Combine scene data with image URLs
    # Build a mapping from scene_number to image_url
    image_url_map = {
        result["scene_number"]: result["image_url"]
        for result in illustration_results
    }

    # Update scenes with image URLs
    completed_scenes = []
    for scene in scenes:
        image_url = image_url_map.get(
            scene.scene_number,
            "https://placehold.co/1024x576/e2e8f0/64748b?text=Scene+Illustration+Unavailable",
        )
        completed_scene = Scene(
            scene_number=scene.scene_number,
            narrative=scene.narrative,
            question=scene.question,
            options=scene.options,
            image_url=image_url,
        )
        completed_scenes.append(completed_scene)

    # Step 5: Build and return response
    quest_id = str(uuid.uuid4())
    quest_title = f"{request.character_name}'s {lesson.replace('_', ' ').title()} Adventure"

    quest_data = QuestData(
        id=quest_id,
        title=quest_title,
        lesson=lesson,
        genre=request.genre,
        character_name=request.character_name,
        scenes=completed_scenes,
        total_scenes=8,
    )

    return QuestGenerateResponse(
        status="success",
        quest=quest_data,
    )


# --- TTS ---


@app.post(
    "/api/tts/synthesize",
    response_model=TTSSynthesizeResponse,
    responses={500: {"model": ErrorResponse}},
)
async def synthesize_speech(request: TTSSynthesizeRequest):
    """
    Convert text to speech using Amazon Polly Neural.
    Returns a URL to the generated MP3 audio file.
    """
    tts_service = TTSService()
    result = await tts_service.synthesize(text=request.text, session_id=request.session_id)

    if result["available"]:
        return TTSSynthesizeResponse(
            status="success",
            audio_url=result["audio_url"],
            duration_seconds=result["duration_seconds"],
        )
    else:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "code": ErrorCode.SERVICE_UNAVAILABLE.value,
                "message": (
                    "The read-aloud button isn't working right now, "
                    "but you can keep reading!"
                ),
            },
        )


# --- Lesson Validation ---


@app.post(
    "/api/lessons/validate",
    response_model=LessonValidateResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def validate_lesson(request: LessonValidateRequest):
    """
    Validate a custom lesson topic for age-appropriateness.
    Checks length and content safety via LLM.
    """
    moderator = ContentModerator()

    try:
        result = await moderator.validate_lesson(
            text=request.custom_lesson,
            session_id=request.session_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "code": ErrorCode.VALIDATION_ERROR.value,
                "message": str(e),
            },
        )
    except ModerationError:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "code": ErrorCode.SERVICE_UNAVAILABLE.value,
                "message": "Oops! We couldn't check your lesson right now. Please try again in a moment!",
            },
        )

    return LessonValidateResponse(
        status="success",
        is_appropriate=result["is_appropriate"],
        sanitized_lesson=result["sanitized_lesson"],
    )


# --- Parent Dashboard ---

from pin_lockout import (
    is_locked_out,
    remaining_lockout_seconds,
    record_failed_attempt,
    record_success,
    reset_lockout_state,
)

# In-memory store for dashboard data (MVP — replaced by persistent storage later)
_dashboard_stats = {
    "quests_completed": 0,
    "lessons_covered": 0,
    "total_coins": 0,
    "characters_created": 0,
    "total_time_minutes": 0,
}
_recent_quests: list = []


@app.get(
    "/api/parent/dashboard",
    response_model=ParentDashboardResponse,
    responses={401: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
async def get_parent_dashboard(x_pin: str = Header(..., alias="X-PIN")):
    """
    Get parent dashboard with stats and recent quests.
    Requires correct 4-digit PIN in X-PIN header.
    """
    # Check lockout first
    if is_locked_out():
        remaining = remaining_lockout_seconds()
        raise HTTPException(
            status_code=429,
            detail={
                "status": "error",
                "code": ErrorCode.PIN_LOCKOUT.value,
                "message": f"Too many tries! Wait {remaining} seconds and try again.",
            },
        )

    # Validate PIN format: must be exactly 4 digits
    if not (len(x_pin) == 4 and x_pin.isdigit()):
        triggered = record_failed_attempt()
        if triggered:
            raise HTTPException(
                status_code=429,
                detail={
                    "status": "error",
                    "code": ErrorCode.PIN_LOCKOUT.value,
                    "message": "Too many tries! Wait a minute and try again.",
                },
            )
        raise HTTPException(
            status_code=401,
            detail={
                "status": "error",
                "code": ErrorCode.PIN_INCORRECT.value,
                "message": "The PIN is incorrect. Please try again.",
            },
        )

    # Validate PIN value
    if x_pin != settings.parent_pin:
        triggered = record_failed_attempt()
        if triggered:
            raise HTTPException(
                status_code=429,
                detail={
                    "status": "error",
                    "code": ErrorCode.PIN_LOCKOUT.value,
                    "message": "Too many tries! Wait a minute and try again.",
                },
            )
        raise HTTPException(
            status_code=401,
            detail={
                "status": "error",
                "code": ErrorCode.PIN_INCORRECT.value,
                "message": "The PIN is incorrect. Please try again.",
            },
        )

    # PIN is correct — reset lockout state and return dashboard data
    record_success()

    from models import ParentDashboardStats, RecentQuest

    stats = ParentDashboardStats(**_dashboard_stats)
    recent = _recent_quests[:50]  # Cap at 50, newest-first

    return ParentDashboardResponse(
        status="success",
        stats=stats,
        recent_quests=recent,
    )


# --- Collaborative Mode WebSocket ---


@app.websocket("/ws/collab/{room_code}")
async def collaborative_websocket(websocket: WebSocket, room_code: str):
    """
    WebSocket endpoint for collaborative story mode.
    Handles room joining, turn alternation, and disconnect events.
    """
    await collab_manager.handle_websocket(websocket, room_code)


# --- Entry Point ---

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=settings.port)
