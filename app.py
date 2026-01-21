from flask import Flask, render_template_string, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime

app = Flask(__name__)

# Конфигурация для Render
if 'RENDER' in os.environ:
    # На Render
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'render-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL').replace("postgres://", "postgresql://", 1)
    app.config['UPLOAD_FOLDER'] = '/opt/render/project/src/static/videos'
else:
    # Локально
    app.config['SECRET_KEY'] = 'local-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pixtube.db'
    app.config['UPLOAD_FOLDER'] = 'static/videos'

# Создаем папку для видео если её нет
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# Модели
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password_hash = db.Column(db.String(200))
    is_admin = db.Column(db.Boolean, default=False)
    is_banned = db.Column(db.Boolean, default=False)

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    filename = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    views = db.Column(db.Integer, default=0)
    is_blocked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    author = db.relationship('User', backref='videos')

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'))
    is_blocked = db.Column(db.Boolean, default=False)
    author = db.relationship('User', backref='comments')
    video = db.relationship('Video', backref='comments')

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'))
    is_like = db.Column(db.Boolean, default=True)

# Создаем базу и админа
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            password_hash=generate_password_hash('admin'),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()

# Хелперы
def current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

def is_admin():
    user = current_user()
    return user and user.is_admin

# Главная
@app.route('/')
def index():
    videos = Video.query.filter_by(is_blocked=False).all()
    user = current_user()
    
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Pixtube - Видеохостинг</title>
    <style>
        /* Основные стили */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        body {
            background-color: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 15px;
        }
        
        /* Шапка */
        header {
            background: linear-gradient(135deg, #ff0000, #cc0000);
            color: white;
            padding: 1rem 0;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            position: sticky;
            top: 0;
            z-index: 100;
        }
        
        .header-content {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .logo {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 1.8rem;
            font-weight: bold;
        }
        
        .logo i {
            color: white;
        }
        
        .nav-links {
            display: flex;
            gap: 20px;
            align-items: center;
        }
        
        .nav-links a {
            color: white;
            text-decoration: none;
            padding: 8px 15px;
            border-radius: 5px;
            transition: all 0.3s ease;
            font-weight: 500;
        }
        
        .nav-links a:hover {
            background-color: rgba(255, 255, 255, 0.2);
        }
        
        .nav-links .admin-btn {
            background-color: #ff3333;
            color: white;
        }
        
        .user-info {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .username {
            font-weight: 600;
        }
        
        /* Основной контент */
        .main-content {
            padding: 2rem 0;
        }
        
        .welcome-section {
            background: linear-gradient(135deg, #4285f4, #34a853);
            color: white;
            padding: 2rem;
            border-radius: 10px;
            margin-bottom: 2rem;
            text-align: center;
        }
        
        .welcome-section h1 {
            font-size: 2.5rem;
            margin-bottom: 1rem;
        }
        
        .welcome-section p {
            font-size: 1.2rem;
            opacity: 0.9;
        }
        
        /* Видео грид */
        .video-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 25px;
            margin-top: 2rem;
        }
        
        .video-card {
            background-color: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);
            transition: all 0.3s ease;
            cursor: pointer;
        }
        
        .video-card:hover {
            transform: translateY(-10px);
            box-shadow: 0 15px 30px rgba(0, 0, 0, 0.15);
        }
        
        .video-thumbnail {
            width: 100%;
            height: 160px;
            background-color: #e0e0e0;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #666;
            position: relative;
        }
        
        .video-thumbnail i {
            font-size: 3rem;
            color: #ff0000;
        }
        
        .video-info {
            padding: 15px;
        }
        
        .video-title {
            font-weight: 600;
            font-size: 1.1rem;
            margin-bottom: 10px;
            color: #333;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }
        
        .video-author {
            color: #666;
            font-size: 0.9rem;
            margin-bottom: 5px;
        }
        
        .video-stats {
            display: flex;
            justify-content: space-between;
            color: #888;
            font-size: 0.85rem;
        }
        
        .banned-badge {
            background-color: #ff3333;
            color: white;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 0.8rem;
            display: inline-block;
            margin-top: 5px;
        }
        
        /* Формы */
        .auth-container {
            max-width: 400px;
            margin: 50px auto;
            padding: 30px;
            background-color: white;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        }
        
        .auth-container h2 {
            text-align: center;
            margin-bottom: 25px;
            color: #ff0000;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            color: #555;
        }
        
        .form-control {
            width: 100%;
            padding: 12px 15px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 1rem;
            transition: border 0.3s;
        }
        
        .form-control:focus {
            outline: none;
            border-color: #ff0000;
        }
        
        .btn {
            display: inline-block;
            background-color: #ff0000;
            color: white;
            padding: 12px 25px;
            border: none;
            border-radius: 5px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-align: center;
            text-decoration: none;
        }
        
        .btn:hover {
            background-color: #cc0000;
            transform: translateY(-2px);
        }
        
        .btn-block {
            width: 100%;
        }
        
        .btn-secondary {
            background-color: #4285f4;
        }
        
        .btn-secondary:hover {
            background-color: #3367d6;
        }
        
        .back-link {
            display: inline-block;
            margin-top: 15px;
            color: #666;
            text-decoration: none;
        }
        
        .back-link:hover {
            color: #ff0000;
        }
        
        /* Страница видео */
        .video-page {
            padding: 2rem 0;
        }
        
        .video-player-container {
            background-color: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);
            margin-bottom: 2rem;
        }
        
        video {
            width: 100%;
            border-radius: 5px;
        }
        
        .video-meta {
            margin-top: 20px;
        }
        
        .video-meta h1 {
            font-size: 1.8rem;
            margin-bottom: 10px;
            color: #333;
        }
        
        .video-author-info {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 15px;
        }
        
        .video-stats-bar {
            display: flex;
            gap: 20px;
            color: #666;
            font-size: 0.9rem;
        }
        
        /* Комментарии */
        .comments-section {
            background-color: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);
        }
        
        .comments-section h3 {
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid #eee;
        }
        
        .comment-form textarea {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 5px;
            resize: vertical;
            min-height: 80px;
            margin-bottom: 15px;
        }
        
        .comment {
            padding: 15px;
            border-bottom: 1px solid #f0f0f0;
        }
        
        .comment:last-child {
            border-bottom: none;
        }
        
        .comment-author {
            font-weight: 600;
            color: #333;
            margin-bottom: 5px;
        }
        
        .comment-content {
            color: #555;
            line-height: 1.5;
        }
        
        .comment-actions {
            margin-top: 10px;
            font-size: 0.85rem;
        }
        
        .comment-actions a {
            color: #ff0000;
            text-decoration: none;
        }
        
        /* Админ панель */
        .admin-panel {
            padding: 2rem 0;
        }
        
        .admin-section {
            background-color: white;
            border-radius: 10px;
            padding: 25px;
            margin-bottom: 2rem;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);
        }
        
        .admin-section h2 {
            color: #ff0000;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #f0f0f0;
        }
        
        .admin-table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .admin-table th {
            background-color: #f8f8f8;
            padding: 12px 15px;
            text-align: left;
            font-weight: 600;
            color: #333;
            border-bottom: 2px solid #eee;
        }
        
        .admin-table td {
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
            vertical-align: top;
        }
        
        .admin-table tr:hover {
            background-color: #f9f9f9;
        }
        
        .admin-table .banned {
            background-color: #ffebee;
        }
        
        .action-buttons {
            display: flex;
            gap: 10px;
        }
        
        .action-btn {
            padding: 5px 10px;
            border-radius: 3px;
            font-size: 0.85rem;
            text-decoration: none;
            font-weight: 500;
        }
        
        .action-btn.ban {
            background-color: #ff3333;
            color: white;
        }
        
        .action-btn.unban {
            background-color: #34a853;
            color: white;
        }
        
        .action-btn.block {
            background-color: #ff9800;
            color: white;
        }
        
        .action-btn.view {
            background-color: #4285f4;
            color: white;
        }
        
        /* Футер */
        footer {
            background-color: #333;
            color: white;
            padding: 2rem 0;
            margin-top: 3rem;
        }
        
        .footer-content {
            text-align: center;
        }
        
        /* Адаптивность */
        @media (max-width: 768px) {
            .header-content {
                flex-direction: column;
                gap: 15px;
            }
            
            .nav-links {
                flex-wrap: wrap;
                justify-content: center;
            }
            
            .video-grid {
                grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            }
            
            .admin-table {
                display: block;
                overflow-x: auto;
            }
        }
        
        /* Утилиты */
        .text-center {
            text-align: center;
        }
        
        .mt-2 {
            margin-top: 2rem;
        }
        
        .mb-2 {
            margin-bottom: 2rem;
        }
    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body>
    <header>
        <div class="container">
            <div class="header-content">
                <div class="logo">
                    <i class="fab fa-youtube"></i>
                    <span>Pixtube</span>
                </div>
                
                <div class="nav-links">
                    {% if user %}
                        <div class="user-info">
                            <span class="username">{{ user.username }}</span>
                            <a href="/upload" class="btn">Загрузить видео</a>
                            {% if user.is_admin %}
                                <a href="/admin" class="btn admin-btn"><i class="fas fa-crown"></i> Админка</a>
                            {% endif %}
                            <a href="/logout" class="btn btn-secondary">Выйти</a>
                        </div>
                    {% else %}
                        <a href="/login" class="btn">Войти</a>
                        <a href="/register" class="btn btn-secondary">Регистрация</a>
                    {% endif %}
                </div>
            </div>
        </div>
    </header>
    
    <div class="container">
        <div class="main-content">
            {% if not user %}
            <div class="welcome-section">
                <h1>Добро пожаловать на Pixtube!</h1>
                <p>Смотрите, загружайте и делитесь видео с сообществом</p>
            </div>
            {% endif %}
            
            <h2>Популярные видео:</h2>
            <div class="video-grid">
                {% for video in videos %}
                <a href="/video/{{ video.id }}" style="text-decoration: none;">
                    <div class="video-card">
                        <div class="video-thumbnail">
                            <i class="fas fa-play-circle"></i>
                        </div>
                        <div class="video-info">
                            <h3 class="video-title">{{ video.title }}</h3>
                            <p class="video-author">{{ video.author.username }}</p>
                            <div class="video-stats">
                                <span><i class="fas fa-eye"></i> {{ video.views }}</span>
                                <span><i class="far fa-clock"></i> {{ video.created_at.strftime('%d.%m.%Y') }}</span>
                            </div>
                            {% if video.author.is_banned %}
                            <div class="banned-badge">
                                <i class="fas fa-ban"></i> Канал забанен
                            </div>
                            {% endif %}
                        </div>
                    </div>
                </a>
                {% endfor %}
            </div>
            
            {% if videos|length == 0 %}
            <div class="text-center mt-2">
                <p style="font-size: 1.2rem; color: #666;">Пока нет видео. Будьте первым, кто загрузит видео!</p>
                {% if user %}
                <a href="/upload" class="btn mt-2">Загрузить первое видео</a>
                {% endif %}
            </div>
            {% endif %}
        </div>
    </div>
    
    <footer>
        <div class="container">
            <div class="footer-content">
                <p>© 2023 Pixtube. Все права защищены.</p>
                <p>Платформа для обмена видео</p>
            </div>
        </div>
    </footer>
