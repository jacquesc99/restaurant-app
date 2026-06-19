import os
import io
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash
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
class Restaurant(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    csv_data = db.Column(db.Text, nullable=True)
    is_admin = db.Column(db.Boolean, default=False)

class MenuVisit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    visited_at = db.Column(db.DateTime, default=datetime.utcnow)
    allergens_selected = db.Column(db.String(500), nullable=True)

@login_manager.user_loader
def load_user(user_id):
    return Restaurant.query.get(int(user_id))

with app.app_context():
    db.create_all()
    try:
        db.session.execute(db.text('ALTER TABLE restaurant ADD COLUMN is_admin BOOLEAN DEFAULT FALSE'))
        db.session.commit()
    except:
        db.session.rollback()

# ── Routes ───────────────────────────────────────────────

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/restaurants')
def restaurants():
    all_restaurants = Restaurant.query.filter_by(is_admin=False).all()
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

        base_slug = name.lower().replace(' ', '-')
        slug = base_slug
        counter = 1
        while Restaurant.query.filter_by(slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1

        if Restaurant.query.filter_by(email=email).first():
            flash('Email already registered.')
            return redirect(url_for('signup'))

        restaurant = Restaurant(
            name=name,
            email=email,
            password=generate_password_hash(password),
            slug=slug
        )
        db.session.add(restaurant)
        db.session.commit()
        login_user(restaurant)
        return redirect(url_for('dashboard'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        restaurant = Restaurant.query.filter_by(email=email).first()

        if not restaurant or not check_password_hash(restaurant.password, password):
            flash('Invalid email or password.')
            return redirect(url_for('login'))

        login_user(restaurant, remember=True)

        if restaurant.is_admin:
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))

    return render_template('login.html')

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form.get('email')
        new_password = request.form.get('new_password')

        restaurant = Restaurant.query.filter_by(email=email).first()
        if not restaurant:
            flash('No account found with that email.')
            return redirect(url_for('reset_password'))

        restaurant.password = generate_password_hash(new_password)
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

    restaurants = Restaurant.query.filter_by(is_admin=False).all()

    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    year_ago = now - timedelta(days=365)

    stats = {}
    for r in restaurants:
        visits = MenuVisit.query.filter_by(restaurant_id=r.id)
        stats[r.id] = {
            'weekly': visits.filter(MenuVisit.visited_at >= week_ago).count(),
            'monthly': visits.filter(MenuVisit.visited_at >= month_ago).count(),
            'yearly': visits.filter(MenuVisit.visited_at >= year_ago).count(),
        }

    return render_template('admin.html', restaurants=restaurants, stats=stats)

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        file = request.files.get('csv_files')
        if file and file.filename.endswith('.csv'):
            csv_content = file.read().decode('utf-8')
            current_user.csv_data = csv_content
            db.session.commit()
            flash('Menu uploaded successfully!')
        else:
            flash('Please upload a valid CSV file.')

    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    year_ago = now - timedelta(days=365)

    visits = MenuVisit.query.filter_by(restaurant_id=current_user.id)
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

    menu_url = url_for('menu', slug=current_user.slug, _external=True)
    return render_template('dashboard.html',
                           restaurant=current_user,
                           menu_url=menu_url,
                           weekly=weekly,
                           monthly=monthly,
                           yearly=yearly,
                           top_allergens=top_allergens)

@app.route('/generate-menu', methods=['GET', 'POST'])
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

    df = pd.read_csv(io.StringIO(restaurant.csv_data), sep=None, engine='python')
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