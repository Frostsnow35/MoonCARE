import logging
import os
import re
from pathlib import Path
from typing import Iterable, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user_id
from app.database import get_db
from app.models.music import Music, MusicFeedback
from app.schemas.music import (
    MusicFeedbackRequest,
    MusicFeedbackResponse,
    MusicRecommendationContext,
    MusicRecommendResponse,
)
from app.services.emotion_engine import EmotionEngine


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/music", tags=["音乐疗愈"])

MUSIC_DIR = Path(__file__).resolve().parents[3] / "music"
AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac"}
MAX_UPLOAD_BYTES = 30 * 1024 * 1024
ALLOWED_FEEDBACK_ACTIONS = {"played", "completed", "liked", "disliked", "skipped", "play_failed"}


def get_emotion_category_from_mood(mood_level: float) -> str:
    """Map a 1-10 mood score to a lightweight music recommendation category."""
    if mood_level >= 7:
        return "joy"
    if mood_level >= 4:
        return "normal"
    return "anxiety"


def _emotion_reason(emotion_category: str) -> str:
    reasons = {
        "joy": "今天的状态看起来更轻快，适合听明亮一点的音乐。",
        "normal": "当前状态比较平稳，适合听轻柔、稳定的音乐。",
        "anxiety": "如果身体或心里有些绷紧，适合先听偏舒缓、低刺激的旋律。",
        "sadness": "如果情绪有些往下沉，适合听温和、有承托感的音乐。",
        "calm": "你可能更需要安静和放松，适合听节奏慢一点的音乐。",
    }
    return reasons.get(emotion_category, "为你推荐更柔和、低压力的音乐。")


def _emotion_message(emotion_category: str) -> str:
    messages = {
        "joy": "为你准备了轻快一点的音乐。",
        "normal": "为你准备了平稳、轻柔的音乐。",
        "anxiety": "为你准备了偏舒缓的音乐。",
        "sadness": "为你准备了温和陪伴感更强的音乐。",
        "calm": "为你准备了适合放松的音乐。",
    }
    return messages.get(emotion_category, "为你推荐疗愈音乐。")


def _infer_local_category(filename: str) -> str:
    name = Path(filename).stem.lower()
    calming_keywords = ("forest", "water", "cloud", "mountain", "sleep", "meditation", "healing", "rain")
    bright_keywords = ("happy", "sun", "bright", "walk", "carefree")
    if any(keyword in name for keyword in bright_keywords):
        return "joy"
    if any(keyword in name for keyword in calming_keywords):
        return "calm"
    return "normal"


def _compatible_categories(emotion_category: str) -> List[str]:
    compatibility = {
        "anxiety": ["anxiety", "calm", "normal"],
        "sadness": ["sadness", "calm", "normal"],
        "joy": ["joy", "normal", "calm"],
        "normal": ["normal", "calm"],
        "calm": ["calm", "normal"],
    }
    return compatibility.get(emotion_category, [emotion_category, "calm", "normal"])


def _attach_recommendation_metadata(
    song: Music,
    *,
    source: str,
    requested_emotion: str,
    fallback: bool = False,
) -> Music:
    category = song.emotion_category or "normal"
    if category == requested_emotion:
        reason = "适合现在先听一小段。"
    elif fallback:
        reason = "没有完全匹配的曲目，先用更柔和的音乐作临时陪伴。"
    else:
        reason = "这首旋律比较温和，可以作为当下的轻量陪伴。"

    song.source = source
    song.recommendation_reason = reason
    song.playback_notice = "如遇播放失败，可以切换下一首或稍后重试。"
    return song


def _local_music_candidates(requested_emotion: Optional[str] = None) -> List[Music]:
    if not MUSIC_DIR.exists():
        return []

    compatible = _compatible_categories(requested_emotion) if requested_emotion else None
    candidates: List[Music] = []
    try:
        filenames = sorted(os.listdir(MUSIC_DIR))
    except OSError as exc:
        logger.warning("Cannot read music directory %s: %s", MUSIC_DIR, exc)
        return []

    for index, filename in enumerate(filenames):
        suffix = Path(filename).suffix.lower()
        if suffix not in AUDIO_EXTENSIONS:
            continue

        category = _infer_local_category(filename)
        if compatible and category not in compatible:
            continue

        song = Music(
            id=100000 + index,
            title=Path(filename).stem,
            artist="本地音乐",
            url=f"/media/music/{filename}",
            duration=180,
            mood_tags=[category, "local"],
            emotion_category=category,
            is_active=1,
            cover_url=None,
        )
        candidates.append(
            _attach_recommendation_metadata(
                song,
                source="local",
                requested_emotion=requested_emotion or category,
                fallback=bool(requested_emotion and category != requested_emotion),
            )
        )

    return candidates


def _rank_candidates(candidates: Iterable[Music], requested_emotion: str) -> List[Music]:
    compatible = _compatible_categories(requested_emotion)
    compatibility_rank = {category: index for index, category in enumerate(compatible)}

    def score(song: Music) -> tuple[int, str]:
        return (
            compatibility_rank.get(song.emotion_category, len(compatibility_rank) + 1),
            song.title or "",
        )

    return sorted(candidates, key=score)


def _serialize_music(song: Music, source: str = "library") -> dict:
    return {
        "id": song.id,
        "title": song.title,
        "artist": song.artist,
        "url": song.url,
        "duration": song.duration,
        "mood_tags": song.mood_tags or [],
        "emotion_category": song.emotion_category,
        "cover_url": song.cover_url,
        "source": getattr(song, "source", source),
        "recommendation_reason": getattr(song, "recommendation_reason", None),
        "playback_notice": getattr(song, "playback_notice", None),
    }