</body>
</html>
    ''', videos=videos, user=user)

# Регистрация
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            return '''
            <div class="container">
                <div class="auth-container">
                    <h2>Регистрация</h2>
                    <p style="color: red; text-align: center; margin-bottom: 20px;">Имя пользователя уже занято</p>
                    <form method="POST">
                        <div class="form-group">
                            <label for="username">Имя пользователя</label>
                            <input type="text" id="username" name="username" class="form-control" placeholder="Введите имя" required>
                        </div>
                        <div class="form-group">
                            <label for="password">Пароль</label>
                            <input type="password" id="password" name="password" class="form-control" placeholder="Введите пароль" required>
                        </div>
                        <button type="submit" class="btn btn-block">Зарегистрироваться</button>
                    </form>
                    <a href="/" class="back-link"><i class="fas fa-arrow-left"></i> На главную</a>
                </div>
            </div>
            '''
        
        user = User(
            username=username,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        
        session['user_id'] = user.id
        return redirect('/')
    
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Регистрация - Pixtube</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            
            body {
                background-color: #f5f5f5;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
            }
            
            .auth-container {
                width: 100%;
                max-width: 400px;
                padding: 30px;
                background-color: white;
                border-radius: 10px;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            }
            
            .auth-container h2 {
                text-align: center;
                margin-bottom: 25px;
                color: #ff0000;
            }
            
            .form-group {
                margin-bottom: 20px;
            }
            
            .form-group label {
                display: block;
                margin-bottom: 8px;
                font-weight: 500;
                color: #555;
            }
            
            .form-control {
                width: 100%;
                padding: 12px 15px;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-size: 1rem;
                transition: border 0.3s;
            }
            
            .form-control:focus {
                outline: none;
                border-color: #ff0000;
            }
            
            .btn {
                display: inline-block;
                background-color: #ff0000;
                color: white;
                padding: 12px 25px;
                border: none;
                border-radius: 5px;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                text-align: center;
                text-decoration: none;
                width: 100%;
            }
            
            .btn:hover {
                background-color: #cc0000;
                transform: translateY(-2px);
            }
            
            .back-link {
                display: block;
                margin-top: 15px;
                color: #666;
                text-decoration: none;
                text-align: center;
            }
            
            .back-link:hover {
                color: #ff0000;
            }
            
            .logo {
                text-align: center;
                margin-bottom: 20px;
                color: #ff0000;
                font-size: 1.5rem;
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        <div class="auth-container">
            <div class="logo">
                <i class="fab fa-youtube"></i> Pixtube
            </div>
            <h2>Регистрация</h2>
            <form method="POST">
                <div class="form-group">
                    <label for="username">Имя пользователя</label>
                    <input type="text" id="username" name="username" class="form-control" placeholder="Введите имя" required>
                </div>
                <div class="form-group">
                    <label for="password">Пароль</label>
                    <input type="password" id="password" name="password" class="form-control" placeholder="Введите пароль" required>
                </div>
                <button type="submit" class="btn">Зарегистрироваться</button>
            </form>
            <a href="/" class="back-link"><i class="fas fa-arrow-left"></i> На главную</a>
        </div>
    </body>
    </html>
    '''

