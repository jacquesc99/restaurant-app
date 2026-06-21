import os
import io
import base64
import qrcode
from PIL import Image
from io import BytesIO
import pandas as pd
import resend
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

app = Flask(__name__)
from config import Config
app.config.from_object(Config)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ── Models ──────────────────────────────────────────────
class Manager(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    restaurants = db.relationship('Restaurant', backref='manager', lazy=True)

class Restaurant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    csv_data = db.Column(db.Text, nullable=True)
    logo_data = db.Column(db.Text, nullable=True)
    qr_color = db.Column(db.String(20), nullable=True, default='#0d47a1')
    qr_bg_color = db.Column(db.String(20), nullable=True, default='#ffffff')
    manager_id = db.Column(db.Integer, db.ForeignKey('manager.id'), nullable=True)

class MenuVisit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    visited_at = db.Column(db.DateTime, default=datetime.utcnow)
    allergens_selected = db.Column(db.String(500), nullable=True)

@login_manager.user_loader
def load_user(user_id):
    return Manager.query.get(int(user_id))

with app.app_context():
    db.create_all()

# ── Routes ───────────────────────────────────────────────

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/restaurants')
def restaurants():
    all_restaurants = Restaurant.query.all()
    return render_template('restaurants.html', restaurants=all_restaurants)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        if not request.form.get('agree_terms'):
            flash('You must agree to the Terms of Service to sign up.')
            return redirect(url_for('signup'))

        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        signature = request.form.get('signature')
        agreed_at = datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')

        if Manager.query.filter_by(email=email).first():
            flash('Email already registered.')
            return redirect(url_for('signup'))

        manager = Manager(
            name=name,
            email=email,
            password=generate_password_hash(password)
        )
        db.session.add(manager)
        db.session.commit()

        try:
            resend.api_key = os.environ.get('RESEND_API_KEY')
            resend.Emails.send({
                "from": "onboarding@resend.dev",
                "to": "jacques.calame89@gmail.com",
                "subject": f"New Signup — {name}",
                "text": f"""
New manager signed up and agreed to Terms of Service:

Name: {name}
Email: {email}
Signed by: {signature}
Date: {agreed_at}
                """
            })
            resend.Emails.send({
                "from": "onboarding@resend.dev",
                "to": email,
                "subject": "Welcome to the Allergen Filter App — Terms of Service Confirmation",
                "text": f"""
Hi {name},

Thank you for signing up for the Allergen & Dietary Filter App.

This email confirms that you have read and agreed to our Terms of Service on {agreed_at}.

Signed by: {signature}

Log in to your dashboard to add your restaurants and upload your menus:
eatwithease.onrender.com/login

© 2026 All Rights Reserved
                """
            })
        except:
            pass

        login_user(manager)
        return redirect(url_for('dashboard'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        manager = Manager.query.filter_by(email=email).first()

        if not manager or not check_password_hash(manager.password, password):
            flash('Invalid email or password.')
            return redirect(url_for('login'))

        login_user(manager, remember=True)

        if manager.is_admin:
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))

    return render_template('login.html')

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form.get('email')
        new_password = request.form.get('new_password')

        manager = Manager.query.filter_by(email=email).first()
        if not manager:
            flash('No account found with that email.')
            return redirect(url_for('reset_password'))

        manager.password = generate_password_hash(new_password)
        db.session.commit()
        flash('Password updated successfully. You can now log in.')
        return redirect(url_for('login'))

    return render_template('reset_password.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('dashboard'))

    managers = Manager.query.filter_by(is_admin=False).all()
    restaurants = Restaurant.query.all()

    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    year_ago = now - timedelta(days=365)

    stats = {}
    for r in restaurants:
        visits = MenuVisit.query.filter_by(restaurant_id=r.id)
        weekly = visits.filter(MenuVisit.visited_at >= week_ago).count()
        monthly = visits.filter(MenuVisit.visited_at >= month_ago).count()
        yearly = visits.filter(MenuVisit.visited_at >= year_ago).count()

        all_visits = visits.filter(MenuVisit.allergens_selected != None).all()
        allergen_counts = {}
        for v in all_visits:
            for a in v.allergens_selected.split(','):
                a = a.strip()
                if a:
                    allergen_counts[a] = allergen_counts.get(a, 0) + 1
        top = sorted(allergen_counts.items(), key=lambda x: x[1], reverse=True)[:3]

        stats[r.id] = {
            'weekly': weekly,
            'monthly': monthly,
            'yearly': yearly,
            'top_allergens': top,
            'has_logo': bool(r.logo_data),
        }

    total_visits = MenuVisit.query.filter(MenuVisit.visited_at >= week_ago).count()

    return render_template('admin.html',
                           managers=managers,
                           restaurants=restaurants,
                           stats=stats,
                           total_visits=total_visits)

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    return render_template('dashboard.html', manager=current_user)

@app.route('/restaurant/<slug>/manage', methods=['GET', 'POST'])
@login_required
def manage_restaurant(slug):
    restaurant = Restaurant.query.filter_by(slug=slug).first_or_404()

    if restaurant.manager_id != current_user.id:
        flash('Access denied.')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        file = request.files.get('csv_files')
        if file and file.filename.endswith('.csv'):
            csv_content = file.read().decode('utf-8')
            restaurant.csv_data = csv_content
            db.session.commit()
            flash('Menu uploaded successfully!')
        else:
            flash('Please upload a valid CSV file.')

    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    year_ago = now - timedelta(days=365)

    visits = MenuVisit.query.filter_by(restaurant_id=restaurant.id)
    weekly = visits.filter(MenuVisit.visited_at >= week_ago).count()
    monthly = visits.filter(MenuVisit.visited_at >= month_ago).count()
    yearly = visits.filter(MenuVisit.visited_at >= year_ago).count()

    all_visits = visits.filter(MenuVisit.allergens_selected != None).all()
    allergen_counts = {}
    for v in all_visits:
        for a in v.allergens_selected.split(','):
            a = a.strip()
            if a:
                allergen_counts[a] = allergen_counts.get(a, 0) + 1
    top_allergens = sorted(allergen_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    menu_url = url_for('menu', slug=restaurant.slug, _external=True)
    return render_template('manage_restaurant.html',
                           restaurant=restaurant,
                           manager=current_user,
                           menu_url=menu_url,
                           weekly=weekly,
                           monthly=monthly,
                           yearly=yearly,
                           top_allergens=top_allergens)

@app.route('/add-restaurant', methods=['GET', 'POST'])
@login_required
def add_restaurant():
    if request.method == 'POST':
        name = request.form.get('name')

        base_slug = name.lower().replace(' ', '-')
        slug = base_slug
        counter = 1
        while Restaurant.query.filter_by(slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1

        restaurant = Restaurant(
            name=name,
            slug=slug,
            manager_id=current_user.id
        )
        db.session.add(restaurant)
        db.session.commit()
        flash(f'{name} added successfully!')
        return redirect(url_for('dashboard'))

    return render_template('add_restaurant.html')

@app.route('/upload-logo/<slug>', methods=['POST'])
@login_required
def upload_logo(slug):
    restaurant = Restaurant.query.filter_by(slug=slug).first_or_404()
    if restaurant.manager_id != current_user.id:
        flash('Access denied.')
        return redirect(url_for('dashboard'))

    file = request.files.get('logo')
    if file and file.filename:
        logo_bytes = file.read()
        logo_b64 = base64.b64encode(logo_bytes).decode('utf-8')
        ext = file.filename.rsplit('.', 1)[-1].lower()
        restaurant.logo_data = f"data:image/{ext};base64,{logo_b64}"
        db.session.commit()
        flash('Logo uploaded successfully!')
    else:
        flash('Please upload a valid image file.')
    return redirect(url_for('manage_restaurant', slug=slug))

@app.route('/update-qr-color/<slug>', methods=['POST'])
@login_required
def update_qr_color(slug):
    restaurant = Restaurant.query.filter_by(slug=slug).first_or_404()
    if restaurant.manager_id != current_user.id:
        flash('Access denied.')
        return redirect(url_for('dashboard'))

    restaurant.qr_color = request.form.get('qr_color', '#0d47a1')
    restaurant.qr_bg_color = request.form.get('qr_bg_color', '#ffffff')
    db.session.commit()
    flash('QR code colors updated!')
    return redirect(url_for('manage_restaurant', slug=slug))

@app.route('/qr/<slug>')
def generate_qr(slug):
    restaurant = Restaurant.query.filter_by(slug=slug).first_or_404()
    menu_url = url_for('menu', slug=slug, _external=True)

    qr_color = restaurant.qr_color or '#0d47a1'
    qr_bg_color = restaurant.qr_bg_color or '#ffffff'

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(menu_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color=qr_color, back_color=qr_bg_color).convert('RGB')

    if restaurant.logo_data:
        try:
            header, b64data = restaurant.logo_data.split(',', 1)
            logo_bytes = base64.b64decode(b64data)
            logo = Image.open(BytesIO(logo_bytes)).convert('RGBA')
            qr_size = qr_img.size[0]
            logo_size = qr_size // 4
            logo = logo.resize((logo_size, logo_size), Image.LANCZOS)
            pos = ((qr_size - logo_size) // 2, (qr_size - logo_size) // 2)
            qr_img.paste(logo, pos, mask=logo.split()[3])
        except:
            pass

    buf = BytesIO()
    qr_img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

@app.route('/generate-menu')
@login_required
def generate_menu():
    return render_template('generate_menu.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/menu/<slug>', methods=['GET', 'POST'])
def menu(slug):
    restaurant = Restaurant.query.filter_by(slug=slug).first_or_404()

    if not restaurant.csv_data:
        return render_template('no_menu.html', restaurant=restaurant)

    visit = MenuVisit(restaurant_id=restaurant.id)
    db.session.add(visit)
    db.session.commit()

    df = pd.read_csv(io.StringIO(restaurant.csv_data.lstrip('\ufeff')), sep=None, engine='python')
    df.columns = df.columns.str.strip().str.lower()
    NON_ALLERGEN_COLUMNS = ['dish', 'category'] + [col for col in df.columns if col.startswith('alt_')]

    for col in df.columns:
        if col not in NON_ALLERGEN_COLUMNS:
            df[col] = (
                df[col].astype(str).str.strip().str.lower()
                .map({"true": True, "false": False, "1": True,
                      "0": False, "yes": True, "no": False})
                .fillna(False)
            )

    allergens = [col for col in df.columns if col not in NON_ALLERGEN_COLUMNS]
    safe_results = []

    if request.method == 'POST':
        selected_allergens = [a.lower() for a in request.form.getlist('allergens')]

        visit.allergens_selected = ','.join(selected_allergens)
        db.session.commit()

        EXCLUDE_IF_TRUE = ['pork', 'beef', 'chicken', 'egg', 'dairy', 'fish', 'shellfish',
                           'gluten', 'peanuts', 'tree nuts', 'soy', 'sesame', 'capsaicin',
                           'piperine', 'unpasteurized (raw) cheese', 'derived protiens',
                           'cured meats', 'seed']

        REQUIRE_TRUE = ['vegetarian', 'vegan', 'pregnancy safe']

        for _, row in df.iterrows():
            is_safe = True
            for a in selected_allergens:
                if a in EXCLUDE_IF_TRUE and row.get(a) == True:
                    is_safe = False
                    break
                if a in REQUIRE_TRUE and row.get(a) != True:
                    is_safe = False
                    break

            if is_safe:
                safe_results.append({
                    "dish": row['dish'],
                    "modified": False
                })
            else:
                relevant_alts = []
                for a in selected_allergens:
                    alt_col = f"alt_{a.replace(' ', '_')}"
                    if alt_col in row and pd.notna(row[alt_col]) and str(row[alt_col]).strip():
                        relevant_alts.append(str(row[alt_col]).strip())

                if relevant_alts:
                    safe_results.append({
                        "dish": row['dish'],
                        "modified": True,
                        "modifications": relevant_alts
                    })

        return render_template('results.html', results=safe_results, restaurant=restaurant)

    return render_template('index.html', allergens=allergens, restaurant=restaurant)