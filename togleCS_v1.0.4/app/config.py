from urllib.parse import quote_plus

DB_USER = "egenauto_admin"
DB_PASSWORD = quote_plus("Ea@!46941808")  # 인코딩 필수
DB_HOST = "localhost"
DB_PORT = "3306"
DB_NAME = "togle"

SQLALCHEMY_DATABASE_URI = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
)

SQLALCHEMY_TRACK_MODIFICATIONS = False