# Вход
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            if user.is_banned:
                return '''
                <div class="container">
                    <div class="auth-container">
                        <h2>Вход</h2>
                        <div style="background-color: #ffebee; color: #c62828; padding: 15px; border-radius: 5px; text-align: center; margin-bottom: 20px;">
                            <i class="fas fa-ban"></i> Ваш канал забанен
                        </div>
                        <form method="POST">
                            <div class="form-group">
                                <label for="username">Имя пользователя</label>
                                <input type="text" id="username" name="username" class="form-control" placeholder="Введите имя" required>
                            </div>
                            <div class="form-group">
                                <label for="password">Пароль</label>
                                <input type="password" id="password" name="password" class="form-control" placeholder="Введите пароль" required>
                            </div>
                            <button type="submit" class="btn btn-block">Войти</button>
                        </form>
                        <a href="/" class="back-link"><i class="fas fa-arrow-left"></i> На главную</a>
                    </div>
                </div>
                '''
            session['user_id'] = user.id
            return redirect('/')
        
        return '''
        <div class="container">
            <div class="auth-container">
                <h2>Вход</h2>
                <p style="color: red; text-align: center; margin-bottom: 20px;">Неверный логин или пароль</p>
                <form method="POST">
                    <div class="form-group">
                        <label for="username">Имя пользователя</label>
                        <input type="text" id="username" name="username" class="form-control" placeholder="Введите имя" required>
                    </div>
                    <div class="form-group">
                        <label for="password">Пароль</label>
                        <input type="password" id="password" name="password" class="form-control" placeholder="Введите пароль" required>
                    </div>
                    <button type="submit" class="btn btn-block">Войти</button>
                </form>
                <a href="/" class="back-link"><i class="fas fa-arrow-left"></i> На главную</a>
            </div>
        </div>
        '''
    
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Вход - Pixtube</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            
            body {
                background-color: #f5f5f5;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
            }
            
            .auth-container {
                width: 100%;
                max-width: 400px;
                padding: 30px;
                background-color: white;
                border-radius: 10px;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            }
            
            .auth-container h2 {
                text-align: center;
                margin-bottom: 25px;
                color: #ff0000;
            }
            
            .form-group {
                margin-bottom: 20px;
            }
            
            .form-group label {
                display: block;
                margin-bottom: 8px;
                font-weight: 500;
                color: #555;
            }
            
            .form-control {
                width: 100%;
                padding: 12px 15px;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-size: 1rem;
                transition: border 0.3s;
            }
            
            .form-control:focus {
                outline: none;
                border-color: #ff0000;
            }
            
            .btn {
                display: inline-block;
                background-color: #ff0000;
                color: white;
                padding: 12px 25px;
                border: none;
                border-radius: 5px;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                text-align: center;
                text-decoration: none;
                width: 100%;
            }
            
            .btn:hover {
                background-color: #cc0000;
                transform: translateY(-2px);
            }
            
            .back-link {
                display: block;
                margin-top: 15px;
                color: #666;
                text-decoration: none;
                text-align: center;
            }
            
            .back-link:hover {
                color: #ff0000;
            }
            
            .logo {
                text-align: center;
                margin-bottom: 20px;
                color: #ff0000;
                font-size: 1.5rem;
                font-weight: bold;
            }
            
            .register-link {
                text-align: center;
                margin-top: 15px;
                color: #666;
            }
            
            .register-link a {
                color: #ff0000;
                text-decoration: none;
                font-weight: 500;
            }
        </style>
    </head>
    <body>
        <div class="auth-container">
            <div class="logo">
                <i class="fab fa-youtube"></i> Pixtube
            </div>
            <h2>Вход в аккаунт</h2>
            <form method="POST">
                <div class="form-group">
                    <label for="username">Имя пользователя</label>
                    <input type="text" id="username" name="username" class="form-control" placeholder="Введите имя" required>
                </div>
                <div class="form-group">
                    <label for="password">Пароль</label>
                    <input type="password" id="password" name="password" class="form-control" placeholder="Введите пароль" required>
                </div>
                <button type="submit" class="btn">Войти</button>
            </form>
            <div class="register-link">
                Нет аккаунта? <a href="/register">Зарегистрироваться</a>
            </div>
            <a href="/" class="back-link"><i class="fas fa-arrow-left"></i> На главную</a>
        </div>
    </body>
    </html>
    '''

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/')

# Загрузка видео
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    user = current_user()
    if not user or user.is_banned:
        return redirect('/')
    
    if request.method == 'POST':
        title = request.form['title']
        video_file = request.files['video']
        
        if video_file:
            filename = video_file.filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            video_file.save(filepath)
            
            video = Video(
                title=title,
                filename=filename,
                user_id=user.id
            )
            db.session.add(video)
            db.session.commit()
            
            return redirect('/')
    
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Загрузка видео - Pixtube</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            
            body {
                background-color: #f5f5f5;
            }
            
            .container {
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }
            
            .upload-container {
                background-color: white;
                border-radius: 10px;
                padding: 30px;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            }
            
            .upload-container h1 {
                color: #ff0000;
                margin-bottom: 25px;
                text-align: center;
            }
            
            .form-group {
                margin-bottom: 20px;
            }
            
            .form-group label {
                display: block;
                margin-bottom: 8px;
                font-weight: 500;
                color: #555;
                font-size: 1.1rem;
            }
            
            .form-control {
                width: 100%;
                padding: 12px 15px;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-size: 1rem;
                transition: border 0.3s;
            }
            
            .form-control:focus {
                outline: none;
                border-color: #ff0000;
            }
            
            .file-input {
                padding: 15px;
                border: 2px dashed #ddd;
                border-radius: 5px;
                text-align: center;
                cursor: pointer;
                transition: all 0.3s;
            }
            
            .file-input:hover {
                border-color: #ff0000;
                background-color: #f9f9f9;
            }
            
            .btn {
                display: inline-block;
                background-color: #ff0000;
                color: white;
                padding: 12px 25px;
                border: none;
                border-radius: 5px;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                text-align: center;
                text-decoration: none;
                width: 100%;
                margin-top: 20px;
            }
            
            .btn:hover {
                background-color: #cc0000;
                transform: translateY(-2px);
            }
            
            .back-link {
                display: inline-block;
                margin-top: 15px;
                color: #666;
                text-decoration: none;
            }
            
            .back-link:hover {
                color: #ff0000;
            }
            
            .logo {
                text-align: center;
                margin-bottom: 20px;
                color: #ff0000;
                font-size: 1.8rem;
                font-weight: bold;
            }
            
            .upload-icon {
                font-size: 3rem;
                color: #ff0000;
                margin-bottom: 15px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">
                <i class="fab fa-youtube"></i> Pixtube
            </div>
            
            <div class="upload-container">
                <h1><i class="fas fa-cloud-upload-alt"></i> Загрузка видео</h1>
                
                <form method="POST" enctype="multipart/form-data">
                    <div class="form-group">
                        <label for="title">Название видео</label>
                        <input type="text" id="title" name="title" class="form-control" placeholder="Введите название видео" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="video">Выберите видео файл</label>
                        <div class="file-input">
                            <div class="upload-icon">
                                <i class="fas fa-file-video"></i>
                            </div>
                            <p>Перетащите файл сюда или нажмите для выбора</p>
                            <input type="file" id="video" name="video" accept="video/*" required style="margin-top: 10px;">
                        </div>
                    </div>
                    
                    <button type="submit" class="btn">Загрузить видео</button>
                </form>
                
                <a href="/" class="back-link"><i class="fas fa-arrow-left"></i> На главную</a>
            </div>
        </div>
    </body>
    </html>
    '''

