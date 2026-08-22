import os
import csv
import io
from datetime import datetime
from functools import wraps

from flask import (
    Flask, request, redirect, render_template_string,
    session, send_file, url_for, abort
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "SCM_PRO_V8_CHANGE_THIS")

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///scm_v8.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


# =========================
# DATABASE MODELS
# =========================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), default="staff")
    active = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    price = db.Column(db.Float, default=0)
    cost = db.Column(db.Float, default=0)
    minimum = db.Column(db.Integer, default=0)
    supplier = db.Column(db.String(150), default="")
    category = db.Column(db.String(100), default="")
    location = db.Column(db.String(100), default="")


class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(60), default="")
    email = db.Column(db.String(150), default="")
    address = db.Column(db.String(250), default="")
    rating = db.Column(db.Float, default=5)


class StockLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item = db.Column(db.String(150))
    action = db.Column(db.String(30))
    quantity = db.Column(db.Integer)
    note = db.Column(db.String(250), default="")
    user = db.Column(db.String(80), default="")
    date = db.Column(db.DateTime, default=datetime.utcnow)


class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_no = db.Column(db.String(80))
    customer = db.Column(db.String(150), default="")
    item = db.Column(db.String(150))
    quantity = db.Column(db.Integer)
    total = db.Column(db.Float)
    profit = db.Column(db.Float)
    date = db.Column(db.DateTime, default=datetime.utcnow)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    po_no = db.Column(db.String(80))
    item = db.Column(db.String(150))
    quantity = db.Column(db.Integer)
    supplier = db.Column(db.String(150))
    status = db.Column(db.String(30), default="Pending")
    date = db.Column(db.DateTime, default=datetime.utcnow)


class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_no = db.Column(db.String(80))
    customer = db.Column(db.String(150))
    item = db.Column(db.String(150))
    quantity = db.Column(db.Integer)
    amount = db.Column(db.Float)
    date = db.Column(db.DateTime, default=datetime.utcnow)


class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80))
    action = db.Column(db.String(250))
    date = db.Column(db.DateTime, default=datetime.utcnow)


with app.app_context():
    db.create_all()

    if not User.query.filter_by(username="admin").first():
        u = User(username="admin", role="admin")
        u.set_password("admin123")
        db.session.add(u)

    if not User.query.filter_by(username="manager").first():
        u = User(username="manager", role="manager")
        u.set_password("manager123")
        db.session.add(u)

    if not User.query.filter_by(username="staff").first():
        u = User(username="staff", role="staff")
        u.set_password("staff123")
        db.session.add(u)

    db.session.commit()


# =========================
# UI
# =========================

STYLE = """
<meta name="viewport" content="width=device-width,initial-scale=1">

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<style>
*{box-sizing:border-box}

body{
margin:0;
font-family:Arial,sans-serif;
background:#f1f5f9;
color:#111827
}

nav{
position:sticky;
top:0;
z-index:50;
background:#111827;
padding:10px;
display:flex;
gap:7px;
flex-wrap:wrap
}

nav a{
color:white;
text-decoration:none;
padding:10px 12px;
border-radius:9px;
font-size:14px
}

nav a:hover{background:#374151}

main{
max-width:1250px;
margin:auto;
padding:18px
}

h1{margin-top:8px}

.grid{
display:grid;
grid-template-columns:
repeat(auto-fit,minmax(170px,1fr));
gap:14px
}

.card{
background:white;
border-radius:18px;
padding:18px;
margin-bottom:16px;
box-shadow:0 3px 15px #00000012
}

.big{
font-size:26px;
font-weight:bold;
margin-top:8px
}

form{
background:white;
padding:18px;
border-radius:18px;
margin:15px 0
}

input,select,textarea{
background:#ffffff !important;
color:#111827 !important;
-webkit-text-fill-color:#111827 !important;
caret-color:#111827 !important;
border:1px solid #cbd5e1;
}
font-size:15px
}

button,.btn{
border:0;
background:#111827;
color:white;
padding:11px 16px;
border-radius:9px;
text-decoration:none;
display:inline-block;
cursor:pointer;
margin:4px
}

.green{background:#15803d}
.blue{background:#1d4ed8}
.red{background:#b91c1c}
.orange{background:#c2410c}

table{
width:100%;
border-collapse:collapse;
background:white
}

th,td{
padding:11px;
border-bottom:1px solid #e5e7eb;
text-align:left
}

.low{color:#dc2626;font-weight:bold}
.ok{color:#15803d;font-weight:bold}

.alert{
padding:14px;
background:#fee2e2;
color:#991b1b;
border-radius:12px;
margin:12px 0
}

.success{
padding:14px;
background:#dcfce7;
color:#166534;
border-radius:12px;
margin:12px 0
}

.badge{
padding:5px 9px;
border-radius:20px;
background:#e5e7eb;
font-size:12px
}

@media(max-width:650px){
nav{
display:grid;
grid-template-columns:repeat(2,1fr)
}

table{
font-size:12px
}

th,td{
padding:8px
}
}
</style>
"""


