import os
from dotenv import load_dotenv

# Use absolute path so it works regardless of working directory
_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if os.path.exists(_env_path):
    load_dotenv(_env_path)


class Settings:
    def __init__(self):
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.deepseek_base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.deepseek_model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_port = int(os.getenv("DB_PORT", "3306"))
        self.db_user = os.getenv("DB_USER", "root")
        self.db_password = os.getenv("DB_PASSWORD", "")
        self.db_name = os.getenv("DB_NAME", "ai_learning_assistant")
        self.use_sqlite = os.getenv("USE_SQLITE", "false").lower() == "true"
        self.sqlite_path = os.getenv("SQLITE_PATH", "ai_learning.db")
        self.jwt_secret = os.getenv("JWT_SECRET", "default-secret")
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.jwt_expiration_hours = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
        self.server_host = os.getenv("SERVER_HOST", "0.0.0.0")
        self.server_port = int(os.getenv("SERVER_PORT", "8000"))
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        self.rag_max_distance = float(os.getenv("RAG_MAX_DISTANCE", "1.6"))

    @property
    def database_url(self) -> str:
        if self.use_sqlite:
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), self.sqlite_path)
            return f"sqlite:///{db_path}"
        return f"mysql+pymysql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"

settings = Settings()
