import os
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
db.init_app(app)

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

@app.route('/news')
def news():
    page = request.args.get('page', 1, type=int)
    news_items = News.query.order_by(News.date.desc()).paginate(
        page=page, per_page=6, error_out=False)
    return render_template('news.html', news_items=news_items)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        contact = Contact(
            name=request.form['name'],
            company=request.form['company'],
            email=request.form['email'],
            phone=request.form['phone'],
            subject=request.form['subject'],
            message=request.form['message'],
            date=datetime.now()
        )
        db.session.add(contact)
        db.session.commit()
        flash('お問い合わせありがとうございます。担当者より連絡させていただきます。')
        return redirect(url_for('contact'))
    return render_template('contact.html')

with app.app_context():
    db.create_all()
    
    # Add sample news if none exist
    if not News.query.first():
        sample_news = [
            News(
                title="新オフィスへの移転のお知らせ",
                content="より良いサービス提供のため、本社オフィスを移転いたしました。",
                summary="本社オフィス移転のお知らせ",
                date=datetime.now()
            ),
            News(
                title="クラウドソリューション事業部の設立",
                content="お客様のデジタルトランスフォーメーションを支援するため、新事業部を設立しました。",
                summary="新事業部設立のお知らせ",
                date=datetime.now()
            ),
            News(
                title="技術セミナー開催のお知らせ",
                content="最新のテクノロジートレンドについて、オンラインセミナーを開催いたします。",
                summary="技術セミナー開催",
                date=datetime.now()
            )
        ]
        for news in sample_news:
            db.session.add(news)
        db.session.commit()
