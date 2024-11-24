import os
from datetime import datetime
from flask import Flask, render_template, request, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin as FlaskAdmin
from flask_admin.contrib.sqla import ModelView
from flask_ckeditor import CKEditor
from flask_mail import Mail, Message
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import ssl
import smtplib
import traceback
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
import os
import ssl
from flask_mail import Mail, Message
from flask_admin import Admin as FlaskAdmin
from flask_admin.contrib.sqla import ModelView
from flask_ckeditor import CKEditor
from datetime import datetime
from flask import Flask, render_template, request, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "a secret key"
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# メール設定
app.config['MAIL_SERVER'] = 'sv15011.xserver.jp'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'info@connectsol-corp.com'
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = ('株式会社コネクトソル', 'info@connectsol-corp.com')
app.config['MAIL_DEBUG'] = True
app.config['MAIL_MAX_EMAILS'] = None
app.config['MAIL_SUPPRESS_SEND'] = False

# SMTPデバッグログを有効化
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('flask.app')

# SSLコンテキストの設定
# メール設定
app.config['MAIL_SERVER'] = 'sv15011.xserver.jp'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'info@connectsol-corp.com'
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = ('株式会社コネクトソル', 'info@connectsol-corp.com')

from models import News, Contact, Admin
# Initialize Flask-Admin and CKEditor
admin = FlaskAdmin(app, name='管理画面', template_mode='bootstrap4', url='/admin', endpoint='admin')
ckeditor = CKEditor(app)

# Admin views configuration
class SecureModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('admin_login'))

# Add model views
class NewsAdmin(SecureModelView):
    column_list = ('title', 'date', 'summary')
    form_columns = ('title', 'content', 'summary', 'image_url', 'date')
    column_labels = {
        'title': 'タイトル',
        'content': '内容',
        'summary': '概要',
        'image_url': '画像URL',
        'date': '日付'
    }

class ContactAdmin(SecureModelView):
    column_list = ('name', 'company', 'email', 'subject', 'date', 'status')
    form_columns = ('name', 'company', 'email', 'phone', 'subject', 'message', 'status')
    column_labels = {
        'name': '氏名',
        'company': '会社名',
        'email': 'メールアドレス',
        'phone': '電話番号',
        'subject': '件名',
        'message': 'メッセージ',
        'date': '日付',
        'status': 'ステータス'
    }

# Register model views
admin.add_view(NewsAdmin(News, db.session, name='ニュース管理'))
admin.add_view(ContactAdmin(Contact, db.session, name='お問い合わせ管理'))

db.init_app(app)
mail = Mail(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))

@app.route('/')
def index():
    news_items = News.query.order_by(News.date.desc()).limit(3).all()
    return render_template('index.html', news_items=news_items)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/news')
def news():
    page = request.args.get('page', 1, type=int)
    news_items = News.query.order_by(News.date.desc()).paginate(page=page, per_page=6)
    return render_template('news.html', news_items=news_items)