NAV = """
<nav>
<a href="/">📊 Dashboard</a>
<a href="/inventory">📦 Inventory</a>
<a href="/stock">🔄 Stock</a>
<a href="/sales">💵 Sales</a>
<a href="/orders">📋 Purchase Orders</a>
<a href="/suppliers">🏭 Suppliers</a>
<a href="/invoices">🧾 Invoices</a>
<a href="/reports">📈 Analytics</a>
{% if session.get("role")=="admin" %}
<a href="/users">👥 Users</a>
<a href="/activity">🕒 Activity</a>
{% endif %}
<a href="/export">📥 Export</a>
<a href="/logout">🚪 Logout</a>
</nav>
"""


LOGIN = STYLE + """
<main style="max-width:430px;margin:70px auto">
<div class="card">

<h1>🔐 SCM PRO V8</h1>

<p>Enterprise Supply Chain Management</p>

<form method="post">

<input
name="username"
placeholder="Username"
autocomplete="username"
required>

<input
name="password"
type="password"
placeholder="Password"
autocomplete="current-password"
required>

<button style="width:100%">
🚀 Login
</button>

</form>

<p><b>Demo Accounts</b></p>
<p>Admin: admin / admin123</p>
<p>Manager: manager / manager123</p>
<p>Staff: staff / staff123</p>

</div>
</main>
"""


# =========================
# HELPERS
# =========================

def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return db.session.get(User, uid)


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            return redirect("/login")
        return fn(*args, **kwargs)
    return wrapper


def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_user()

            if not user:
                return redirect("/login")

            if user.role not in roles:
                return "❌ Access denied", 403

            return fn(*args, **kwargs)

        return wrapper
    return decorator


def log(action):
    user = current_user()
    db.session.add(
        Activity(
            username=user.username if user else "system",
            action=action
        )
    )


def render_page(body, **data):
    return render_template_string(
        STYLE + NAV + "<main>" + body + "</main>",
        **data
    )


# =========================
# AUTH
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if current_user():
        return redirect("/dashboard")

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()

        if user and user.active and user.check_password(password):

            session["user_id"] = user.id
            session["role"] = user.role
            session["username"] = user.username

            log("Logged in")

            db.session.commit()

            return redirect("/dashboard")

        return render_template_string(
            LOGIN +
            '<main><div class="alert">❌ Invalid username or password</div></main>'
        )

    return LOGIN


@app.route("/logout")
def logout():

    if current_user():
        log("Logged out")
        db.session.commit()

    session.clear()

    return redirect("/login")


# =========================
# DASHBOARD
# =========================

@app.route("/")
@app.route("/dashboard")
@login_required
def dashboard():

    items = Item.query.all()
    suppliers = Supplier.query.all()
    sales = Sale.query.all()

    stock_value = sum(
        x.quantity * x.price for x in items
    )

    cost_value = sum(
        x.quantity * x.cost for x in items
    )

    revenue = sum(x.total for x in sales)
    profit = sum(x.profit for x in sales)

    low = [
        x for x in items
        if x.quantity <= x.minimum
    ]

    pending = Order.query.filter_by(
        status="Pending"
    ).count()

    labels = [x.name for x in items]
    quantities = [x.quantity for x in items]

    return render_page("""

<h1>📊 SCM PRO V10 Dashboard</h1>

<div class="card">
<h2>🔎 Global Search</h2>

<input
id="globalSearch"
type="text"
placeholder="Search inventory, supplier, sale, order or invoice..."
autocomplete="off"
style="width:100%;box-sizing:border-box;color:#111827!important;background:#fff!important;"
>

<div id="globalResults" style="margin-top:12px;"></div>
</div>

<script>
let searchTimer;

document.getElementById("globalSearch").addEventListener("input", function () {

    clearTimeout(searchTimer);

    const q = this.value.trim();
    const box = document.getElementById("globalResults");

    if (!q) {
        box.innerHTML = "";
        return;
    }

    box.innerHTML = "🔎 Searching...";

    searchTimer = setTimeout(async () => {

        try {
            const response = await fetch(
                "/api/search?q=" + encodeURIComponent(q)
            );

            const data = await response.json();

            if (!data.results || data.results.length === 0) {
                box.innerHTML = "<p>❌ No results found</p>";
                return;
            }

            box.innerHTML = data.results.map(x => `
                <div style="
                    padding:12px;
                    margin:6px 0;
                    border:1px solid #ddd;
                    border-radius:8px;
                    background:#fff;
                    color:#111827;
                ">
                    <b>${x.type}</b> — ${x.name}<br>
                    <small>${x.detail}</small>
                </div>
            `).join("");

        } catch (error) {
            box.innerHTML = "⚠️ Search error";
        }

    }, 250);

});
</script>


<div class="grid">

<div class="card">
📦 Items
<div class="big">{{items|length}}</div>
</div>

<div class="card">
🏭 Suppliers
<div class="big">{{suppliers|length}}</div>
</div>

<div class="card">
💰 Stock Value
<div class="big">₹{{"%.2f"|format(stock_value)}}</div>
</div>

<div class="card">
🚨 Low Stock
<div class="big">{{low|length}}</div>
</div>

<div class="card">
💵 Revenue
<div class="big">₹{{"%.2f"|format(revenue)}}</div>
</div>

<div class="card">
📈 Profit
<div class="big">₹{{"%.2f"|format(profit)}}</div>
</div>

<div class="card">
📋 Pending PO
<div class="big">{{pending}}</div>
</div>

<div class="card">
🏦 Inventory Cost
<div class="big">₹{{"%.2f"|format(cost_value)}}</div>
</div>

</div>

{% if low %}
<div class="alert">
<b>🚨 LOW STOCK ALERT</b><br>
{% for x in low %}
{{x.name}} — {{x.quantity}} / minimum {{x.minimum}}<br>
{% endfor %}
</div>
{% endif %}

<div class="card">
<h2>📊 Inventory Overview</h2>
<canvas id="inventoryChart"></canvas>
</div>

<div class="grid">

<div class="card">
<h3>⚡ Quick Actions</h3>

<a class="btn" href="/inventory">➕ Add Item</a>
<a class="btn green" href="/stock">🔄 Stock Update</a>
<a class="btn blue" href="/sales">💵 New Sale</a>
<a class="btn orange" href="/invoices">🧾 Invoice</a>

</div>

<div class="card">
<h3>👤 Current User</h3>
<p>{{session.get("username")}}</p>
<p>Role: <b>{{session.get("role")}}</b></p>
</div>

</div>

<script>
new Chart(
document.getElementById("inventoryChart"),
{
type:"bar",
data:{
labels:{{labels|tojson}},
datasets:[
{
label:"Current Stock",
data:{{quantities|tojson}}
}
]
},
options:{
responsive:true,
plugins:{
legend:{display:true}
}
}
}
);
</script>
""",
        items=items,
        suppliers=suppliers,
        stock_value=stock_value,
        cost_value=cost_value,
        revenue=revenue,
        profit=profit,
        low=low,
        pending=pending,
        labels=labels,
        quantities=quantities
    )


