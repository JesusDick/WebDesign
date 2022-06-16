from flask import Flask, render_template, request, url_for, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

import os
import sys
import click

WIN = sys.platform.startswith('win')
if WIN:  # 如果是 Windows 系统，使用三個斜槓
    prefix = 'sqlite:///'
else:  # 否則使用四個斜槓
    prefix = 'sqlite:////'

app = Flask(__name__)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

app.config['SECRET_KEY'] = 'dev'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://bcjrmszwukoaov:908980c9d57498e34d15cde857459304e0505dda916ca9429fdbdfe2502573d8@ec2-23-23-182-238.compute-1.amazonaws.com:5432/dtf2ujo6lplnf'
#app.config['SQLALCHEMY_DATABASE_URI'] = 'prefix + os.path.join(app.root_path, 'data.db')'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # 關閉對模型修改的監控

db = SQLAlchemy(app)

@login_manager.user_loader
def load_user(user_id):  # 創建用戶加載回調函數，接受用戶 ID 作為參數
    user = User.query.get(int(user_id))  # 用 ID 作為 User 模型的主鍵查詢對應的用戶
    return user  # 返回用戶對象

class User(db.Model, UserMixin):  # 表名將會是 user（自動生成，小寫處理）
    id = db.Column(db.Integer, primary_key=True)  # 主鍵
    name = db.Column(db.String(20))  # 名字
    username = db.Column(db.String(20))  # 用戶名
    password_hash = db.Column(db.String(128))  # 密碼散列值

    def set_password(self, password):  # 用來設置密碼的方法，接受密碼作為參數
        self.password_hash = generate_password_hash(password)  # 將生成的密碼保持到對應字段

    def validate_password(self, password):  # 用於驗證密碼的方法，接受密碼作為參數
        return check_password_hash(self.password_hash, password)  # 返回布林值

class Movie(db.Model):  # 表名將會是 movie
    id = db.Column(db.Integer, primary_key=True)  # 主鍵
    title = db.Column(db.String(60))  # 電影標題
    year = db.Column(db.String(4))  # 電影年份


@app.cli.command()
@click.option('--username', prompt=True, help='The username used to login.')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='The password used to login.')
def admin(username, password):
    """Create user."""
    db.create_all()

    user = User.query.first()
    if user is not None:
        click.echo('Updating user...')
        user.username = username
        user.set_password(password)  # 設置密碼
    else:
        click.echo('Creating user...')
        user = User(username=username, name='Admin')
        user.set_password(password)  # 設置密碼
        db.session.add(user)

    db.session.commit()  # 提交資料庫會話
    click.echo('Done.')

@app.cli.command()  # 註冊為命令
@click.option('--drop', is_flag=True, help='Create after drop.')  # 設置選項
def initdb(drop):
    """Initialize the database."""
    if drop:  # 判斷是否輸入選項
        db.drop_all()
    db.create_all()
    click.echo('Initialized database.')  # 輸出提示訊息

@app.cli.command()
def forge():
    """Generate fake data."""
    db.create_all()
    
    # 全局的两個變量移動到這個函數内
    name = 'Grey Li'
    movies = [
        {'title': 'My Neighbor Totoro', 'year': '1988'},
        {'title': 'Dead Poets Society', 'year': '1989'},
        {'title': 'A Perfect World', 'year': '1993'},
        {'title': 'Leon', 'year': '1994'},
        {'title': 'Mahjong', 'year': '1996'},
        {'title': 'Swallowtail Butterfly', 'year': '1996'},
        {'title': 'King of Comedy', 'year': '1999'},
        {'title': 'Devils on the Doorstep', 'year': '1999'},
        {'title': 'WALL-E', 'year': '2008'},
        {'title': 'The Pork of Music', 'year': '2012'},
    ]
    
    user = User(name=name)
    db.session.add(user)
    for m in movies:
        movie = Movie(title=m['title'], year=m['year'])
        db.session.add(movie)
    
    db.session.commit()
    click.echo('Done.')

# 新增電影條目
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':  # 判斷是否是 POST 請求
        if not current_user.is_authenticated:  # 如果當前用戶未認證
            return redirect(url_for('index'))  # 重定向到主頁
        # 獲取表單數據
        title = request.form.get('title')  # 傳入表單對應输入字段的 name 值
        year = request.form.get('year')
        # 驗證數據
        if not title or not year or len(year) > 4 or len(title) > 60:
            flash('Invalid input.')  # 顯示錯誤提示
            return redirect(url_for('index'))  # 重定向回主页
        # 保存表單數據到資料庫
        movie = Movie(title=title, year=year)  # 創建紀錄
        db.session.add(movie)  # 添加到資料庫會話
        db.session.commit()  # 提交資料庫會話
        flash('Item created.')  # 顯示成功創建的提示
        return redirect(url_for('index'))  # 重定向回主頁

    movies = Movie.query.all()
    return render_template('index.html', movies=movies)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.context_processor
def inject_user():
    user = User.query.first()
    return dict(user=user)  # 需要返回字典，等同於 return {'user': user}

# 編輯電影條目
@app.route('/movie/edit/<int:movie_id>', methods=['GET', 'POST'])
@login_required
def edit(movie_id):
    movie = Movie.query.get_or_404(movie_id)

    if request.method == 'POST':  # 處理編輯表單的提交請求
        title = request.form['title']
        year = request.form['year']
        
        if not title or not year or len(year) != 4 or len(title) > 60:
            flash('Invalid input.')
            return redirect(url_for('edit', movie_id=movie_id))  # 重定向回對應的編輯頁面
        
        movie.title = title  # 更新標題
        movie.year = year  # 更新年份
        db.session.commit()  # 提交資料庫會話
        flash('Item updated.')
        return redirect(url_for('index'))  # 重定向回主頁
    
    return render_template('edit.html', movie=movie)  # 傳入被編輯的電影紀錄

# 刪除電影條目
@app.route('/movie/delete/<int:movie_id>', methods=['POST'])  # 限定只接受 POST 請求
@login_required
def delete(movie_id):
    movie = Movie.query.get_or_404(movie_id)  # 獲取電影紀錄
    db.session.delete(movie)  # 删除對應的紀錄
    db.session.commit()  # 提交資料庫會話
    flash('Item deleted.')
    return redirect(url_for('index'))  # 重定向回主頁

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            flash('Invalid input.')
            return redirect(url_for('login'))
        
        user = User.query.first()
        # 驗證用戶名和密碼是否一致
        if username == user.username and user.validate_password(password):
            login_user(user)  # 登入用戶
            flash('Login success.')
            return redirect(url_for('index'))  # 重定向到主頁

        flash('Invalid username or password.')  # 如果驗證失敗，顯示錯誤消息
        return redirect(url_for('login'))  # 重定向回登錄頁面
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()  # 登出用戶
    flash('Goodbye.')
    return redirect(url_for('index'))  # 重定向回首页

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        name = request.form['name']
        
        if not name or len(name) > 20:
            flash('Invalid input.')
            return redirect(url_for('settings'))
        
        current_user.name = name
        # current_user 會返回當前登錄用戶的資料庫記錄對象
        # 等同於下面的用法
        # user = User.query.first()
        # user.name = name
        db.session.commit()
        flash('Settings updated.')
        return redirect(url_for('index'))
    return render_template('settings.html')