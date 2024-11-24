import os
from flask_mail import Mail, Message
from datetime import datetime
from flask import Flask, render_template, request, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "a secret key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///unitectol.db"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# メール設定
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT'))
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME')

db.init_app(app)
mail = Mail(app)

from models import News, Contact

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
    news_items = News.query.order_by(News.date.desc()).paginate(
        page=page, per_page=6, error_out=False)
    return render_template('news.html', news_items=news_items)

@app.route('/news/<int:id>')
def news_detail(id):
    news = News.query.get_or_404(id)
    return render_template('news_detail.html', news=news)

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

        # 管理者へのメール通知
        msg = Message(
            subject='新規お問い合わせ',
            recipients=[app.config['MAIL_USERNAME']],
            body=f'''
新規のお問い合わせがありました。

お名前: {contact.name}
会社名: {contact.company}
メールアドレス: {contact.email}
電話番号: {contact.phone}
お問い合わせ内容: {contact.subject}
メッセージ:
{contact.message}
            '''
        )
        mail.send(msg)

        flash('お問い合わせありがとうございます。担当者より連絡させていただきます。')
        return redirect(url_for('contact'))
    return render_template('contact.html')

with app.app_context():
    db.create_all()
    
    # Add sample news if none exist
    if not News.query.first():
        for news_data in [
            {
                "title": "新オフィスへの移転のお知らせ",
                "content": "より良いサービス提供のため、本社オフィスを移転いたしました。",
                "summary": "本社オフィス移転のお知らせ"
            },
            {
                "title": "クラウドソリューション事業部の設立",
                "content": "お客様のデジタルトランスフォーメーションを支援するため、新事業部を設立しました。",
                "summary": "新事業部設立のお知らせ"
            },
            {
                "title": "技術セミナー開催のお知らせ",
                "content": "最新のテクノロジートレンドについて、オンラインセミナーを開催いたします。",
                "summary": "技術セミナー開催"
            }
        ]:
            news = News()
            news.title = news_data["title"]
            news.content = news_data["content"]
            news.summary = news_data["summary"]
            news.date = datetime.now()
            db.session.add(news)
        db.session.commit()