# =========================
# INVENTORY
# =========================

@app.route("/inventory", methods=["GET", "POST"])
@login_required
def inventory():

    if request.method == "POST":

        try:

            sku = request.form["sku"].strip()

            if Item.query.filter_by(sku=sku).first():
                return "❌ SKU already exists"

            item = Item(
                sku=sku,
                name=request.form["name"],
                quantity=int(request.form["quantity"]),
                price=float(request.form["price"]),
                cost=float(request.form["cost"]),
                minimum=int(request.form["minimum"]),
                supplier=request.form.get("supplier", ""),
                category=request.form.get("category", ""),
                location=request.form.get("location", "")
            )

            db.session.add(item)

            supplier = request.form.get("supplier", "").strip()

            if supplier and not Supplier.query.filter_by(name=supplier).first():
                db.session.add(
                    Supplier(name=supplier)
                )

            log(f"Added inventory item: {item.name}")

            db.session.commit()

            return redirect("/inventory")

        except Exception as e:

            db.session.rollback()

            return "❌ Invalid item data: " + str(e)

    q = request.args.get("q", "").lower().strip()

    items = Item.query.order_by(
        Item.id.desc()
    ).all()

    if q:
        items = [
            x for x in items
            if q in x.name.lower()
            or q in x.sku.lower()
            or q in x.supplier.lower()
            or q in x.category.lower()
        ]

    return render_page("""
<h1>📦 Inventory Management</h1>

<form>
<input
name="q"
value="{{q}}"
placeholder="🔎 Search SKU, item, supplier or category">

<button>Search</button>
</form>

<form method="post">

<h2>➕ Add Inventory Item</h2>

<input name="sku" placeholder="SKU / Product Code" required>

<input name="name" placeholder="Item Name" required>

<input
name="quantity"
type="number"
min="0"
placeholder="Opening Quantity"
required>

<input
name="price"
type="number"
step="0.01"
min="0"
placeholder="Selling Price"
required>

<input
name="cost"
type="number"
step="0.01"
min="0"
placeholder="Purchase Cost"
required>

<input
name="minimum"
type="number"
min="0"
placeholder="Minimum Stock"
required>

<input name="supplier" placeholder="Supplier">

<input name="category" placeholder="Category">

<input name="location" placeholder="Warehouse / Location">

<button>➕ Add Item</button>

</form>

<div class="card">

<table>

<tr>
<th>SKU</th>
<th>Item</th>
<th>Qty</th>
<th>Price</th>
<th>Category</th>
<th>Supplier</th>
<th>Status</th>
</tr>

{% for x in items %}

<tr>

<td>{{x.sku}}</td>

<td>{{x.name}}</td>

<td>{{x.quantity}}</td>

<td>₹{{"%.2f"|format(x.price)}}</td>

<td>{{x.category}}</td>

<td>{{x.supplier}}</td>

<td class="{{'low' if x.quantity<=x.minimum else 'ok'}}">

{{"⚠️ LOW" if x.quantity<=x.minimum else "✅ OK"}}

</td>

</tr>

{% endfor %}

</table>

</div>
""", items=items, q=q)


