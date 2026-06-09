import os
from dataclasses import dataclass
 
 
@dataclass
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "8951619112:AAFeihc9UtCxpx-jrGplUqU8t3IZEf8SmoM")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:fghXzTgMmGASQDAorSNAxaqIwLBWvJAX@acela.proxy.rlwy.net:29323/railway")
    
    # Admin IDs (vergul bilan ajratilgan)
    ADMIN_IDS: list = None
    
    def __post_init__(self):
        admin_ids_str = os.getenv("ADMIN_IDS", "")
        if admin_ids_str:
            self.ADMIN_IDS = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip()]
        else:
            self.ADMIN_IDS = []
 
 
config = Config()