@app.route('/news/<int:news_id>')
def news_detail(news_id):
    try:
        news = News.query.get_or_404(news_id)
        return render_template('news_detail.html', news=news)
    except Exception as e:
        app.logger.error(f'ニュース詳細の取得エラー: {str(e)}')
        return render_template('404.html'), 404

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        contact = Contact()
        contact.name = request.form['name']
        contact.company = request.form['company']
        contact.email = request.form['email']
        contact.phone = request.form['phone']
        contact.subject = request.form['subject']
        contact.message = request.form['message']
        contact.date = datetime.now()
        
        db.session.add(contact)
        db.session.commit()

        max_retries = 3
        retry_count = 0
        retry_delay = 1  # 秒単位の待機時間

        while retry_count < max_retries:
            try:
                app.logger.info(f'メール送信を開始します (試行回数: {retry_count + 1})')
                app.logger.debug(f'SMTP設定: SERVER={app.config["MAIL_SERVER"]}, PORT={app.config["MAIL_PORT"]}, TLS={app.config["MAIL_USE_TLS"]}, SSL={app.config["MAIL_USE_SSL"]}')

                # メール本文の作成
                email_body = f'''
新規のお問い合わせがありました。

お名前: {contact.name}
会社名: {contact.company}
メールアドレス: {contact.email}
電話番号: {contact.phone}
お問い合わせ内容: {contact.subject}

メッセージ:
{contact.message}

このメールは自動送信されています。
'''
                # メッセージの作成
                # メール送信の詳細をログに記録
                app.logger.info('メール送信の設定を確認します')
                app.logger.info(f'送信者: {app.config["MAIL_DEFAULT_SENDER"]}')
                app.logger.info(f'送信先: info@connectsol-corp.com')
                app.logger.info(f'SMTPサーバー: {app.config["MAIL_SERVER"]}:{app.config["MAIL_PORT"]}')
                app.logger.debug(f'メール本文:\n{email_body}')

                # SSLコンテキストを使用してメッセージを作成
                msg = Message(
                    subject='【コネクトソル】新規お問い合わせ',
                    sender=app.config['MAIL_DEFAULT_SENDER'],
                    recipients=['info@connectsol-corp.com'],
                    body=email_body
                )

                # メール送信
                mail.send(msg)
                app.logger.info('メール送信が完了しました')
                flash('お問い合わせありがとうございます。担当者より連絡させていただきます。', 'success')
                break

            except Exception as e:
                retry_count += 1
                error_type = type(e).__name__
                error_details = traceback.format_exc()
                
                app.logger.error(f'メール送信エラー（{error_type}）:\n{error_details}')
                app.logger.error(f'エラーの詳細情報: {str(e)}')

                if isinstance(e, smtplib.SMTPAuthenticationError):
                    app.logger.error('SMTP認証エラー: 認証情報を確認してください')
                    flash('メールサーバーの認証に失敗しました。システム管理者に連絡してください。', 'error')
                    return render_template('contact.html')

                elif isinstance(e, smtplib.SMTPServerDisconnected):
                    app.logger.error('SMTPサーバー接続エラー: サーバーとの接続が切断されました')
                    if retry_count < max_retries:
                        time.sleep(retry_delay)
                        continue

                elif isinstance(e, ssl.SSLError):
                    app.logger.error(f'SSLエラー: {e.reason if hasattr(e, "reason") else str(e)}')
                    flash('セキュアな接続の確立に失敗しました。しばらく時間をおいて再度お試しください。', 'error')
                    return render_template('contact.html')

                elif isinstance(e, smtplib.SMTPRecipientsRefused):
                    app.logger.error(f'受信者拒否エラー: {str(e)}')
                    flash('メール送信に失敗しました。宛先アドレスを確認してください。', 'error')
                    return render_template('contact.html')

                if retry_count >= max_retries:
                    app.logger.error('最大リトライ回数に達しました')
                    if app.debug:
                        flash(f'メール送信エラー: {error_type} - {str(e)}', 'error')
                    else:
                        flash('申し訳ありません。お問い合わせの送信中にエラーが発生しました。しばらく時間をおいて再度お試しください。', 'error')
                    return render_template('contact.html')

                time.sleep(retry_delay * retry_count)  # 再試行時の待機時間を徐々に増やす

        return redirect(url_for('contact'))
    return render_template('contact.html')

# Admin routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = Admin.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        
        flash('ユーザー名またはパスワードが正しくありません。', 'danger')
    return render_template('admin/login.html')

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    news_count = News.query.count()
    contacts_count = Contact.query.filter_by(status='新規').count()
    return render_template('admin/dashboard.html', 
                         news_count=news_count, 
                         contacts_count=contacts_count)

@app.route('/admin/news')
@login_required
def admin_news():
    news_items = News.query.order_by(News.date.desc()).all()
    return render_template('admin/news.html', news_items=news_items)

@app.route('/admin/contacts')
@login_required
def admin_contacts():
    contacts = Contact.query.order_by(Contact.date.desc()).all()
    return render_template('admin/contacts.html', contacts=contacts)

with app.app_context():
    db.create_all()
    # Create default admin user if not exists
    if not Admin.query.filter_by(username='admin').first():
        admin = Admin(
            username='admin',
            email='admin@example.com',
            password_hash=generate_password_hash('admin123')
        )
        db.session.add(admin)
        db.session.commit()