# =========================
# STOCK
# =========================

@app.route("/stock", methods=["GET", "POST"])
@login_required
def stock():

    if request.method == "POST":

        item = db.session.get(
            Item,
            int(request.form["item"])
        )

        quantity = int(
            request.form["quantity"]
        )

        action = request.form["action"]

        if not item:
            return "❌ Item not found"

        if quantity <= 0:
            return "❌ Quantity must be positive"

        if action == "OUT":

            if quantity > item.quantity:
                return "❌ Insufficient stock"

            item.quantity -= quantity

        else:

            item.quantity += quantity

        db.session.add(
            StockLog(
                item=item.name,
                action=action,
                quantity=quantity,
                note=request.form.get("note", ""),
                user=session["username"]
            )
        )

        log(
            f"Stock {action}: {item.name} x {quantity}"
        )

        db.session.commit()

        return redirect("/stock")

    items = Item.query.all()

    logs = StockLog.query.order_by(
        StockLog.date.desc()
    ).limit(100).all()

    return render_page("""
<h1>🔄 Stock IN / OUT</h1>

<form method="post">

<select name="item" required>

{% for x in items %}

<option value="{{x.id}}">
{{x.name}} — {{x.quantity}} available
</option>

{% endfor %}

</select>

<input
name="quantity"
type="number"
min="1"
placeholder="Quantity"
required>

<select name="action">

<option value="IN">📥 Stock IN</option>
<option value="OUT">📤 Stock OUT</option>

</select>

<input name="note" placeholder="Note / Reason">

<button>Update Stock</button>

</form>

<h2>🕒 Stock History</h2>

<table>

<tr>
<th>Item</th>
<th>Action</th>
<th>Qty</th>
<th>User</th>
<th>Date</th>
</tr>

{% for x in logs %}

<tr>

<td>{{x.item}}</td>
<td>{{x.action}}</td>
<td>{{x.quantity}}</td>
<td>{{x.user}}</td>
<td>{{x.date}}</td>

</tr>

{% endfor %}

</table>
""", items=items, logs=logs)


# =========================
# SALES
# =========================

@app.route("/sales", methods=["GET", "POST"])
@login_required
def sales():

    if request.method == "POST":
        try:
            item_name = request.form.get("item_name", "").strip()
            quantity = int(request.form.get("quantity", "0"))
            customer = request.form.get("customer", "").strip() or "Walk-in Customer"

            if not item_name:
                return "❌ Please enter an item name", 400

            if quantity <= 0:
                return "❌ Invalid quantity", 400

            item = Item.query.filter(
                db.func.lower(Item.name) == item_name.lower()
            ).first()

            if not item:
                return "❌ Item not found in Inventory. Please add the item first.", 400

            if quantity > item.quantity:
                return "❌ Insufficient stock", 400

            total = quantity * item.price
            profit = quantity * (item.price - item.cost)

            invoice_no = "INV-" + datetime.now().strftime("%Y%m%d%H%M%S")

            item.quantity -= quantity

            sale = Sale(
                invoice_no=invoice_no,
                customer=customer,
                item=item.name,
                quantity=quantity,
                total=total,
                profit=profit
            )

            db.session.add(sale)
            log(f"Sale: {item.name} x {quantity}")
            db.session.commit()

            return redirect(url_for("invoice", invoice_no=invoice_no))

        except (ValueError, TypeError):
            return "❌ Please enter a valid quantity", 400
        except Exception as e:
            db.session.rollback()
            return "❌ Sale failed: " + str(e), 500

    items = Item.query.all()

    sales = Sale.query.order_by(
        Sale.date.desc()
    ).limit(100).all()

    return render_page("""
<h1>💵 Sales & Profit</h1>

<form method="post">

<label>Customer Name</label>
<input
name="customer"
placeholder="Customer Name">

<label>Item Name</label>
<input
name="item_name"
list="salesItems"
placeholder="Type item name"
required>

<datalist id="salesItems">
{% for x in items %}
<option value="{{x.name}}">₹{{x.price}} — Stock {{x.quantity}}</option>
{% endfor %}
</datalist>

<label>Quantity</label>
<input
name="quantity"
type="number"
min="1"
placeholder="Quantity"
required>

<button type="submit">💵 Record Sale</button>

</form>

<table>

<tr>
<th>Invoice</th>
<th>Customer</th>
<th>Item</th>
<th>Qty</th>
<th>Revenue</th>
<th>Profit</th>
<th>Date</th>
</tr>

{% for x in sales %}
<tr>
<td>{{x.invoice_no}}</td>
<td>{{x.customer}}</td>
<td>{{x.item}}</td>
<td>{{x.quantity}}</td>
<td>₹{{"%.2f"|format(x.total)}}</td>
<td>₹{{"%.2f"|format(x.profit)}}</td>
<td>{{x.date}}</td>
</tr>
{% endfor %}

</table>
""", items=items, sales=sales)


# =========================
# PURCHASE ORDERS
# =========================

