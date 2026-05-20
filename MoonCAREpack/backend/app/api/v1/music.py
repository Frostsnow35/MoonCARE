from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import random
import os
from pathlib import Path

from app.database import get_db
from app.models.music import Music
from app.schemas.music import Music as MusicSchema, MusicRecommendResponse
from app.services.emotion_engine import EmotionEngine

router = APIRouter(prefix="/music", tags=["音乐疗愈"])

# Local music directory (one more level up to backend/)
MUSIC_DIR = Path(__file__).parent.parent.parent.parent / "music"


def get_emotion_category_from_mood(mood_level: float) -> str:
    """根据情绪等级映射到情绪分类"""
    if mood_level >= 7:
        return "joy"
    elif mood_level >= 4:
        return "normal"
    else:
        return "anxiety"


@router.get("/recommend", response_model=MusicRecommendResponse)
async def recommend_music(
    user_id: int,
    emotion_category: str = None,
    db: Session = Depends(get_db)
):
    """
    根据用户当前情绪状态推荐音乐
    触发条件：用户点击音乐疗愈模块
    优先从本地音乐文件夹随机选择音乐
    """
    # Get user's current emotion state
    engine = EmotionEngine(db)
    try:
        emotion_result = await engine.analyze(user_id)
        mood_level = emotion_result.get("mood_level", 5.0)
    except Exception:
        mood_level = 5.0

    # Determine emotion category if not provided
    if not emotion_category:
        emotion_category = get_emotion_category_from_mood(mood_level)

    # Try to get local music files first
    local_music_files = []
    if MUSIC_DIR.exists():
        # Get all audio files (mp3, wav, ogg, m4a)
        audio_extensions = {'.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac'}
        local_music_files = [
            f for f in os.listdir(MUSIC_DIR)
            if Path(f).suffix.lower() in audio_extensions
        ]

    recommended_songs = []

    if local_music_files:
        # Shuffle and pick up to 5 local files
        random.shuffle(local_music_files)
        selected_files = local_music_files[:5]

        for i, filename in enumerate(selected_files):
            # Use filename without extension as title
            title = Path(filename).stem
            # Determine emotion_category based on index for variety, or use provided emotion_category
            categories = ["joy", "normal", "anxiety", "sadness", "calm"]
            song_emotion = categories[i % len(categories)]

            recommended_songs.append(Music(
                id=1000 + i,
                title=title,
                artist="本地音乐",
                url=f"/music/{filename}",
                duration=180,  # Default duration
                mood_tags=[song_emotion],
                emotion_category=song_emotion,
                is_active=1,
                cover_url=None
            ))
    else:
        # Fallback to database music
        query = db.query(Music).filter(Music.is_active == 1)
        music_list = query.all()
        matching_music = [m for m in music_list if m.emotion_category == emotion_category]

        if not matching_music:
            matching_music = music_list

        random.shuffle(matching_music)
        recommended_songs = matching_music[:5]

    emotion_messages = {
        "joy": "根据您愉悦的心情，为您推荐欢快的音乐",
        "normal": "根据您平静的心情，为您推荐轻柔的音乐",
        "anxiety": "根据您焦虑的心情，为您推荐舒缓的音乐",
        "sadness": "根据您低落的心情，为您推荐安慰的音乐",
        "calm": "根据您需要放松的心情，为您推荐放松的音乐"
    }

    return MusicRecommendResponse(
        current_emotion=emotion_category,
        recommended_songs=recommended_songs,
        message=emotion_messages.get(emotion_category, "为您推荐疗愈音乐")
    )


@router.get("/list")
async def list_music(
    emotion_category: str = None,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """获取音乐库列表"""
    query = db.query(Music).filter(Music.is_active == 1)

    if emotion_category:
        query = query.filter(Music.emotion_category == emotion_category)

    music_list = query.limit(limit).all()

    return {
        "total": len(music_list),
        "music_list": music_list
    }


@router.post("/seed")
async def seed_music_data(db: Session = Depends(get_db)):
    """初始化示例音乐数据"""
    # Check if data already exists
    existing = db.query(Music).first()
    if existing:
        return {"status": "already_seeded", "message": "音乐数据已存在"}

    sample_music = [
        # 愉悦音乐
        Music(
            title="Happy Rock",
            artist="Kevin MacLeod",
            url="https://incompetech.com/music/royalty-free/mp3-royaltyfree/Happy%20Rock.mp3",
            duration=113,
            mood_tags=["happy", "joy", "uplifting"],
            emotion_category="joy",
            cover_url=None
        ),
        Music(
            title="Carefree",
            artist="Kevin MacLeod",
            url="https://incompetech.com/music/royalty-free/mp3-royaltyfree/Carefree.mp3",
            duration=130,
            mood_tags=["happy", "joy", "relaxed"],
            emotion_category="joy",
            cover_url=None
        ),
        # 平静/舒缓音乐
        Music(
            title="Slow Sleep",
            artist="Kevin MacLeod",
            url="https://incompetech.com/music/royalty-free/mp3-royaltyfree/Slow%20Sleep.mp3",
            duration=270,
            mood_tags=["calm", "relaxed", "sleep"],
            emotion_category="normal",
            cover_url=None
        ),
        Music(
            title="Meditation",
            artist="Kevin MacLeod",
            url="https://incompetech.com/music/royalty-free/mp3-royaltyfree/Meditation%20imbo.mp3",
            duration=300,
            mood_tags=["calm", "meditation", "peaceful"],
            emotion_category="normal",
            cover_url=None
        ),
        # 焦虑缓解
        Music(
            title="Healing",
            artist="Kevin MacLeod",
            url="https://incompetech.com/music/royalty-free/mp3-royaltyfree/Healing.mp3",
            duration=180,
            mood_tags=["anxious", "healing", "relaxing"],
            emotion_category="anxiety",
            cover_url=None
        ),
        Music(
            title="Clear Waters",
            artist="Kevin MacLeod",
            url="https://incompetech.com/music/royalty-free/mp3-royaltyfree/Clear%20Waters.mp3",
            duration=240,
            mood_tags=["calm", "peaceful", "nature"],
            emotion_category="anxiety",
            cover_url=None
        ),
        # 情绪低落
        Music(
            title="Mysterious Mountains",
            artist="Kevin MacLeod",
            url="https://incompetech.com/music/royalty-free/mp3-royaltyfree/Mysterious%20Mountains.mp3",
            duration=185,
            mood_tags=["sad", "melancholy", "reflective"],
            emotion_category="sadness",
            cover_url=None
        ),
        Music(
            title="Sunny Morning",
            artist="Kevin MacLeod",
            url="https://incompetech.com/music/royalty-free/mp3-royaltyfree/Sunny.mp3",
            duration=160,
            mood_tags=["sad", "hopeful", "uplifting"],
            emotion_category="sadness",
            cover_url=None
        ),
    ]

    for music in sample_music:
        db.add(music)

    db.commit()

    return {"status": "success", "message": f"已添加{len(sample_music)}首示例音乐"}