# Просмотр видео
@app.route('/video/<int:video_id>')
def video(video_id):
    video = Video.query.get_or_404(video_id)
    user = current_user()
    
    if video.is_blocked:
        return '''
        <div class="container">
            <div style="text-align: center; padding: 50px; background-color: white; border-radius: 10px; margin-top: 50px;">
                <i class="fas fa-ban" style="font-size: 4rem; color: #ff3333; margin-bottom: 20px;"></i>
                <h1 style="color: #ff3333;">Видео заблокировано</h1>
                <p style="font-size: 1.2rem; margin-top: 20px;">Это видео было заблокировано администрацией за нарушение правил платформы.</p>
                <a href="/" class="btn" style="display: inline-block; margin-top: 20px;">Вернуться на главную</a>
            </div>
        </div>
        '''
    
    if video.author.is_banned:
        return '''
        <div class="container">
            <div style="text-align: center; padding: 50px; background-color: white; border-radius: 10px; margin-top: 50px;">
                <i class="fas fa-user-slash" style="font-size: 4rem; color: #ff3333; margin-bottom: 20px;"></i>
                <h1 style="color: #ff3333;">Канал автора забанен</h1>
                <p style="font-size: 1.2rem; margin-top: 20px;">Автор этого видео был забанен за нарушение правил платформы.</p>
                <a href="/" class="btn" style="display: inline-block; margin-top: 20px;">Вернуться на главную</a>
            </div>
        </div>
        '''
    
    # Увеличиваем просмотры
    video.views += 1
    db.session.commit()
    
    comments = Comment.query.filter_by(video_id=video_id, is_blocked=False).all()
    
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>{{ video.title }} - Pixtube</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        body {
            background-color: #f5f5f5;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 15px;
        }
        
        /* Шапка */
        header {
            background: linear-gradient(135deg, #ff0000, #cc0000);
            color: white;
            padding: 1rem 0;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        
        .header-content {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .logo {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 1.8rem;
            font-weight: bold;
        }
        
        .logo i {
            color: white;
        }
        
        .nav-links {
            display: flex;
            gap: 20px;
            align-items: center;
        }
        
        .nav-links a {
            color: white;
            text-decoration: none;
            padding: 8px 15px;
            border-radius: 5px;
            transition: all 0.3s ease;
            font-weight: 500;
        }
        
        .nav-links a:hover {
            background-color: rgba(255, 255, 255, 0.2);
        }
        
        .btn {
            display: inline-block;
            background-color: #ff0000;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-align: center;
            text-decoration: none;
        }
        
        .btn:hover {
            background-color: #cc0000;
            transform: translateY(-2px);
        }
        
        .btn-secondary {
            background-color: #4285f4;
        }
        
        .btn-secondary:hover {
            background-color: #3367d6;
        }
        
        /* Основной контент */
        .video-page {
            padding: 2rem 0;
        }
        
        .video-player-container {
            background-color: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);
            margin-bottom: 2rem;
        }
        
        video {
            width: 100%;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        
        .video-meta h1 {
            font-size: 1.8rem;
            margin-bottom: 15px;
            color: #333;
        }
        
        .video-author-info {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid #eee;
        }
        
        .author-avatar {
            width: 50px;
            height: 50px;
            background-color: #4285f4;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 1.5rem;
            font-weight: bold;
        }
        
        .author-details {
            flex-grow: 1;
        }
        
        .author-name {
            font-weight: 600;
            font-size: 1.1rem;
            color: #333;
        }
        
        .video-stats-bar {
            display: flex;
            gap: 25px;
            color: #666;
            font-size: 1rem;
        }
        
        .video-stats-bar i {
            margin-right: 8px;
            color: #ff0000;
        }
        
        /* Комментарии */
        .comments-section {
            background-color: white;
            border-radius: 10px;
            padding: 25px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);
        }
        
        .comments-section h3 {
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #f0f0f0;
            color: #333;
            font-size: 1.5rem;
        }
        
        .comment-form {
            margin-bottom: 30px;
        }
        
        .comment-form textarea {
            width: 100%;
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 5px;
            resize: vertical;
            min-height: 100px;
            margin-bottom: 15px;
            font-size: 1rem;
            transition: border 0.3s;
        }
        
        .comment-form textarea:focus {
            outline: none;
            border-color: #ff0000;
        }
        
        .comment {
            padding: 20px;
            border-bottom: 1px solid #f0f0f0;
            display: flex;
            gap: 15px;
        }
        
        .comment:last-child {
            border-bottom: none;
        }
        
        .comment-avatar {
            width: 40px;
            height: 40px;
            background-color: #34a853;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            flex-shrink: 0;
        }
        
        .comment-content {
            flex-grow: 1;
        }
        
        .comment-author {
            font-weight: 600;
            color: #333;
            margin-bottom: 8px;
            font-size: 1.1rem;
        }
        
        .comment-text {
            color: #555;
            line-height: 1.6;
            margin-bottom: 10px;
        }
        
        .comment-actions {
            font-size: 0.9rem;
        }
        
        .comment-actions a {
            color: #ff0000;
            text-decoration: none;
            font-weight: 500;
        }
        
        .no-comments {
            text-align: center;
            padding: 40px;
            color: #666;
            font-size: 1.1rem;
        }
        
        .no-comments i {
            font-size: 3rem;
            color: #ddd;
            margin-bottom: 15px;
        }
        
        /* Футер */
        footer {
            background-color: #333;
            color: white;
            padding: 2rem 0;
            margin-top: 3rem;
            text-align: center;
        }
        
        @media (max-width: 768px) {
            .header-content {
                flex-direction: column;
                gap: 15px;
            }
            
            .video-stats-bar {
                flex-direction: column;
                gap: 10px;
            }
        }
    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body>
    <header>
        <div class="container">
            <div class="header-content">
                <a href="/" class="logo" style="text-decoration: none; color: white;">
                    <i class="fab fa-youtube"></i>
                    <span>Pixtube</span>
                </a>
                
                <div class="nav-links">
                    {% if user %}
                        <span style="font-weight: 500;">{{ user.username }}</span>
                        <a href="/upload" class="btn">Загрузить видео</a>
                        {% if user.is_admin %}
                            <a href="/admin" class="btn btn-secondary">Админка</a>
                        {% endif %}
                        <a href="/logout" class="btn btn-secondary">Выйти</a>
                    {% else %}
                        <a href="/login" class="btn">Войти</a>
                        <a href="/register" class="btn btn-secondary">Регистрация</a>
                    {% endif %}
                </div>
            </div>
        </div>
    </header>
    
    <div class="container">
        <div class="video-page">
            <div class="video-player-container">
                <video controls>
                    <source src="/static/videos/{{ video.filename }}" type="video/mp4">
                    Ваш браузер не поддерживает видео тег.
                </video>
                
                <div class="video-meta">
                    <h1>{{ video.title }}</h1>
                    
                    <div class="video-author-info">
                        <div class="author-avatar">
                            {{ video.author.username[0].upper() }}
                        </div>
                        <div class="author-details">
                            <div class="author-name">{{ video.author.username }}</div>
                            <div class="video-stats-bar">
                                <span><i class="fas fa-eye"></i> {{ video.views }} просмотров</span>
                                <span><i class="far fa-calendar"></i> {{ video.created_at.strftime('%d.%m.%Y') }}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="comments-section">
                <h3>Комментарии ({{ comments|length }})</h3>
                
                {% if user and not user.is_banned %}
                <div class="comment-form">
                    <form method="POST" action="/comment/{{ video.id }}">
                        <textarea name="content" placeholder="Добавьте комментарий..." required></textarea>
                        <button type="submit" class="btn">Отправить комментарий</button>
                    </form>
                </div>
                {% elif not user %}
                <p style="text-align: center; padding: 20px; background-color: #f9f9f9; border-radius: 5px;">
                    <a href="/login" style="color: #ff0000; font-weight: 500;">Войдите</a>, чтобы оставить комментарий
                </p>
                {% endif %}
                
                {% if comments %}
                    {% for comment in comments %}
                    <div class="comment">
                        <div class="comment-avatar">
                            {{ comment.author.username[0].upper() }}
                        </div>
                        <div class="comment-content">
                            <div class="comment-author">{{ comment.author.username }}</div>
                            <div class="comment-text">{{ comment.content }}</div>
                            <div class="comment-actions">
                                {% if user and user.is_admin %}
                                <a href="/admin/block_comment/{{ comment.id }}">Заблокировать</a>
                                {% endif %}
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                {% else %}
                <div class="no-comments">
                    <i class="far fa-comment-dots"></i>
                    <p>Пока нет комментариев. Будьте первым!</p>
                </div>
                {% endif %}
            </div>
            
            <div style="text-align: center; margin-top: 2rem;">
                <a href="/" class="btn"><i class="fas fa-arrow-left"></i> На главную</a>
            </div>
        </div>
    </div>
    
    <footer>
        <div class="container">
            <p>© 2023 Pixtube. Все права защищены.</p>
            <p>Платформа для обмена видео</p>
        </div>
    </footer>
</body>
</html>
    ''', video=video, comments=comments, user=user)

# Комментарий
@app.route('/comment/<int:video_id>', methods=['POST'])
def add_comment(video_id):
    user = current_user()
    if not user or user.is_banned:
        return redirect('/')
    
    content = request.form['content']
    comment = Comment(
        content=content,
        user_id=user.id,
        video_id=video_id
    )
    db.session.add(comment)
    db.session.commit()
    
    return redirect(f'/video/{video_id}')

# АДМИНКА
@app.route('/admin')
def admin():
    user = current_user()
    if not user or not user.is_admin:
        return redirect('/')
    
    videos = Video.query.all()
    users = User.query.all()
    comments = Comment.query.all()
    
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Админ панель - Pixtube</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        body {
            background-color: #f5f5f5;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 15px;
        }
        
        /* Шапка */
        header {
            background: linear-gradient(135deg, #333, #222);
            color: white;
            padding: 1rem 0;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        
        .header-content {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .logo {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 1.8rem;
            font-weight: bold;
        }
        
        .logo i {
            color: #ff0000;
        }
        
        .nav-links {
            display: flex;
            gap: 20px;
            align-items: center;
        }
        
        .nav-links a {
            color: white;
            text-decoration: none;
            padding: 8px 15px;
            border-radius: 5px;
            transition: all 0.3s ease;
            font-weight: 500;
        }
        
        .nav-links a:hover {
            background-color: rgba(255, 255, 255, 0.2);
        }
        
        .btn {
            display: inline-block;
            background-color: #ff0000;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-align: center;
            text-decoration: none;
        }
        
        .btn:hover {
            background-color: #cc0000;
            transform: translateY(-2px);
        }
        
        /* Админ панель */
        .admin-panel {
            padding: 2rem 0;
        }
        
        .admin-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
        }
        
        .admin-header h1 {
            color: #333;
        }
        
        .admin-section {
            background-color: white;
            border-radius: 10px;
            padding: 25px;
            margin-bottom: 2rem;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);
        }
        
        .admin-section h2 {
            color: #ff0000;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #f0f0f0;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .admin-section h2 i {
            color: #ff0000;
        }
        
        .admin-table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .admin-table th {
            background-color: #f8f8f8;
            padding: 15px;
            text-align: left;
            font-weight: 600;
            color: #333;
            border-bottom: 2px solid #eee;
            font-size: 0.95rem;
        }
        
        .admin-table td {
            padding: 15px;
            border-bottom: 1px solid #eee;
            vertical-align: top;
            font-size: 0.9rem;
        }
        
        .admin-table tr:hover {
            background-color: #f9f9f9;
        }
        
        .admin-table .banned {
            background-color: #ffebee;
        }
        
        .admin-table .admin-user {
            background-color: #e8f5e9;
        }
        
        .action-buttons {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }
        
        .action-btn {
            padding: 6px 12px;
            border-radius: 4px;
            font-size: 0.85rem;
            text-decoration: none;
            font-weight: 500;
            transition: all 0.3s;
            white-space: nowrap;
        }
        
        .action-btn.ban {
            background-color: #ff3333;
            color: white;
        }
        
        .action-btn.ban:hover {
            background-color: #d32f2f;
        }
        
        .action-btn.unban {
            background-color: #34a853;
            color: white;
        }
        
        .action-btn.unban:hover {
            background-color: #2e7d32;
        }
        
        .action-btn.block {
            background-color: #ff9800;
            color: white;
        }
        
        .action-btn.block:hover {
            background-color: #ef6c00;
        }
        
        .action-btn.unblock {
            background-color: #4285f4;
            color: white;
        }
        
        .action-btn.unblock:hover {
            background-color: #3367d6;
        }
        
        .action-btn.view {
            background-color: #9c27b0;
            color: white;
        }
        
        .action-btn.view:hover {
            background-color: #7b1fa2;
        }
        
        .user-status {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 500;
        }
        
        .status-admin {
            background-color: #4caf50;
            color: white;
        }
        
        .status-banned {
            background-color: #f44336;
            color: white;
        }
        
        .status-normal {
            background-color: #2196f3;
            color: white;
        }
        
        .video-status {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 500;
        }
        
        .status-blocked {
            background-color: #ff9800;
            color: white;
        }
        
        .status-active {
            background-color: #4caf50;
            color: white;
        }
        
        /* Футер */
        footer {
            background-color: #333;
            color: white;
            padding: 2rem 0;
            margin-top: 3rem;
            text-align: center;
        }
        
        /* Адаптивность */
        @media (max-width: 1024px) {
            .admin-table {
                display: block;
                overflow-x: auto;
            }
        }
        
        @media (max-width: 768px) {
            .header-content {
                flex-direction: column;
                gap: 15px;
            }
            
            .admin-header {
                flex-direction: column;
                align-items: flex-start;
                gap: 15px;
            }
            
            .action-buttons {
                flex-direction: column;
            }
        }
    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body>
    <header>
        <div class="container">
            <div class="header-content">
                <a href="/" class="logo" style="text-decoration: none; color: white;">
                    <i class="fab fa-youtube"></i>
                    <span>Pixtube Админ</span>
                </a>
                
                <div class="nav-links">
                    <span style="font-weight: 500;">{{ user.username }} (Администратор)</span>
                    <a href="/" class="btn">На сайт</a>
                    <a href="/logout" class="btn">Выйти</a>
                </div>
            </div>
        </div>
    </header>
    
    <div class="container">
        <div class="admin-panel">
            <div class="admin-header">
                <h1><i class="fas fa-crown"></i> Панель администратора</h1>
                <p>Всего: {{ users|length }} пользователей, {{ videos|length }} видео, {{ comments|length }} комментариев</p>
            </div>
            
            <div class="admin-section">
                <h2><i class="fas fa-users"></i> Пользователи</h2>
                <table class="admin-table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Имя пользователя</th>
                            <th>Статус</th>
                            <th>Действия</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for u in users %}
                        <tr class="{% if u.is_banned %}banned{% elif u.is_admin %}admin-user{% endif %}">
                            <td>{{ u.id }}</td>
                            <td>{{ u.username }}</td>
                            <td>
                                {% if u.is_admin %}
                                <span class="user-status status-admin"><i class="fas fa-crown"></i> Админ</span>
                                {% elif u.is_banned %}
                                <span class="user-status status-banned"><i class="fas fa-ban"></i> Забанен</span>
                                {% else %}
                                <span class="user-status status-normal"><i class="fas fa-user"></i> Пользователь</span>
                                {% endif %}
                            </td>
                            <td>
                                <div class="action-buttons">
                                    {% if not u.is_admin %}
                                        {% if u.is_banned %}
                                        <a href="/admin/unban/{{ u.id }}" class="action-btn unban"><i class="fas fa-user-check"></i> Разбанить</a>
                                        {% else %}
                                        <a href="/admin/ban/{{ u.id }}" class="action-btn ban"><i class="fas fa-user-slash"></i> Забанить</a>
                                        {% endif %}
                                    {% else %}
                                    <span style="color: #666; font-size: 0.85rem;">Нет действий</span>
                                    {% endif %}
                                </div>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            
            <div class="admin-section">
                <h2><i class="fas fa-video"></i> Видео</h2>
                <table class="admin-table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Название</th>
                            <th>Автор</th>
                            <th>Просмотры</th>
                            <th>Статус</th>
                            <th>Действия</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for v in videos %}
                        <tr class="{% if v.is_blocked %}banned{% endif %}">
                            <td>{{ v.id }}</td>
                            <td>{{ v.title[:50] }}{% if v.title|length > 50 %}...{% endif %}</td>
                            <td>{{ v.author.username }}</td>
                            <td>{{ v.views }}</td>
                            <td>
                                {% if v.is_blocked %}
                                <span class="video-status status-blocked"><i class="fas fa-ban"></i> Заблокировано</span>
                                {% else %}
                                <span class="video-status status-active"><i class="fas fa-check-circle"></i> Активно</span>
                                {% endif %}
                            </td>
                            <td>
                                <div class="action-buttons">
                                    {% if v.is_blocked %}
                                    <a href="/admin/unblock_video/{{ v.id }}" class="action-btn unblock"><i class="fas fa-unlock"></i> Разблок.</a>
                                    {% else %}
                                    <a href="/admin/block_video/{{ v.id }}" class="action-btn block"><i class="fas fa-lock"></i> Заблок.</a>
                                    {% endif %}
                                    <a href="/video/{{ v.id }}" class="action-btn view" target="_blank"><i class="fas fa-eye"></i> Смотреть</a>
                                </div>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            
            <div class="admin-section">
                <h2><i class="fas fa-comments"></i> Комментарии</h2>
                <table class="admin-table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Текст</th>
                            <th>Автор</th>
                            <th>Видео</th>
                            <th>Статус</th>
                            <th>Действия</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for c in comments %}
                        <tr class="{% if c.is_blocked %}banned{% endif %}">
                            <td>{{ c.id }}</td>
                            <td>{{ c.content[:80] }}{% if c.content|length > 80 %}...{% endif %}</td>
                            <td>{{ c.author.username }}</td>
                            <td>{{ c.video.title[:30] }}{% if c.video.title|length > 30 %}...{% endif %}</td>
                            <td>
                                {% if c.is_blocked %}
                                <span class="video-status status-blocked"><i class="fas fa-ban"></i> Заблокирован</span>
                                {% else %}
                                <span class="video-status status-active"><i class="fas fa-check-circle"></i> Активен</span>
                                {% endif %}
                            </td>
                            <td>
                                <div class="action-buttons">
                                    {% if c.is_blocked %}
                                    <a href="/admin/unblock_comment/{{ c.id }}" class="action-btn unblock"><i class="fas fa-unlock"></i> Разблок.</a>
                                    {% else %}
                                    <a href="/admin/block_comment/{{ c.id }}" class="action-btn block"><i class="fas fa-lock"></i> Заблок.</a>
                                    {% endif %}
                                </div>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    
    <footer>
        <div class="container">
            <p>© 2023 Pixtube. Административная панель.</p>
            <p>Только для авторизованных администраторов.</p>
        </div>
    </footer>
</body>
</html>
    ''', videos=videos, users=users, comments=comments, user=user)  # ИСПРАВЛЕНО: добавлен user=user

# Админ действия
@app.route('/admin/ban/<int:user_id>')
def ban_user(user_id):
    if not is_admin():
        return redirect('/')
    
    user = User.query.get(user_id)
    if user and not user.is_admin:
        user.is_banned = True
        
        # Удаляем все видео пользователя
        videos = Video.query.filter_by(user_id=user_id).all()
        for video in videos:
            # Удаляем файл видео
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], video.filename)
            if os.path.exists(filepath):
                os.remove(filepath)
            # Удаляем из базы
            db.session.delete(video)
        
        db.session.commit()
    
    return redirect('/admin')