@app.route("/orders", methods=["GET", "POST"])
@login_required
def orders():

    if request.method == "POST":

        po_no = (
            "PO-" +
            datetime.now().strftime("%Y%m%d%H%M%S")
        )

        order = Order(
            po_no=po_no,
            item=request.form["item"],
            quantity=int(request.form["quantity"]),
            supplier=request.form["supplier"],
            status="Pending"
        )

        db.session.add(order)

        log(
            f"Created PO {po_no}"
        )

        db.session.commit()

        return redirect("/orders")

    orders = Order.query.order_by(
        Order.date.desc()
    ).all()

    suppliers = Supplier.query.all()

    return render_page("""
<h1>📋 Purchase Orders</h1>

<form method="post">

<input
name="item"
placeholder="Item Name"
required>

<input
name="quantity"
type="number"
min="1"
placeholder="Quantity"
required>

<select name="supplier" required>

{% for s in suppliers %}

<option value="{{s.name}}">
{{s.name}}
</option>

{% endfor %}

</select>

<button>➕ Create PO</button>

</form>

<table>

<tr>
<th>PO</th>
<th>Item</th>
<th>Qty</th>
<th>Supplier</th>
<th>Status</th>
<th>Date</th>
<th>Action</th>
</tr>

{% for x in orders %}

<tr>

<td>{{x.po_no}}</td>
<td>{{x.item}}</td>
<td>{{x.quantity}}</td>
<td>{{x.supplier}}</td>

<td>
<span class="badge">
{{x.status}}
</span>
</td>

<td>{{x.date}}</td>

<td>

<form method="post"
action="/order/{{x.id}}"
style="padding:0;margin:0">

<select name="status">

<option>Pending</option>
<option>Approved</option>
<option>Received</option>
<option>Cancelled</option>

</select>

<button>Update</button>

</form>

</td>

</tr>

{% endfor %}

</table>
""", orders=orders, suppliers=suppliers)


@app.post("/order/<int:id>")
@login_required
def order_update(id):

    order = db.session.get(Order, id)

    if not order:
        abort(404)

    old = order.status
    new = request.form["status"]

    order.status = new

    # When PO becomes Received, add stock once.
    if new == "Received" and old != "Received":

        item = Item.query.filter(
            (Item.name == order.item)
            | (Item.sku == order.item)
        ).first()

        if item:
            item.quantity += order.quantity

            db.session.add(
                StockLog(
                    item=item.name,
                    action="IN",
                    quantity=order.quantity,
                    note=f"PO {order.po_no} received",
                    user=session["username"]
                )
            )

    log(
        f"PO {order.po_no}: {old} → {new}"
    )

    db.session.commit()

    return redirect("/orders")


# =========================
# SUPPLIERS
# =========================

@app.route("/suppliers", methods=["GET", "POST"])
@login_required
def suppliers():

    if request.method == "POST":

        name = request.form["name"].strip()

        if not Supplier.query.filter_by(
            name=name
        ).first():

            db.session.add(
                Supplier(
                    name=name,
                    phone=request.form.get("phone", ""),
                    email=request.form.get("email", ""),
                    address=request.form.get("address", ""),
                    rating=float(
                        request.form.get("rating", 5)
                    )
                )
            )

            log(
                f"Added supplier: {name}"
            )

            db.session.commit()

        return redirect("/suppliers")

    suppliers = Supplier.query.order_by(
        Supplier.name
    ).all()

    return render_page("""
<h1>🏭 Supplier Management</h1>

<form method="post">

<input name="name"
placeholder="Supplier Name"
required>

<input name="phone"
placeholder="Phone">

<input name="email"
placeholder="Email">

<input name="address"
placeholder="Address">

<input
name="rating"
type="number"
min="0"
max="5"
step=".1"
placeholder="Rating">

<button>➕ Add Supplier</button>

</form>

<table>

<tr>
<th>Supplier</th>
<th>Phone</th>
<th>Email</th>
<th>Address</th>
<th>Rating</th>
</tr>

{% for x in suppliers %}

<tr>

<td>{{x.name}}</td>
<td>{{x.phone}}</td>
<td>{{x.email}}</td>
<td>{{x.address}}</td>
<td>⭐ {{x.rating}}</td>

</tr>

{% endfor %}

</table>
""", suppliers=suppliers)


# =========================
# INVOICE
# =========================

