import os
import io
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

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

@login_manager.user_loader
def load_user(user_id):
    return Restaurant.query.get(int(user_id))

with app.app_context():
    db.create_all()

# ── Routes ───────────────────────────────────────────────

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
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

        if restaurant.is_admin:                            # ← step 5
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
    return render_template('admin.html', restaurants=restaurants)

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if request.method == 'POST':
        file = request.files.get('csv_files')
        if file and file.filename.endswith('.csv'):
            csv_content = file.read().decode('utf-8')
            current_user.csv_data = csv_content
            db.session.commit()
            flash('Menu uploaded successfully!')
        else:
            flash('Please upload a valid CSV file.')

    menu_url = url_for('menu', slug=current_user.slug, _external=True)
    return render_template('dashboard.html', restaurant=current_user, menu_url=menu_url)

@app.route('/menu/<slug>', methods=['GET', 'POST'])
def menu(slug):
    restaurant = Restaurant.query.filter_by(slug=slug).first_or_404()

    if not restaurant.csv_data:
        return render_template('no_menu.html', restaurant=restaurant)

    df = pd.read_csv(io.StringIO(restaurant.csv_data), sep=None, engine='python')
    df.columns = df.columns.str.strip().str.lower()
    NON_ALLERGEN_COLUMNS = ['dish', 'category']

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

        EXCLUDE_IF_TRUE = ['pork', 'beef', 'chicken', 'egg', 'dairy', 'fish', 'shellfish',
                           'gluten', 'peanuts', 'tree nuts', 'soy', 'sesame', 'capsaicin',
                           'piperine', 'unpasteurized (raw) cheese', 'derived protiens',
                           'cured meats']
        REQUIRE_TRUE = ['vegetarian', 'vegan', 'pregnancy safe']

        safe_results = []

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
            elif pd.notna(row.get('alternatives')) and str(row.get('alternatives')).strip():
                # find which selected allergens triggered the fail
                triggered = []
                for a in selected_allergens:
                    if a in EXCLUDE_IF_TRUE and row.get(a) == True:
                        triggered.append(a)
                    if a in REQUIRE_TRUE and row.get(a) != True:
                        triggered.append(a)

                # only show alternatives that mention the triggered allergen
                all_alts = [a.strip() for a in str(row['alternatives']).split('|')]
                relevant_alts = [
                    alt for alt in all_alts
                    if any(t in alt.lower() for t in triggered)
                ]

                if relevant_alts:
                    safe_results.append({
                        "dish": row['dish'],
                        "modified": True,
                        "modifications": relevant_alts
                    })

    return render_template('index.html', allergens=allergens, restaurant=restaurant)