def _safe_upload_name(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    stem = Path(filename).stem
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("-._") or "music"
    return f"upload-{uuid4().hex[:12]}-{cleaned[:40]}{suffix}"


@router.get("/recommend", response_model=MusicRecommendResponse)
async def recommend_music(
    emotion_category: Optional[str] = None,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> MusicRecommendResponse:
    """Recommend music for the current authenticated user with explainable context."""
    mood_level = 5.0
    try:
        emotion_result = await EmotionEngine(db).analyze(user_id)
        mood_level = float(emotion_result.get("mood_level") or 5.0)
    except Exception as exc:
        logger.warning("Music emotion analysis fallback for user_id=%s: %s", user_id, exc)

    requested_emotion = emotion_category or get_emotion_category_from_mood(mood_level)
    compatible = _compatible_categories(requested_emotion)

    db_music = (
        db.query(Music)
        .filter(Music.is_active == 1, Music.emotion_category.in_(compatible))
        .all()
    )
    db_music = [
        _attach_recommendation_metadata(
            song,
            source="library",
            requested_emotion=requested_emotion,
            fallback=song.emotion_category != requested_emotion,
        )
        for song in db_music
    ]

    local_music = _local_music_candidates(requested_emotion)
    ranked = _rank_candidates([*db_music, *local_music], requested_emotion)
    recommended_songs = ranked[:5]
    fallback_used = not any(song.emotion_category == requested_emotion for song in recommended_songs)

    context = MusicRecommendationContext(
        source="mixed" if db_music and local_music else ("library" if db_music else "local"),
        reason=_emotion_reason(requested_emotion),
        signals=[],
        fallback_used=fallback_used,
    )

    return MusicRecommendResponse(
        current_emotion=requested_emotion,
        recommended_songs=recommended_songs,
        message=_emotion_message(requested_emotion),
        recommendation_context=context,
    )


@router.get("/list")
async def list_music(
    emotion_category: Optional[str] = None,
    limit: int = 50,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """List database and local music for the authenticated user context."""
    del user_id
    query = db.query(Music).filter(Music.is_active == 1)
    if emotion_category:
        query = query.filter(Music.emotion_category == emotion_category)

    db_music = query.limit(max(1, min(limit, 100))).all()
    db_urls = {song.url for song in db_music}
    local_music = [song for song in _local_music_candidates(None) if song.url not in db_urls]
    music_list = [*_serialize_many(db_music, "library"), *[_serialize_music(song, "local") for song in local_music]]
    music_list = music_list[: max(1, min(limit, 100))]

    return {"total": len(music_list), "music_list": music_list}


def _serialize_many(songs: Iterable[Music], source: str) -> List[dict]:
    return [_serialize_music(song, source) for song in songs]


@router.post("/upload")
async def upload_music(
    title: Optional[str] = Form(default=None),
    artist: Optional[str] = Form(default=None),
    user_id: int = Depends(get_current_user_id),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload an audio file and persist it as a playable music record."""
    del user_id
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只支持 mp3、wav、ogg、m4a、aac、flac 音频文件。",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="上传文件为空。")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="单个音频不能超过 30MB。")

    MUSIC_DIR.mkdir(parents=True, exist_ok=True)
    stored_name = _safe_upload_name(file.filename or f"music{suffix}")
    target_path = MUSIC_DIR / stored_name
    target_path.write_bytes(content)

    music = Music(
        title=(title or Path(file.filename or stored_name).stem).strip()[:200],
        artist=(artist or "本地上传").strip()[:100],
        url=f"/media/music/{stored_name}",
        duration=None,
        mood_tags=["uploaded", "local"],
        emotion_category="normal",
        is_active=1,
        cover_url=None,
    )
    db.add(music)
    db.commit()
    db.refresh(music)
    music.source = "uploaded"

    return {"code": 200, "data": _serialize_music(music, "uploaded"), "message": "音乐已上传"}


@router.post("/feedback")
async def create_music_feedback(
    payload: MusicFeedbackRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Persist lightweight playback and preference feedback for the current user."""
    if payload.action not in ALLOWED_FEEDBACK_ACTIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported music feedback action.",
        )

    feedback = MusicFeedback(
        user_id=user_id,
        music_id=payload.music_id,
        music_title=payload.music_title,
        action=payload.action,
        emotion_category=payload.emotion_category,
        source=payload.source,
        note=payload.note,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    return {
        "code": 200,
        "data": MusicFeedbackResponse.model_validate(feedback),
        "message": "反馈已记录",
    }


@router.post("/seed")
async def seed_music_data(db: Session = Depends(get_db)):
    """Seed example music data for local development."""
    existing = db.query(Music).first()
    if existing:
        return {"status": "already_seeded", "message": "音乐数据已存在"}

    sample_music = [
        Music(
            title="Slow Sleep",
            artist="Kevin MacLeod",
            url="https://incompetech.com/music/royalty-free/mp3-royaltyfree/Slow%20Sleep.mp3",
            duration=270,
            mood_tags=["calm", "relaxed", "sleep"],
            emotion_category="normal",
            cover_url=None,
        ),
        Music(
            title="Healing",
            artist="Kevin MacLeod",
            url="https://incompetech.com/music/royalty-free/mp3-royaltyfree/Healing.mp3",
            duration=180,
            mood_tags=["anxious", "healing", "relaxing"],
            emotion_category="anxiety",
            cover_url=None,
        ),
    ]

    for music in sample_music:
        db.add(music)

    db.commit()
    return {"status": "success", "message": f"已添加 {len(sample_music)} 首示例音乐"}