@app.route("/invoices", methods=["GET", "POST"])
@login_required
def invoices():

    if request.method == "POST":

        item = db.session.get(
            Item,
            int(request.form["item"])
        )

        quantity = int(
            request.form["quantity"]
        )

        customer = request.form["customer"]

        if not item:
            return "❌ Item not found"

        if quantity > item.quantity:
            return "❌ Insufficient stock"

        invoice_no = (
            "INV-" +
            datetime.now().strftime("%Y%m%d%H%M%S")
        )

        amount = quantity * item.price

        item.quantity -= quantity

        inv = Invoice(
            invoice_no=invoice_no,
            customer=customer,
            item=item.name,
            quantity=quantity,
            amount=amount
        )

        db.session.add(inv)

        db.session.add(
            StockLog(
                item=item.name,
                action="OUT",
                quantity=quantity,
                note=f"Invoice {invoice_no}",
                user=session["username"]
            )
        )

        log(
            f"Generated invoice {invoice_no}"
        )

        db.session.commit()

        return redirect(
            url_for(
                "invoice",
                invoice_no=invoice_no
            )
        )

    items = Item.query.all()

    invoices = Invoice.query.order_by(
        Invoice.date.desc()
    ).all()

    return render_page("""
<h1>🧾 Invoice Center</h1>

<form method="post">

<input
name="customer"
placeholder="Customer Name"
required>

<select name="item">

{% for x in items %}

<option value="{{x.id}}">
{{x.name}} — ₹{{x.price}}
</option>

{% endfor %}

</select>

<input
name="quantity"
type="number"
min="1"
placeholder="Quantity"
required>

<button>🧾 Generate Invoice</button>

</form>

<h2>Previous Invoices</h2>

<table>

<tr>
<th>Invoice</th>
<th>Customer</th>
<th>Item</th>
<th>Qty</th>
<th>Total</th>
<th>Date</th>
</tr>

{% for x in invoices %}

<tr>

<td>
<a href="/invoice/{{x.invoice_no}}">
{{x.invoice_no}}
</a>
</td>

<td>{{x.customer}}</td>
<td>{{x.item}}</td>
<td>{{x.quantity}}</td>
<td>₹{{"%.2f"|format(x.amount)}}</td>
<td>{{x.date}}</td>

</tr>

{% endfor %}

</table>
""", items=items, invoices=invoices)


@app.route("/invoice/<invoice_no>")
@login_required
def invoice(invoice_no):

    inv = Invoice.query.filter_by(
        invoice_no=invoice_no
    ).first()

    if not inv:
        abort(404)

    return render_template_string(
        STYLE + """
<main style="max-width:750px;margin:auto">

<div class="card">

<h1>🧾 SCM PRO V8</h1>
<h2>Tax / Sales Invoice</h2>

<hr>

<p>
<b>Invoice:</b> {{inv.invoice_no}}
</p>

<p>
<b>Date:</b> {{inv.date}}
</p>

<p>
<b>Customer:</b> {{inv.customer}}
</p>

<table>

<tr>
<th>Item</th>
<th>Qty</th>
<th>Rate</th>
<th>Total</th>
</tr>

<tr>
<td>{{inv.item}}</td>
<td>{{inv.quantity}}</td>
<td>₹{{"%.2f"|format(inv.amount/inv.quantity)}}</td>
<td>₹{{"%.2f"|format(inv.amount)}}</td>
</tr>

</table>

<h2 style="text-align:right">
Total: ₹{{"%.2f"|format(inv.amount)}}
</h2>

<button onclick="window.print()">
🖨️ Print / Save PDF
</button>

<a class="btn" href="/invoices">
← Back
</a>

</div>

</main>
""",
        inv=inv
    )


# =========================
# ANALYTICS
# =========================

@app.route("/reports")
@login_required
def reports():

    items = Item.query.all()
    sales = Sale.query.order_by(
        Sale.date
    ).all()

    revenue = sum(x.total for x in sales)
    profit = sum(x.profit for x in sales)
    stock = sum(
        x.quantity * x.price for x in items
    )

    labels = [
        str(x.date)[:10]
        for x in sales
    ]

    salesdata = [
        x.total for x in sales
    ]

    profitdata = [
        x.profit for x in sales
    ]

    return render_page("""
<h1>📈 Advanced Analytics</h1>

<div class="grid">

<div class="card">
💵 Revenue
<div class="big">
₹{{"%.2f"|format(revenue)}}
</div>
</div>

<div class="card">
📈 Profit
<div class="big">
₹{{"%.2f"|format(profit)}}
</div>
</div>

<div class="card">
💰 Stock Value
<div class="big">
₹{{"%.2f"|format(stock)}}
</div>
</div>

</div>

<div class="card">
<h2>📊 Revenue & Profit</h2>
<canvas id="salesChart"></canvas>
</div>

<div class="card">
<h2>📦 Stock Distribution</h2>
<canvas id="stockChart"></canvas>
</div>

<script>

new Chart(
document.getElementById("salesChart"),
{
type:"line",
data:{
labels:{{labels|tojson}},
datasets:[
{
label:"Revenue",
data:{{salesdata|tojson}},
tension:.3
},
{
label:"Profit",
data:{{profitdata|tojson}},
tension:.3
}
]
},
options:{responsive:true}
}
);

new Chart(
document.getElementById("stockChart"),
{
type:"doughnut",
data:{
labels:{{stocklabels|tojson}},
datasets:[
{
data:{{stockdata|tojson}}
}
]
},
options:{responsive:true}
}
);

</script>
""",
        revenue=revenue,
        profit=profit,
        stock=stock,
        labels=labels,
        salesdata=salesdata,
        profitdata=profitdata,
        stocklabels=[x.name for x in items],
        stockdata=[x.quantity for x in items]
    )


# =========================
# USER MANAGEMENT
# =========================

