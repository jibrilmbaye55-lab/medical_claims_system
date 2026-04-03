import os


class Config:
    # 🔐 clé secrète Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "coud_medical_secure_2026")

    # 🗄️ base SQLite locale / en ligne
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///medical_claims.db"
    )

    # ⚡ optimisation SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False