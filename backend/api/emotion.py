"""
情绪分析 API 路由
Emotion Analysis API Routes
"""
import os
import tempfile
import base64
from typing import Optional, Dict, List
from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from pydantic import BaseModel
from loguru import logger

from services.sensevoice_analyzer import SenseVoiceAnalyzer
from services.emotion2vec_analyzer import Emotion2VecAnalyzer
from services.audio_preprocessor import AudioPreprocessor
from services.face_analyzer import FaceAnalyzer
from models.emotion import AudioAnalysisResult, SupportedLanguage, EmotionCategory, FacialExpression


router = APIRouter()

# 全局分析器实例（延迟初始化）
_sensevoice_analyzer: Optional[SenseVoiceAnalyzer] = None
_emotion2vec_analyzer: Optional[Emotion2VecAnalyzer] = None
_audio_preprocessor: Optional[AudioPreprocessor] = None
_face_analyzer: Optional[FaceAnalyzer] = None


def get_sensevoice_analyzer() -> SenseVoiceAnalyzer:
    """获取 SenseVoice 分析器实例"""
    global _sensevoice_analyzer
    if _sensevoice_analyzer is None:
        _sensevoice_analyzer = SenseVoiceAnalyzer(
            device="cpu"  # 默认使用 CPU，可配置为 "mps" 或 "cuda"
        )
    return _sensevoice_analyzer


def get_emotion2vec_analyzer() -> Emotion2VecAnalyzer:
    """获取 emotion2vec+ 分析器实例"""
    global _emotion2vec_analyzer
    if _emotion2vec_analyzer is None:
        _emotion2vec_analyzer = Emotion2VecAnalyzer(
            device="cpu"  # 默认使用 CPU，可配置为 "mps" 或 "cuda"
        )
    return _emotion2vec_analyzer


def get_audio_preprocessor() -> AudioPreprocessor:
    """获取音频预处理器实例"""
    global _audio_preprocessor
    if _audio_preprocessor is None:
        _audio_preprocessor = AudioPreprocessor()
    return _audio_preprocessor


def get_face_analyzer() -> FaceAnalyzer:
    """获取面部分析器实例"""
    global _face_analyzer
    if _face_analyzer is None:
        _face_analyzer = FaceAnalyzer()
    return _face_analyzer


class AudioAnalysisResponse(BaseModel):
    """音频分析响应模型"""
    text: str
    language: str
    emotion: str
    event: str
    confidence: float
    duration_ms: int
    is_valid: bool


class Emotion2VecResponse(BaseModel):
    """emotion2vec+ 分析响应模型"""
    emotion: str
    scores: Dict[str, float]
    intensity: float
    valence: float
    arousal: float


class CombinedAudioAnalysisResponse(BaseModel):
    """综合音频分析响应模型（SenseVoice + emotion2vec+）"""
    # SenseVoice 结果
    text: str
    language: str
    sensevoice_emotion: str
    event: str
    confidence: float
    duration_ms: int
    # emotion2vec+ 结果
    emotion2vec_emotion: str
    emotion_scores: Dict[str, float]
    intensity: float
    valence: float
    arousal: float


class FaceAnalysisResponse(BaseModel):
    """面部分析响应模型"""
    detected: bool
    expression: str
    confidence: float
    expression_scores: Dict[str, float]
    face_bbox: Optional[List[int]] = None
    valence: float
    arousal: float


class EmotionEngineStatus(BaseModel):
    """情绪引擎状态响应"""
    status: str
    sensevoice_initialized: bool
    emotion2vec_initialized: bool
    face_analyzer_initialized: bool
    supported_languages: list
    sensevoice_emotion_labels: list
    emotion2vec_emotion_labels: list
    face_expression_labels: list
    audio_events: list


