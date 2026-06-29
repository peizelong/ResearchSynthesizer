import os
from pathlib import Path


def _load_env_file() -> None:
    """Load project .env values without overriding real environment variables."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


_load_env_file()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/research.db")

# LLM
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "qwen2.5")

# 抽取器
EXTRACTOR_MODEL = os.getenv("EXTRACTOR_MODEL", "deepseek")

# 叙事融合 - LLM 提供者（deepseek | ollama | demo）
# 默认跟随 EXTRACTOR_MODEL，避免抽取走 ollama/demo、融合又回落到 deepseek。
LLM_PROVIDER = os.getenv("LLM_PROVIDER", EXTRACTOR_MODEL)

# 主题聚类/融合/逻辑链等节点使用的 LLM（默认复用 DeepSeek 配置）
FUSION_LLM_MODEL = os.getenv("FUSION_LLM_MODEL", DEEPSEEK_MODEL)

# 数据目录
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