@app.route("/users", methods=["GET", "POST"])
@role_required("admin")
def users():

    if request.method == "POST":

        username = request.form["username"].strip()

        if User.query.filter_by(
            username=username
        ).first():

            return "❌ Username already exists"

        u = User(
            username=username,
            role=request.form["role"]
        )

        u.set_password(
            request.form["password"]
        )

        db.session.add(u)

        log(
            f"Created user: {username}"
        )

        db.session.commit()

        return redirect("/users")

    users = User.query.all()

    return render_page("""
<h1>👥 User Management</h1>

<form method="post">

<input
name="username"
placeholder="Username"
required>

<input
name="password"
type="password"
placeholder="Password"
required>

<select name="role">

<option value="staff">Staff</option>
<option value="manager">Manager</option>
<option value="admin">Admin</option>

</select>

<button>➕ Create User</button>

</form>

<table>

<tr>
<th>Username</th>
<th>Role</th>
<th>Status</th>
</tr>

{% for x in users %}

<tr>

<td>{{x.username}}</td>
<td>{{x.role}}</td>
<td>
{{"Active" if x.active else "Disabled"}}
</td>

</tr>

{% endfor %}

</table>
""", users=users)


# =========================
# ACTIVITY LOG
# =========================

@app.route("/activity")
@role_required("admin")
def activity():

    logs = Activity.query.order_by(
        Activity.date.desc()
    ).limit(300).all()

    return render_page("""
<h1>🕒 Audit / Activity Log</h1>

<table>

<tr>
<th>User</th>
<th>Action</th>
<th>Date</th>
</tr>

{% for x in logs %}

<tr>
<td>{{x.username}}</td>
<td>{{x.action}}</td>
<td>{{x.date}}</td>
</tr>

{% endfor %}

</table>
""", logs=logs)


# =========================
# CSV EXPORT
# =========================

@app.route("/export")
@login_required
def export():

    output = io.StringIO()

    writer = csv.writer(output)

    writer.writerow([
        "SKU",
        "Item",
        "Quantity",
        "Selling Price",
        "Cost",
        "Minimum",
        "Supplier",
        "Category",
        "Location"
    ])

    for x in Item.query.all():

        writer.writerow([
            x.sku,
            x.name,
            x.quantity,
            x.price,
            x.cost,
            x.minimum,
            x.supplier,
            x.category,
            x.location
        ])

    memory = io.BytesIO(
        output.getvalue().encode()
    )

    memory.seek(0)

    return send_file(
        memory,
        as_attachment=True,
        download_name="SCM_PRO_V8_Inventory.csv",
        mimetype="text/csv"
    )


# =========================
# HEALTH
# =========================

@app.route("/health")
def health():
    return {
        "status": "ok",
        "application": "SCM Pro",
        "version": "V8"
    }


# =========================
# RUN
# =========================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080))
    )

# =========================
# SCM PRO V9 UPGRADE PACK
# =========================


@app.route("/api/search")
@login_required
def global_search():
    q = request.args.get("q", "").strip()

    if not q:
        return {"query": "", "results": []}

    like = f"%{q}%"
    results = []

    for x in Item.query.filter(
        db.or_(
            Item.sku.ilike(like),
            Item.name.ilike(like),
            Item.category.ilike(like),
            Item.supplier.ilike(like),
            Item.location.ilike(like)
        )
    ).limit(20).all():
        results.append({
            "type": "Inventory",
            "name": x.name,
            "detail": f"SKU: {x.sku} | Stock: {x.quantity}"
        })

    for x in Supplier.query.filter(
        db.or_(
            Supplier.name.ilike(like),
            Supplier.phone.ilike(like),
            Supplier.email.ilike(like)
        )
    ).limit(20).all():
        results.append({
            "type": "Supplier",
            "name": x.name,
            "detail": x.phone or x.email or ""
        })

    for x in Sale.query.filter(
        db.or_(
            Sale.invoice_no.ilike(like),
            Sale.customer.ilike(like),
            Sale.item.ilike(like)
        )
    ).limit(20).all():
        results.append({
            "type": "Sale",
            "name": x.invoice_no,
            "detail": f"{x.customer} | ₹{x.total}"
        })

    for x in Order.query.filter(
        db.or_(
            Order.po_no.ilike(like),
            Order.item.ilike(like),
            Order.supplier.ilike(like),
            Order.status.ilike(like)
        )
    ).limit(20).all():
        results.append({
            "type": "Order",
            "name": x.po_no,
            "detail": f"{x.item} | {x.status}"
        })

    for x in Invoice.query.filter(
        db.or_(
            Invoice.invoice_no.ilike(like),
            Invoice.customer.ilike(like)
        )
    ).limit(20).all():
        results.append({
            "type": "Invoice",
            "name": x.invoice_no,
            "detail": x.customer
        })

    return {
        "query": q,
        "count": len(results),
        "results": results[:100]
    }

@app.route("/api/stats")
@login_required
def api_stats():
    items = Item.query.all()
    sales = Sale.query.all()

    return {
        "items": len(items),
        "stock_units": sum(x.quantity for x in items),
        "stock_value": round(sum(x.quantity*x.price for x in items), 2),
        "revenue": round(sum(x.total for x in sales), 2),
        "profit": round(sum(x.profit for x in sales), 2),
        "low_stock": len([
            x for x in items if x.quantity <= x.minimum
        ])
    }