@router.get("/", response_model=EmotionEngineStatus)
async def get_emotion_status():
    """获取情绪分析引擎状态"""
    sensevoice = get_sensevoice_analyzer()
    emotion2vec = get_emotion2vec_analyzer()
    face_analyzer = get_face_analyzer()
    return EmotionEngineStatus(
        status="ready",
        sensevoice_initialized=sensevoice.is_initialized(),
        emotion2vec_initialized=emotion2vec.is_initialized(),
        face_analyzer_initialized=face_analyzer.is_initialized(),
        supported_languages=sensevoice.get_supported_languages(),
        sensevoice_emotion_labels=sensevoice.get_emotion_labels(),
        emotion2vec_emotion_labels=emotion2vec.get_emotion_labels(),
        face_expression_labels=face_analyzer.get_expression_labels(),
        audio_events=sensevoice.get_audio_events()
    )


@router.post("/analyze/audio", response_model=AudioAnalysisResponse)
async def analyze_audio(
    audio: UploadFile = File(...),
    language: str = Form(default="auto")
):
    """
    分析音频情绪
    
    - **audio**: 音频文件 (支持 wav, mp3, flac, ogg, m4a)
    - **language**: 语言代码 (auto, zh, en, yue, ja, ko)
    
    返回:
    - text: 识别的文本内容
    - language: 检测到的语言
    - emotion: 情感标签
    - event: 音频事件
    - confidence: 置信度
    - duration_ms: 音频时长
    """
    # 验证语言参数
    valid_languages = ["auto", "zh", "en", "yue", "ja", "ko"]
    if language not in valid_languages:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid language. Must be one of: {valid_languages}"
        )
    
    # 验证文件类型
    preprocessor = get_audio_preprocessor()
    filename = audio.filename or "audio.wav"
    if not preprocessor.is_supported_format(filename):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format. Supported: {preprocessor.SUPPORTED_FORMATS}"
        )
    
    # 保存上传的文件到临时目录
    temp_file = None
    try:
        suffix = os.path.splitext(filename)[1] or ".wav"
        temp_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        content = await audio.read()
        temp_file.write(content)
        temp_file.close()
        
        # 分析音频
        analyzer = get_sensevoice_analyzer()
        result = await analyzer.analyze(temp_file.name, language=language)
        
        return AudioAnalysisResponse(
            text=result.text,
            language=result.language,
            emotion=result.emotion,
            event=result.event,
            confidence=result.confidence,
            duration_ms=result.duration_ms,
            is_valid=result.is_valid()
        )
        
    except FileNotFoundError as e:
        logger.error(f"Audio file not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        logger.error(f"SenseVoice runtime error: {e}")
        raise HTTPException(status_code=503, detail=f"Model not available: {e}")
    except Exception as e:
        logger.error(f"Audio analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")
    finally:
        # 清理临时文件
        if temp_file and os.path.exists(temp_file.name):
            try:
                os.unlink(temp_file.name)
            except Exception as e:
                logger.warning(f"Failed to delete temp file: {e}")


@router.post("/initialize")
async def initialize_models():
    """
    初始化情绪分析模型
    
    在首次使用前调用此接口预加载模型，避免首次分析时的延迟
    """
    results = {}
    
    try:
        # 初始化 SenseVoice
        sensevoice = get_sensevoice_analyzer()
        sensevoice_success = sensevoice.initialize()
        results["sensevoice"] = "initialized" if sensevoice_success else "failed"
    except Exception as e:
        logger.error(f"SenseVoice initialization failed: {e}")
        results["sensevoice"] = f"error: {e}"
    
    try:
        # 初始化 emotion2vec+
        emotion2vec = get_emotion2vec_analyzer()
        emotion2vec_success = emotion2vec.initialize()
        results["emotion2vec"] = "initialized" if emotion2vec_success else "failed"
    except Exception as e:
        logger.error(f"emotion2vec+ initialization failed: {e}")
        results["emotion2vec"] = f"error: {e}"
    
    try:
        # 初始化 Face Analyzer
        face_analyzer = get_face_analyzer()
        face_success = face_analyzer.initialize()
        results["face_analyzer"] = "initialized" if face_success else "failed"
    except Exception as e:
        logger.error(f"Face analyzer initialization failed: {e}")
        results["face_analyzer"] = f"error: {e}"
    
    all_success = all(v == "initialized" for v in results.values())
    
    return {
        "status": "initialized" if all_success else "partial",
        "models": results,
        "message": "All models loaded successfully" if all_success else "Some models failed to load"
    }


@router.post("/analyze/emotion2vec", response_model=Emotion2VecResponse)
async def analyze_emotion2vec(
    audio: UploadFile = File(...)
):
    """
    使用 emotion2vec+ 分析音频情绪（9类细粒度情绪）
    
    - **audio**: 音频文件 (支持 wav, mp3, flac, ogg, m4a)
    
    返回:
    - emotion: 主要情绪类别 (9类之一)
    - scores: 各情绪的置信度分数
    - intensity: 情绪强度 (0-1)
    - valence: 效价 (-1 到 1)
    - arousal: 唤醒度 (0 到 1)
    """
    # 验证文件类型
    preprocessor = get_audio_preprocessor()
    filename = audio.filename or "audio.wav"
    if not preprocessor.is_supported_format(filename):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format. Supported: {preprocessor.SUPPORTED_FORMATS}"
        )
    
    # 保存上传的文件到临时目录
    temp_file = None
    try:
        suffix = os.path.splitext(filename)[1] or ".wav"
        temp_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        content = await audio.read()
        temp_file.write(content)
        temp_file.close()
        
        # 分析音频
        analyzer = get_emotion2vec_analyzer()
        result = await analyzer.analyze(temp_file.name)
        
        return Emotion2VecResponse(
            emotion=result.emotion.value,
            scores=result.scores,
            intensity=result.intensity,
            valence=analyzer.get_valence(result.emotion.value),
            arousal=analyzer.get_arousal(result.emotion.value)
        )
        
    except FileNotFoundError as e:
        logger.error(f"Audio file not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        logger.error(f"emotion2vec+ runtime error: {e}")
        raise HTTPException(status_code=503, detail=f"Model not available: {e}")
    except Exception as e:
        logger.error(f"emotion2vec+ analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")
    finally:
        # 清理临时文件
        if temp_file and os.path.exists(temp_file.name):
            try:
                os.unlink(temp_file.name)
            except Exception as e:
                logger.warning(f"Failed to delete temp file: {e}")


@router.post("/analyze/combined", response_model=CombinedAudioAnalysisResponse)
async def analyze_combined(
    audio: UploadFile = File(...),
    language: str = Form(default="auto")
):
    """
    综合音频分析（SenseVoice + emotion2vec+）
    
    同时使用 SenseVoice 进行语音识别和 emotion2vec+ 进行细粒度情绪分析
    
    - **audio**: 音频文件 (支持 wav, mp3, flac, ogg, m4a)
    - **language**: 语言代码 (auto, zh, en, yue, ja, ko)
    
    返回综合分析结果
    """
    # 验证语言参数
    valid_languages = ["auto", "zh", "en", "yue", "ja", "ko"]
    if language not in valid_languages:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid language. Must be one of: {valid_languages}"
        )
    
    # 验证文件类型
    preprocessor = get_audio_preprocessor()
    filename = audio.filename or "audio.wav"
    if not preprocessor.is_supported_format(filename):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format. Supported: {preprocessor.SUPPORTED_FORMATS}"
        )
    
    # 保存上传的文件到临时目录
    temp_file = None
    try:
        suffix = os.path.splitext(filename)[1] or ".wav"
        temp_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        content = await audio.read()
        temp_file.write(content)
        temp_file.close()
        
        # SenseVoice 分析
        sensevoice = get_sensevoice_analyzer()
        sv_result = await sensevoice.analyze(temp_file.name, language=language)
        
        # emotion2vec+ 分析
        emotion2vec = get_emotion2vec_analyzer()
        e2v_result = await emotion2vec.analyze(temp_file.name)
        
        return CombinedAudioAnalysisResponse(
            # SenseVoice 结果
            text=sv_result.text,
            language=sv_result.language,
            sensevoice_emotion=sv_result.emotion,
            event=sv_result.event,
            confidence=sv_result.confidence,
            duration_ms=sv_result.duration_ms,
            # emotion2vec+ 结果
            emotion2vec_emotion=e2v_result.emotion.value,
            emotion_scores=e2v_result.scores,
            intensity=e2v_result.intensity,
            valence=emotion2vec.get_valence(e2v_result.emotion.value),
            arousal=emotion2vec.get_arousal(e2v_result.emotion.value)
        )
        
    except FileNotFoundError as e:
        logger.error(f"Audio file not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        logger.error(f"Model runtime error: {e}")
        raise HTTPException(status_code=503, detail=f"Model not available: {e}")
    except Exception as e:
        logger.error(f"Combined analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")
    finally:
        # 清理临时文件
        if temp_file and os.path.exists(temp_file.name):
            try:
                os.unlink(temp_file.name)
            except Exception as e:
                logger.warning(f"Failed to delete temp file: {e}")


@router.post("/analyze/face", response_model=FaceAnalysisResponse)
async def analyze_face(
    image: UploadFile = File(...)
):
    """
    分析面部表情
    
    - **image**: 图像文件 (支持 jpg, jpeg, png, bmp)
    
    返回:
    - detected: 是否检测到人脸
    - expression: 表情类别 (7类之一)
    - confidence: 置信度 (0-1)
    - expression_scores: 各表情的置信度分数
    - face_bbox: 人脸边界框 [x, y, width, height]
    - valence: 效价 (-1 到 1)
    - arousal: 唤醒度 (0 到 1)
    """
    import cv2
    import numpy as np
    
    # 验证文件类型
    supported_formats = {'.jpg', '.jpeg', '.png', '.bmp'}
    filename = image.filename or "image.jpg"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in supported_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image format. Supported: {supported_formats}"
        )
    
    # 读取图像数据
    temp_file = None
    try:
        # 保存上传的文件到临时目录
        temp_file = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
        content = await image.read()
        temp_file.write(content)
        temp_file.close()
        
        # 读取图像
        frame = cv2.imread(temp_file.name)
        if frame is None:
            raise HTTPException(status_code=400, detail="Failed to read image file")
        
        # 分析面部
        analyzer = get_face_analyzer()
        result = await analyzer.analyze(frame)
        
        return FaceAnalysisResponse(
            detected=result.detected,
            expression=result.expression.value,
            confidence=result.confidence,
            expression_scores=result.expression_scores,
            face_bbox=list(result.face_bbox) if result.face_bbox else None,
            valence=analyzer.get_valence(result.expression.value),
            arousal=analyzer.get_arousal(result.expression.value)
        )
        
    except HTTPException:
        raise
    except RuntimeError as e:
        logger.error(f"Face analyzer runtime error: {e}")
        raise HTTPException(status_code=503, detail=f"Face analyzer not available: {e}")
    except Exception as e:
        logger.error(f"Face analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")
    finally:
        # 清理临时文件
        if temp_file and os.path.exists(temp_file.name):
            try:
                os.unlink(temp_file.name)
            except Exception as e:
                logger.warning(f"Failed to delete temp file: {e}")


@router.post("/analyze/face/base64", response_model=FaceAnalysisResponse)
async def analyze_face_base64(
    image_data: str = Form(...)
):
    """
    分析 Base64 编码的图像中的面部表情
    
    - **image_data**: Base64 编码的图像数据
    
    返回与 /analyze/face 相同的结果
    """
    import cv2
    import numpy as np
    
    try:
        # 解码 Base64 图像
        # 移除可能的 data URL 前缀
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        image_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            raise HTTPException(status_code=400, detail="Failed to decode image data")
        
        # 分析面部
        analyzer = get_face_analyzer()
        result = await analyzer.analyze(frame)
        
        return FaceAnalysisResponse(
            detected=result.detected,
            expression=result.expression.value,
            confidence=result.confidence,
            expression_scores=result.expression_scores,
            face_bbox=list(result.face_bbox) if result.face_bbox else None,
            valence=analyzer.get_valence(result.expression.value),
            arousal=analyzer.get_arousal(result.expression.value)
        )
        
    except HTTPException:
        raise
    except RuntimeError as e:
        logger.error(f"Face analyzer runtime error: {e}")
        raise HTTPException(status_code=503, detail=f"Face analyzer not available: {e}")
    except Exception as e:
        logger.error(f"Face analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")


class BioAnalysisRequest(BaseModel):
    """生理信号分析请求"""
    rr_intervals: List[int] = []  # RR 间期列表 (ms)
    heart_rate: Optional[float] = None  # 当前心率 (bpm)