@app.route('/admin/unban/<int:user_id>')
def unban_user(user_id):
    if not is_admin():
        return redirect('/')
    
    user = User.query.get(user_id)
    if user:
        user.is_banned = False
        db.session.commit()
    
    return redirect('/admin')

@app.route('/admin/block_video/<int:video_id>')
def block_video(video_id):
    if not is_admin():
        return redirect('/')
    
    video = Video.query.get(video_id)
    if video:
        video.is_blocked = True
        db.session.commit()
    
    return redirect('/admin')

@app.route('/admin/unblock_video/<int:video_id>')
def unblock_video(video_id):
    if not is_admin():
        return redirect('/')
    
    video = Video.query.get(video_id)
    if video:
        video.is_blocked = False
        db.session.commit()
    
    return redirect('/admin')

@app.route('/admin/block_comment/<int:comment_id>')
def block_comment(comment_id):
    if not is_admin():
        return redirect('/')
    
    comment = Comment.query.get(comment_id)
    if comment:
        comment.is_blocked = True
        db.session.commit()
    
    return redirect(request.referrer or '/admin')

@app.route('/admin/unblock_comment/<int:comment_id>')
def unblock_comment(comment_id):
    if not is_admin():
        return redirect('/')
    
    comment = Comment.query.get(comment_id)
    if comment:
        comment.is_blocked = False
        db.session.commit()
    
    return redirect('/admin')

if __name__ == '__main__':
    # Для Render используем порт из окружения
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