@app.route("/api/inventory")
@login_required
def api_inventory():

    return {
        "items": [
            {
                "id": x.id,
                "sku": x.sku,
                "name": x.name,
                "quantity": x.quantity,
                "price": x.price,
                "cost": x.cost,
                "minimum": x.minimum,
                "supplier": x.supplier,
                "category": x.category,
                "location": x.location,
                "low_stock": x.quantity <= x.minimum
            }
            for x in Item.query.all()
        ]
    }


@app.route("/api/sales")
@login_required
def api_sales():

    return {
        "sales": [
            {
                "invoice": x.invoice_no,
                "customer": x.customer,
                "item": x.item,
                "quantity": x.quantity,
                "revenue": x.total,
                "profit": x.profit,
                "date": str(x.date)
            }
            for x in Sale.query.order_by(
                Sale.date.desc()
            ).limit(200).all()
        ]
    }


@app.route("/api/low-stock")
@login_required
def api_low_stock():

    items = [
        {
            "sku": x.sku,
            "name": x.name,
            "quantity": x.quantity,
            "minimum": x.minimum
        }
        for x in Item.query.all()
        if x.quantity <= x.minimum
    ]

    return {
        "count": len(items),
        "items": items
    }


@app.route("/api/orders")
@login_required
def api_orders():

    return {
        "orders": [
            {
                "po": x.po_no,
                "item": x.item,
                "quantity": x.quantity,
                "supplier": x.supplier,
                "status": x.status,
                "date": str(x.date)
            }
            for x in Order.query.order_by(
                Order.date.desc()
            ).limit(200).all()
        ]
    }


@app.route("/api/suppliers")
@login_required
def api_suppliers():

    return {
        "suppliers": [
            {
                "name": x.name,
                "phone": x.phone,
                "email": x.email,
                "address": x.address,
                "rating": x.rating
            }
            for x in Supplier.query.order_by(
                Supplier.name
            ).all()
        ]
    }


@app.route("/api/activity")
@role_required("admin")
def api_activity():

    return {
        "activity": [
            {
                "user": x.username,
                "action": x.action,
                "date": str(x.date)
            }
            for x in Activity.query.order_by(
                Activity.date.desc()
            ).limit(300).all()
        ]
    }


@app.route("/v9")
@login_required
def v9():

    return render_page("""
<h1>🚀 SCM PRO V9</h1>

<div class="grid">

<div class="card">
<h3>📊 Live Dashboard</h3>
<p id="items">Loading...</p>
</div>

<div class="card">
<h3>📦 Stock Units</h3>
<p id="stock">Loading...</p>
</div>

<div class="card">
<h3>💵 Revenue</h3>
<p id="revenue">Loading...</p>
</div>

<div class="card">
<h3>📈 Profit</h3>
<p id="profit">Loading...</p>
</div>

<div class="card">
<h3>🚨 Low Stock</h3>
<p id="low">Loading...</p>
</div>

</div>

<div class="card">
<h2>📦 Inventory Monitor</h2>

<input
id="search"
placeholder="🔎 Search inventory..."
onkeyup="filterItems()">

<div style="overflow:auto">

<table id="inventoryTable">

<thead>

<tr>
<th>SKU</th>
<th>Item</th>
<th>Qty</th>
<th>Price</th>
<th>Category</th>
<th>Status</th>
</tr>

</thead>

<tbody id="inventoryBody"></tbody>

</table>

</div>
</div>

<script>

let inventory=[];

async function loadDashboard(){

const r=await fetch("/api/stats");
const d=await r.json();

document.getElementById("items").innerText=d.items;
document.getElementById("stock").innerText=d.stock_units;
document.getElementById("revenue").innerText="₹"+d.revenue;
document.getElementById("profit").innerText="₹"+d.profit;
document.getElementById("low").innerText=d.low_stock;

}

async function loadInventory(){

const r=await fetch("/api/inventory");
const d=await r.json();

inventory=d.items;

renderInventory(inventory);

}

function renderInventory(data){

let html="";

data.forEach(x=>{

html+=`

<tr>

<td>${x.sku}</td>

<td>${x.name}</td>

<td>${x.quantity}</td>

<td>₹${x.price}</td>

<td>${x.category}</td>

<td>
${x.low_stock
? "⚠️ LOW"
: "✅ OK"}
</td>

</tr>

`;

});

document.getElementById(
"inventoryBody"
).innerHTML=html;

}

function filterItems(){

const q=document
.getElementById("search")
.value
.toLowerCase();

renderInventory(
inventory.filter(x=>
x.name.toLowerCase().includes(q) ||
x.sku.toLowerCase().includes(q) ||
x.category.toLowerCase().includes(q)
)
);

}

loadDashboard();
loadInventory();

setInterval(loadDashboard,30000);
setInterval(loadInventory,30000);

</script>
""")


# V9 input visibility fix
app.jinja_env.globals["V9_INPUT_FIX"] = True