class BioAnalysisResponse(BaseModel):
    """生理信号分析响应"""
    is_valid: bool
    stress_index: float
    stress_level: str
    heart_rate: float
    heart_rate_status: str
    hrv_metrics: Optional[Dict[str, float]] = None
    message: str = ""


class EmotionFuseRequest(BaseModel):
    """多模态情绪融合请求"""
    # 语音情绪（emotion2vec 结果）
    audio_emotion: Optional[str] = None
    audio_scores: Optional[Dict[str, float]] = None
    audio_intensity: Optional[float] = None
    # 面部表情
    face_expression: Optional[str] = None
    face_scores: Optional[Dict[str, float]] = None
    face_confidence: Optional[float] = None
    face_detected: Optional[bool] = None
    # 生理信号
    bio_stress_index: Optional[float] = None
    bio_is_valid: Optional[bool] = None
    bio_heart_rate: Optional[float] = None


class EmotionFuseResponse(BaseModel):
    """多模态情绪融合响应"""
    category: str
    intensity: float
    valence: float
    arousal: float
    confidence: float
    fusion_mode: str
    conflict_detected: bool
    conflict_resolution: Optional[str] = None
    modality_contributions: Dict[str, float]


@router.post("/analyze/bio", response_model=BioAnalysisResponse)
async def analyze_bio(request: BioAnalysisRequest):
    """
    分析生理信号（HRV 心率变异性）

    - **rr_intervals**: RR 间期列表 (ms)，至少需要 30 个数据点
    - **heart_rate**: 当前心率 (bpm)，可选

    返回压力指数、HRV 指标等
    """
    from services.hrv_analyzer import HRVAnalyzer, BioAnalysisResult

    try:
        analyzer = HRVAnalyzer()

        # 如果没有提供 RR 间期数据
        if not request.rr_intervals:
            result = BioAnalysisResult.insufficient_data("未提供 RR 间期数据")
            return BioAnalysisResponse(
                is_valid=False,
                stress_index=result.stress_index,
                stress_level=result.stress_level,
                heart_rate=request.heart_rate or 0.0,
                heart_rate_status="unknown",
                message=result.message
            )

        # 分析 HRV
        hrv_metrics = analyzer.analyze(request.rr_intervals)

        if hrv_metrics is None:
            result = BioAnalysisResult.insufficient_data("数据不足，无法计算 HRV")
            return BioAnalysisResponse(
                is_valid=False,
                stress_index=result.stress_index,
                stress_level=result.stress_level,
                heart_rate=request.heart_rate or 0.0,
                heart_rate_status="unknown",
                message=result.message
            )

        # 检查心率状态
        hr = request.heart_rate or hrv_metrics.mean_hr
        is_abnormal, hr_status = analyzer.is_heart_rate_abnormal(hr)
        stress_level = analyzer.get_stress_level(hrv_metrics.stress_index)

        return BioAnalysisResponse(
            is_valid=True,
            stress_index=round(hrv_metrics.stress_index, 2),
            stress_level=stress_level,
            heart_rate=round(hr, 1),
            heart_rate_status=hr_status,
            hrv_metrics={
                "rmssd": round(hrv_metrics.rmssd, 2),
                "sdnn": round(hrv_metrics.sdnn, 2),
                "mean_rr": round(hrv_metrics.mean_rr, 2),
                "mean_hr": round(hrv_metrics.mean_hr, 2),
                "nn50": hrv_metrics.nn50,
                "pnn50": round(hrv_metrics.pnn50, 2),
                "sample_count": hrv_metrics.sample_count,
                "duration_seconds": round(hrv_metrics.duration_seconds, 1),
            },
            message="HRV 分析完成"
        )

    except Exception as e:
        logger.error(f"生理信号分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"生理信号分析失败: {e}")


@router.post("/fuse", response_model=EmotionFuseResponse)
async def fuse_emotions(request: EmotionFuseRequest):
    """
    多模态情绪融合

    融合语音、面部、生理信号三种模态的情绪数据，
    支持冲突检测和单模态降级。

    至少需要提供一种模态的数据。
    """
    from services.emotion_fusion import EmotionFusion
    from services.hrv_analyzer import BioAnalysisResult, HRVMetrics

    try:
        fusion = EmotionFusion()

        # 构建语音情绪结果
        audio_result = None
        if request.audio_emotion and request.audio_scores:
            from models.emotion import Emotion2VecResult
            try:
                audio_result = Emotion2VecResult(
                    emotion=EmotionCategory(request.audio_emotion),
                    scores=request.audio_scores,
                    intensity=request.audio_intensity or 0.5
                )
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"无效的语音情绪类别: {request.audio_emotion}"
                )

        # 构建面部表情结果
        face_result = None
        if request.face_expression and request.face_scores:
            from models.emotion import FaceAnalysisResult, FacialExpression
            try:
                face_result = FaceAnalysisResult(
                    detected=request.face_detected if request.face_detected is not None else True,
                    expression=FacialExpression(request.face_expression),
                    confidence=request.face_confidence or 0.8,
                    expression_scores=request.face_scores
                )
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"无效的面部表情类别: {request.face_expression}"
                )

        # 构建生理信号结果
        bio_result = None
        if request.bio_stress_index is not None:
            from services.hrv_analyzer import HRVAnalyzer
            analyzer = HRVAnalyzer()
            stress_level = analyzer.get_stress_level(request.bio_stress_index)
            hr = request.bio_heart_rate or 75.0
            is_abnormal, hr_status = analyzer.is_heart_rate_abnormal(hr)
            bio_result = BioAnalysisResult(
                stress_index=request.bio_stress_index,
                stress_level=stress_level,
                hrv_metrics=None,
                heart_rate=hr,
                heart_rate_status=hr_status,
                is_valid=request.bio_is_valid if request.bio_is_valid is not None else True
            )

        # 检查是否至少有一种模态数据
        if audio_result is None and face_result is None and bio_result is None:
            raise HTTPException(
                status_code=400,
                detail="至少需要提供一种模态的情绪数据"
            )

        # 执行融合
        result = fusion.fuse(
            audio_result=audio_result,
            face_result=face_result,
            bio_result=bio_result
        )

        return EmotionFuseResponse(
            category=result.emotion_state.category.value,
            intensity=round(result.emotion_state.intensity, 3),
            valence=round(result.emotion_state.valence, 3),
            arousal=round(result.emotion_state.arousal, 3),
            confidence=round(result.emotion_state.confidence, 3),
            fusion_mode=result.fusion_mode.value,
            conflict_detected=result.conflict_detected,
            conflict_resolution=result.conflict_resolution,
            modality_contributions=result.modality_contributions
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"情绪融合失败: {e}")
        raise HTTPException(status_code=500, detail=f"情绪融合失败: {e}")
