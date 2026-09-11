import os
import uuid
from flask import Flask, render_template_string, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///site.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# File upload config
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB max
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# ---------------- Models ----------------

class Admin(UserMixin, db.Model):
    __tablename__ = "admin"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Product(db.Model):
    __tablename__ = "product"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    image_filename = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

class PaymentMethod(db.Model):
    __tablename__ = "payment_method"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    order = db.Column(db.Integer, default=0)

class SiteSettings(db.Model):
    __tablename__ = "site_settings"
    id = db.Column(db.Integer, primary_key=True)
    business_name = db.Column(db.String(255), nullable=False)
    seller_email = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(50), nullable=True)
    address = db.Column(db.String(500), nullable=True)
    currency = db.Column(db.String(10), default="USD")

# ---------------- Helpers ----------------

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Admin, int(user_id))

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ---------------- Templates (inline) ----------------

BASE_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{{ settings.business_name if settings else "My Business" }}</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 0; }
    .container { max-width: 960px; margin: 0 auto; padding: 1rem; }
    header { background: #f5f5f5; padding: 1rem 0; }
    header .container { display: flex; justify-content: space-between; align-items: center; }
    nav a { margin-left: 1rem; text-decoration: none; color: #0077cc; }
    .flashes { list-style: none; padding: 0; }
    .flashes li { padding: 0.4rem 0.6rem; margin-bottom: 0.4rem; border-radius: 4px; }
    .success { background: #d4edda; color: #155724; }
    .error { background: #f8d7da; color: #721c24; }
    .products { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 1rem; }
    .product-card { border: 1px solid #ddd; padding: 0.75rem; border-radius: 6px; }
    .product-card img { max-width: 100%; height: auto; border-radius: 4px; }
    .price { font-weight: bold; }
    table { width: 100%; border-collapse: collapse; }
    th, td { border: 1px solid #ddd; padding: 0.4rem; text-align: left; }
    .simple-form label { display: block; margin-bottom: 0.6rem; }
    .simple-form input, .simple-form textarea { width: 100%; padding: 0.4rem; }
    footer { margin-top: 2rem; border-top: 1px solid #eee; padding-top: 1rem; }
  </style>
</head>
<body>
  <header>
    <div class="container">
      <h1>{{ settings.business_name if settings else "My Business" }}</h1>
      <nav>
        <a href="{{ url_for('index') }}">Home</a>
        {% if current_user.is_authenticated %}
          <a href="{{ url_for('dashboard') }}">Admin</a>
          <a href="{{ url_for('logout') }}">Logout</a>
        {% else %}
          <a href="{{ url_for('login') }}">Admin login</a>
        {% endif %}
      </nav>
    </div>
  </header>

  <main class="container">
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        <ul class="flashes">
          {% for category, msg in messages %}
            <li class="{{ category }}">{{ msg }}</li>
          {% endfor %}
        </ul>
      {% endif %}
    {% endwith %}

    {% block content %}{% endblock %}
  </main>

  <footer class="container">
    <p>
      Contact: {{ settings.seller_email if settings else "phabianbirech07@gmail.com" }}
      {% if settings and settings.phone %} | Phone: {{ settings.phone }}{% endif %}
    </p>
  </footer>
</body>
</html>
"""

INDEX_TEMPLATE = """
{% extends "base" %}
{% block content %}
<h2>Our Products</h2>

{% if products %}
  <div class="products">
    {% for p in products %}
      <div class="product-card">
        {% if p.image_filename %}
          <img src="{{ url_for('uploaded_file', filename=p.image_filename) }}" alt="{{ p.name }}">
        {% endif %}
        <h3>{{ p.name }}</h3>
        <p>{{ p.description or "" }}</p>
        <p class="price">${{ "%.2f"|format(p.price) }}</p>
      </div>
    {% endfor %}
  </div>
{% else %}
  <p>No products available at the moment.</p>
{% endif %}

<h2>Modes of Payment</h2>
{% if payments %}
  <ul>
    {% for pm in payments %}
      <li><strong>{{ pm.name }}</strong>{% if pm.details %}: {{ pm.details }}{% endif %}</li>
    {% endfor %}
  </ul>
{% else %}
  <p>No payment methods configured yet.</p>
{% endif %}

<h2>Contact</h2>
<p>
  Email: {{ settings.seller_email }}<br>
  {% if settings and settings.phone %}Phone: {{ settings.phone }}<br>{% endif %}
  {% if settings and settings.address %}Address: {{ settings.address }}{% endif %}
</p>
{% endblock %}
"""

LOGIN_TEMPLATE = """
{% extends "base" %}
{% block content %}
<h2>Admin Login</h2>
<form method="post">
  <label>Email<br><input type="email" name="email" required></label><br>
  <label>Password<br><input type="password" name="password" required></label><br>
  <button type="submit">Login</button>
</form>
{% endblock %}
"""

DASHBOARD_TEMPLATE = """
{% extends "base" %}
{% block content %}
<h2>Admin Dashboard</h2>
<p>Products: {{ products_count }} | Active payment methods: {{ payments_count }}</p>

<ul>
  <li><a href="{{ url_for('admin_products') }}">Manage Products</a></li>
  <li><a href="{{ url_for('admin_payments') }}">Manage Payment Methods</a></li>
  <li><a href="{{ url_for('admin_settings') }}">Site Settings (email, contacts, business name)</a></li>
</ul>

<p>Changes you make here are immediately visible to customers visiting the home page.</p>
{% endblock %}
"""

PRODUCTS_TEMPLATE = """
{% extends "base" %}
{% block content %}
<h2>Products</h2>

<form method="post" class="simple-form" enctype="multipart/form-data">
  <h3>Add new product</h3>
  <label>Name<br><input name="name" required></label><br>
  <label>Description<br><textarea name="description"></textarea></label><br>
  <label>Price (USD)<br><input name="price" required></label><br>
  <label>Product image (optional)<br><input type="file" name="image" accept="image/*"></label><br>
  <button type="submit">Add product</button>
</form>

<h3>Existing products</h3>
{% if products %}
  <table>
    <thead>
      <tr>
        <th>Image</th>
        <th>Name</th>
        <th>Price</th>
        <th>Active</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody>
      {% for p in products %}
      <tr>
        <td>
          {% if p.image_filename %}
            <img src="{{ url_for('uploaded_file', filename=p.image_filename) }}" width="60" alt="">
          {% endif %}
        </td>
        <td>{{ p.name }}</td>
        <td>${{ p.price }}</td>
        <td>{{ "Yes" if p.is_active else "No" }}</td>
        <td>
          <a href="{{ url_for('admin_edit_product', pid=p.id) }}">Edit</a>
          <form method="post" action="{{ url_for('admin_delete_product', pid=p.id) }}" style="display:inline;">
            <button type="submit" onclick="return confirm('Delete this product?')">Delete</button>
          </form>
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
{% else %}
  <p>No products yet.</p>
{% endif %}
{% endblock %}
"""

EDIT_PRODUCT_TEMPLATE = """
{% extends "base" %}
{% block content %}
<h2>Edit Product</h2>
<form method="post" class="simple-form" enctype="multipart/form-data">
  <label>Name<br><input name="name" value="{{ product.name }}" required></label><br>
  <label>Description<br><textarea name="description">{{ product.description or "" }}</textarea></label><br>
  <label>Price (USD)<br><input name="price" value="{{ product.price }}" required></label><br>
  <label>Replace image (optional)<br><input type="file" name="image" accept="image/*"></label><br>
  {% if product.image_filename %}
    <p>Current image:<br>
      <img src="{{ url_for('uploaded_file', filename=product.image_filename) }}" width="150" alt="">
    </p>
  {% endif %}
  <label><input type="checkbox" name="is_active" {% if product.is_active %}checked{% endif %}> Active</label><br>
  <button type="submit">Save changes</button>
</form>
<p><a href="{{ url_for('admin_products') }}">Back to products</a></p>
{% endblock %}
"""

PAYMENTS_TEMPLATE = """
{% extends "base" %}
{% block content %}
<h2>Payment Methods</h2>

<form method="post" class="simple-form">
  <h3>Add payment method</h3>
  <label>Name (e.g. PayPal, Binance Pay)<br><input name="name" required></label><br>
  <label>Details (e.g. email, wallet address, instructions)<br><textarea name="details"></textarea></label><br>
  <button type="submit">Add</button>
</form>

<h3>Current methods</h3>
{% if payments %}
  <ul>
    {% for pm in payments %}
      <li>
        <strong>{{ pm.name }}</strong> {% if pm.details %}– {{ pm.details }}{% endif %}
        ({{ "Active" if pm.is_active else "Hidden" }})
        <form method="post" action="{{ url_for('admin_toggle_payment', pmid=pm.id) }}" style="display:inline;">
          <button type="submit">{{ "Hide" if pm.is_active else "Show" }}</button>
        </form>
        <form method="post" action="{{ url_for('admin_delete_payment', pmid=pm.id) }}" style="display:inline;">
          <button type="submit" onclick="return confirm('Delete this payment method?')">Delete</button>
        </form>
      </li>
    {% endfor %}
  </ul>
{% else %}
  <p>No payment methods yet.</p>
{% endif %}
{% endblock %}
"""

SETTINGS_TEMPLATE = """
{% extends "base" %}
{% block content %}
<h2>Site Settings</h2>
<form method="post" class="simple-form">
  <label>Business name<br><input name="business_name" value="{{ settings.business_name }}" required></label><br>
  <label>Seller email<br><input type="email" name="seller_email" value="{{ settings.seller_email }}" required></label><br>
  <label>Phone<br><input name="phone" value="{{ settings.phone or '' }}"></label><br>
  <label>Address<br><textarea name="address">{{ settings.address or '' }}</textarea></label><br>
  <label>Currency (fixed to USD)<br><input name="currency" value="USD" readonly></label><br>
  <button type="submit">Save settings</button>
</form>
{% endblock %}
"""

TEMPLATES = {
    "base": BASE_TEMPLATE,
    "index": INDEX_TEMPLATE,
    "login": LOGIN_TEMPLATE,
    "dashboard": DASHBOARD_TEMPLATE,
    "products": PRODUCTS_TEMPLATE,
    "edit_product": EDIT_PRODUCT_TEMPLATE,
    "payments": PAYMENTS_TEMPLATE,
    "settings": SETTINGS_TEMPLATE,
}

def render_template(name, **context):
    return render_template_string(TEMPLATES[name], **context)

# ---------------- Routes ----------------

@app.route("/")
def index():
    products = Product.query.filter_by(is_active=True).order_by(Product.created_at.desc()).all()
    payments = PaymentMethod.query.filter_by(is_active=True).order_by(PaymentMethod.order).all()
    settings = SiteSettings.query.first()
    if not settings:
        settings = SiteSettings(
            business_name="My Business",
            seller_email="phabianbirech07@gmail.com",
            phone="",
            address="",
            currency="USD"
        )
    return render_template("index", products=products, payments=payments, settings=settings)

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        admin = Admin.query.filter_by(email=email).first()
        if admin and admin.check_password(password):
            login_user(admin)
            return redirect(url_for("dashboard"))
        flash("Invalid email or password", "error")
    return render_template("login")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out", "success")
    return redirect(url_for("index"))

@app.route("/admin")
@login_required
def dashboard():
    products_count = Product.query.count()
    payments_count = PaymentMethod.query.filter_by(is_active=True).count()
    settings = SiteSettings.query.first()
    return render_template("dashboard", products_count=products_count, payments_count=payments_count, settings=settings)

@app.route("/admin/products", methods=["GET", "POST"])
@login_required
def admin_products():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        price = request.form.get("price", "").strip()
        image_file = request.files.get("image")

        if not (name and price):
            flash("Name and price are required", "error")
        else:
            try:
                price_val = float(price)
            except ValueError:
                flash("Price must be a number", "error")
                price_val = None

            if price_val is not None:
                image_filename = None
                if image_file and allowed_file(image_file.filename):
                    ext = image_file.filename.rsplit(".", 1)[1].lower()
                    image_filename = f"{uuid.uuid4().hex}.{ext}"
                    image_file.save(os.path.join(app.config["UPLOAD_FOLDER"], image_filename))

                p = Product(
                    name=name,
                    description=description,
                    price=price_val,
                    image_filename=image_filename
                )
                db.session.add(p)
                db.session.commit()
                flash("Product added", "success")

        return redirect(url_for("admin_products"))

    products = Product.query.order_by(Product.created_at.desc()).all()
    return render_template("products", products=products)

@app.route("/admin/products/<int:pid>/edit", methods=["GET", "POST"])
@login_required
def admin_edit_product(pid):
    product = db.session.get(Product, pid)
    if not product:
        from flask import abort
        abort(404)

    if request.method == "POST":
        product.name = request.form.get("name", "").strip()
        product.description = request.form.get("description", "").strip()
        price = request.form.get("price", "").strip()
        product.is_active = request.form.get("is_active") == "on"

        image_file = request.files.get("image")
        if image_file and allowed_file(image_file.filename):
            if product.image_filename:
                old_path = os.path.join(app.config["UPLOAD_FOLDER"], product.image_filename)
                if os.path.exists(old_path):
                    os.remove(old_path)
            ext = image_file.filename.rsplit(".", 1)[1].lower()
            product.image_filename = f"{uuid.uuid4().hex}.{ext}"
            image_file.save(os.path.join(app.config["UPLOAD_FOLDER"], image_filename))

        try:
            product.price = float(price)
        except ValueError:
            flash("Price must be a number", "error")
            return render_template("edit_product", product=product)

        db.session.commit()
        flash("Product updated", "success")
        return redirect(url_for("admin_products"))

    return render_template("edit_product", product=product)

@app.route("/admin/products/<int:pid>/delete", methods=["POST"])
@login_required
def admin_delete_product(pid):
    product = db.session.get(Product, pid)
    if product:
        if product.image_filename:
            path = os.path.join(app.config["UPLOAD_FOLDER"], product.image_filename)
            if os.path.exists(path):
                os.remove(path)
        db.session.delete(product)
        db.session.commit()
        flash("Product deleted", "success")
    return redirect(url_for("admin_products"))

@app.route("/admin/payments", methods=["GET", "POST"])
@login_required
def admin_payments():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        details = request.form.get("details", "").strip()
        if name:
            pm = PaymentMethod(name=name, details=details, is_active=True)
            db.session.add(pm)
            db.session.commit()
            flash("Payment method added", "success")
        else:
            flash("Name is required", "error")
        return redirect(url_for("admin_payments"))

    payments = PaymentMethod.query.order_by(PaymentMethod.order).all()
    return render_template("payments", payments=payments)

@app.route("/admin/payments/<int:pmid>/toggle", methods=["POST"])
@login_required
def admin_toggle_payment(pmid):
    pm = db.session.get(PaymentMethod, pmid)
    if pm:
        pm.is_active = not pm.is_active
        db.session.commit()
        flash("Payment method updated", "success")
    return redirect(url_for("admin_payments"))

@app.route("/admin/payments/<int:pmid>/delete", methods=["POST"])
@login_required
def admin_delete_payment(pmid):
    pm = db.session.get(PaymentMethod, pmid)
    if pm:
        db.session.delete(pm)
        db.session.commit()
        flash("Payment method deleted", "success")
    return redirect(url_for("admin_payments"))

@app.route("/admin/settings", methods=["GET", "POST"])
@login_required
def admin_settings():
    settings = SiteSettings.query.first()
    if not settings:
        settings = SiteSettings(
            business_name="My Business",
            seller_email="phabianbirech07@gmail.com",
            phone="",
            address="",
            currency="USD"
        )
        db.session.add(settings)
        db.session.commit()

    if request.method == "POST":
        settings.business_name = request.form.get("business_name", "").strip()
        settings.seller_email = request.form.get("seller_email", "").strip()
        settings.phone = request.form.get("phone", "").strip()
        settings.address = request.form.get("address", "").strip()
        settings.currency = "USD"
        db.session.commit()
        flash("Settings updated", "success")
        return redirect(url_for("admin_settings"))

    return render_template("settings", settings=settings)

# ---------------- Init DB ----------------

def init_db():
  with app.app_context():
        db.create_all()
        if not Admin.query.first():
            admin = Admin(email="phabianbirech07@gmail.com")
            # Default password – CHANGE THIS in production or add a change-password page
            admin.set_password("admin123")
            db.session.add(admin)

            # Default site settings
            settings = SiteSettings(
                business_name="My Business",
                seller_email="phabianbirech07@gmail.com",
                phone="",
                address="",
                currency="USD"
            )
            db.session.add(settings)
            db.session.commit()
            print("Admin created: phabianbirech07@gmail.com / admin123")

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
