import os
from pathlib import Path
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseModel):
    PROJECT_NAME: str = "考研英语智能学习系统"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/kaoyan_learning.db")
    
    # Vocabulary Database resolution: env var -> repo bundled -> desktop fallback
    VOCAB_DB_PATH: str = os.getenv(
        "VOCAB_DB_PATH",
        str(BASE_DIR / "app" / "data" / "kaoyan_vocab.db")
    )
    DESKTOP_VOCAB_DB: str = os.getenv(
        "DESKTOP_VOCAB_DB",
        r"C:\Users\Administrator\Desktop\KaoyanVocab\data\kaoyan_vocab.db"
    )
    
    # AI Analysis Model Settings
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "rule_evidence_engine")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    AI_MODEL_NAME: str = os.getenv("AI_MODEL_NAME", "deepseek-v3")
    
    # FSRS default parameters (FSRS v4.5 standard weights)
    FSRS_W: list[float] = Field(default_factory=lambda: [
        0.4072, 1.1829, 3.1262, 15.4722, 7.2102, 0.5316, 1.0651, 0.0234,
        1.616, 0.1544, 1.0824, 1.9813, 0.0953, 0.2975, 2.2042, 0.2407, 2.9466, 0.5034, 0.6567
    ])
    FSRS_REQUEST_RETENTION: float = 0.90
    FSRS_MAXIMUM_INTERVAL: int = 36500

settings = Settings()
