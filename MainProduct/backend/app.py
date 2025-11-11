"""
Flask 애플리케이션 메인 파일
"""
from flask import Flask
from flask_cors import CORS
from config import Config
from api import api_bp


def create_app():
    """Flask 애플리케이션 팩토리"""
    app = Flask(__name__)
    
    # 설정 로드
    app.config.from_object(Config)
    
    # CORS 설정 (React 프론트엔드와 통신)
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:3000", "http://localhost:5173"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type"]
        }
    })
    
    # Blueprint 등록
    app.register_blueprint(api_bp)
    
    return app


# Gunicorn이 사용할 수 있도록 app 객체를 모듈 레벨에서 생성
app = create_app()


if __name__ == "__main__":
    # API 키 확인 경고
    if not Config.TMDB_API_KEY:
        print("[경고] TMDB_API_KEY가 .env에 없습니다. TMDb 요청이 실패할 수 있습니다.")
    
    if not Config.OMDB_API_KEY:
        print("[알림] OMDB_API_KEY가 .env에 없습니다. OMDb 추가 정보를 가져올 수 없습니다.")
    
    # 서버 실행 (이미 생성된 app 사용)
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )
