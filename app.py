from flask import Flask,request,redirect,render_template_string,session,send_file,url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os,csv,io,json

app=Flask(__name__)
app.secret_key=os.environ.get("SECRET_KEY","SCM_V7_SECRET_2026")

DATABASE_URL=os.environ.get("DATABASE_URL")
if DATABASE_URL:
    DATABASE_URL=DATABASE_URL.replace("postgres://","postgresql://",1)
    app.config["SQLALCHEMY_DATABASE_URI"]=DATABASE_URL
else:
    app.config["SQLALCHEMY_DATABASE_URI"]="sqlite:///scm_v7.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"]=False
db=SQLAlchemy(app)

class Item(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(120),unique=True,nullable=False)
    quantity=db.Column(db.Integer,default=0)
    price=db.Column(db.Float,default=0)
    cost=db.Column(db.Float,default=0)
    minimum=db.Column(db.Integer,default=0)
    supplier=db.Column(db.String(120),default="")

class Supplier(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(120),unique=True,nullable=False)
    phone=db.Column(db.String(50),default="")
    email=db.Column(db.String(120),default="")

class StockLog(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    item=db.Column(db.String(120))
    action=db.Column(db.String(20))
    quantity=db.Column(db.Integer)
    date=db.Column(db.DateTime,default=datetime.utcnow)

class Sale(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    item=db.Column(db.String(120))
    quantity=db.Column(db.Integer)
    total=db.Column(db.Float)
    profit=db.Column(db.Float)
    date=db.Column(db.DateTime,default=datetime.utcnow)

class Order(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    item=db.Column(db.String(120))
    quantity=db.Column(db.Integer)
    supplier=db.Column(db.String(120))
    status=db.Column(db.String(30),default="Pending")
    date=db.Column(db.DateTime,default=datetime.utcnow)

class Invoice(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    customer=db.Column(db.String(120))
    item=db.Column(db.String(120))
    quantity=db.Column(db.Integer)
    amount=db.Column(db.Float)
    date=db.Column(db.DateTime,default=datetime.utcnow)

with app.app_context():
    db.create_all()

    # Import old V6 JSON data once if database is empty
    if Item.query.count()==0 and os.path.exists("scm_data.json"):
        try:
            with open("scm_data.json",encoding="utf8") as f:
                old=json.load(f)

            for x in old.get("items",[]):
                if not Item.query.filter_by(name=x.get("name","")).first():
                    db.session.add(Item(
                        name=x.get("name","Unknown"),
                        quantity=int(x.get("quantity",0)),
                        price=float(x.get("price",0)),
                        cost=float(x.get("cost",0)),
                        minimum=int(x.get("minimum",0)),
                        supplier=x.get("supplier","")
                    ))

            for s in old.get("suppliers",[]):
                if not Supplier.query.filter_by(name=s).first():
                    db.session.add(Supplier(name=s))

            db.session.commit()
        except Exception as e:
            print("Old data import:",e)

CSS="""
<meta name="viewport" content="width=device-width,initial-scale=1">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
*{box-sizing:border-box}
body{margin:0;font-family:Arial;background:#f1f5f9;color:#111}
nav{background:#111827;padding:12px;display:flex;gap:8px;flex-wrap:wrap;position:sticky;top:0;z-index:10}
nav a{color:white;text-decoration:none;padding:10px 13px;border-radius:8px}
nav a:hover{background:#374151}
main{max-width:1200px;margin:auto;padding:18px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px}
.card{background:white;border-radius:16px;padding:18px;margin-bottom:15px;box-shadow:0 2px 10px #0001}
.big{font-size:25px;font-weight:bold;margin-top:8px}
form{background:white;padding:18px;border-radius:16px;margin:15px 0}
input,select{width:100%;padding:11px;margin:5px 0;border:1px solid #ddd;border-radius:9px}
button,.btn{background:#111827;color:white;border:0;padding:11px 15px;border-radius:9px;text-decoration:none;display:inline-block;margin:4px 0}
.danger{background:#b91c1c}.green{background:#15803d}.blue{background:#1d4ed8}
table{width:100%;background:white;border-collapse:collapse;border-radius:12px;overflow:hidden}
th,td{padding:11px;border-bottom:1px solid #eee;text-align:left}
.low{color:#dc2626;font-weight:bold}.ok{color:#15803d;font-weight:bold}
.alert{padding:13px;background:#fee2e2;color:#991b1b;border-radius:10px;margin:10px 0}
@media(max-width:600px){table{font-size:13px}nav{display:grid;grid-template-columns:repeat(2,1fr)}}
</style>
"""

NAV="""
<nav>
<a href="/">📊 Dashboard</a>
<a href="/inventory">📦 Inventory</a>
<a href="/stock">🔄 Stock</a>
<a href="/sales">💵 Sales</a>
<a href="/orders">📋 Orders</a>
<a href="/suppliers">🏭 Suppliers</a>
<a href="/invoices">🧾 Invoices</a>
<a href="/reports">📈 Reports</a>
<a href="/logout">🚪 Logout</a>
</nav>
"""

LOGIN=CSS+"""
<main style="max-width:420px;margin:70px auto">
<div class="card">
<h1>🔐 SCM PRO V7</h1>
<p>Supply Chain Management System</p>
<form method="post">
<input name="user" placeholder="Username" required>
<input name="password" type="password" placeholder="Password" required>
<button style="width:100%">Login</button>
</form>
<p>Demo: <b>admin / admin123</b></p>
</div>
</main>
"""

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        if request.form.get("user")=="admin" and request.form.get("password")=="admin123":
            session["login"]=True
            return redirect("/dashboard")
        return render_template_string(LOGIN+"<main><div class='alert'>❌ Wrong login</div></main>")
    return LOGIN

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

def auth():
    return session.get("login",False)

def page(body,**kwargs):
    return render_template_string(CSS+NAV+"<main>"+body+"</main>",**kwargs)

@app.route("/")
@app.route("/dashboard")
def dashboard():
    if not auth(): return redirect("/login")

    items=Item.query.all()
    sales=Sale.query.all()
    orders=Order.query.all()

    value=sum(x.quantity*x.price for x in items)
    revenue=sum(x.total for x in sales)
    profit=sum(x.profit for x in sales)
    low=[x for x in items if x.quantity<=x.minimum]

    labels=[x.name for x in items]
    quantities=[x.quantity for x in items]

    return page("""
<h1>📊 SCM PRO V7 Dashboard</h1>

<div class="grid">
<div class="card">📦 Items<div class="big">{{items|length}}</div></div>
<div class="card">🏭 Suppliers<div class="big">{{sup}}</div></div>
<div class="card">💰 Stock Value<div class="big">₹{{"%.2f"|format(value)}}</div></div>
<div class="card">🚨 Low Stock<div class="big">{{low|length}}</div></div>
<div class="card">💵 Revenue<div class="big">₹{{"%.2f"|format(revenue)}}</div></div>
<div class="card">📈 Profit<div class="big">₹{{"%.2f"|format(profit)}}</div></div>
<div class="card">📋 Pending PO<div class="big">{{pending}}</div></div>
</div>

{%if low%}
<div class="alert"><b>🚨 Low Stock Alert:</b>
{%for x in low%} {{x.name}} ({{x.quantity}}) {%endfor%}
</div>
{%endif%}

<div class="card">
<h2>📊 Inventory Chart</h2>
<canvas id="chart"></canvas>
</div>

<div class="card">
<h2>⚡ Quick Actions</h2>
<a class="btn" href="/inventory">📦 Inventory</a>
<a class="btn green" href="/stock">🔄 Stock Update</a>
<a class="btn blue" href="/sales">💵 New Sale</a>
<a class="btn" href="/invoices">🧾 Invoice</a>
</div>

<script>
new Chart(document.getElementById('chart'),{
type:'bar',
data:{
labels:{{labels|tojson}},
datasets:[{label:'Quantity',data:{{quantities|tojson}}}]
},
options:{responsive:true}
});
</script>
""",items=items,sup=Supplier.query.count(),value=value,
revenue=revenue,profit=profit,low=low,pending=Order.query.filter_by(status="Pending").count(),
labels=labels,quantities=quantities)

@app.route("/inventory",methods=["GET","POST"])
def inventory():
    if not auth(): return redirect("/login")

    if request.method=="POST":
        try:
            x=Item(
                name=request.form["name"],
                quantity=int(request.form["quantity"]),
                price=float(request.form["price"]),
                cost=float(request.form["cost"]),
                minimum=int(request.form["minimum"]),
                supplier=request.form.get("supplier","")
            )
            db.session.add(x)

            s=request.form.get("supplier","")
            if s and not Supplier.query.filter_by(name=s).first():
                db.session.add(Supplier(name=s))

            db.session.commit()
            return redirect("/inventory")
        except Exception as e:
            db.session.rollback()
            return "❌ Item already exists or invalid data: "+str(e)

    q=request.args.get("q","").lower()
    items=Item.query.all()
    if q:
        items=[x for x in items if q in x.name.lower() or q in x.supplier.lower()]

    return page("""
<h1>📦 Inventory</h1>

<form>
<input name="q" value="{{q}}" placeholder="🔎 Search item or supplier">
<button>Search</button>
</form>

<form method="post">
<h2>➕ Add Item</h2>
<input name="name" placeholder="Item name" required>
<input name="quantity" type="number" placeholder="Quantity" required>
<input name="price" type="number" step=".01" placeholder="Selling price" required>
<input name="cost" type="number" step=".01" placeholder="Purchase cost" required>
<input name="minimum" type="number" placeholder="Minimum stock" required>
<input name="supplier" placeholder="Supplier">
<button>Add Item</button>
</form>

<table>
<tr><th>Item</th><th>Qty</th><th>Price</th><th>Value</th><th>Status</th></tr>
{%for x in items%}
<tr>
<td>{{x.name}}</td>
<td>{{x.quantity}}</td>
<td>₹{{"%.2f"|format(x.price)}}</td>
<td>₹{{"%.2f"|format(x.quantity*x.price)}}</td>
<td class="{{'low' if x.quantity<=x.minimum else 'ok'}}">
{{'⚠️ LOW' if x.quantity<=x.minimum else '✅ OK'}}
</td>
</tr>
{%endfor%}
</table>
""",items=items,q=q)

@app.route("/stock",methods=["GET","POST"])
def stock():
    if not auth(): return redirect("/login")

    if request.method=="POST":
        x=Item.query.filter_by(id=int(request.form["item"])).first()
        q=int(request.form["quantity"])
        action=request.form["action"]

        if not x:return "❌ Item not found"

        if action=="IN":
            x.quantity+=q
        else:
            if q>x.quantity:return "❌ Insufficient stock"
            x.quantity-=q

        db.session.add(StockLog(item=x.name,action=action,quantity=q))
        db.session.commit()
        return redirect("/stock")

    items=Item.query.all()
    logs=StockLog.query.order_by(StockLog.date.desc()).limit(30).all()

    return page("""
<h1>🔄 Stock Management</h1>

<form method="post">
<select name="item">
{%for x in items%}<option value="{{x.id}}">{{x.name}} ({{x.quantity}})</option>{%endfor%}
</select>
<input name="quantity" type="number" min="1" placeholder="Quantity" required>
<select name="action"><option>IN</option><option>OUT</option></select>
<button>Update Stock</button>
</form>

<h2>🕘 Stock History</h2>
<table>
<tr><th>Item</th><th>Action</th><th>Qty</th><th>Date</th></tr>
{%for x in logs%}<tr><td>{{x.item}}</td><td>{{x.action}}</td><td>{{x.quantity}}</td><td>{{x.date}}</td></tr>{%endfor%}
</table>
""",items=items,logs=logs)

@app.route("/sales",methods=["GET","POST"])
def sales():
    if not auth(): return redirect("/login")

    if request.method=="POST":
        x=Item.query.get(int(request.form["item"]))
        q=int(request.form["quantity"])

        if not x:return "❌ Item not found"
        if q>x.quantity:return "❌ Insufficient stock"

        total=q*x.price
        profit=q*(x.price-x.cost)

        x.quantity-=q
        db.session.add(Sale(item=x.name,quantity=q,total=total,profit=profit))

        db.session.commit()
        return redirect("/sales")

    items=Item.query.all()
    sales=Sale.query.order_by(Sale.date.desc()).all()

    return page("""
<h1>💵 Sales & Profit</h1>

<form method="post">
<select name="item">{%for x in items%}<option value="{{x.id}}">{{x.name}} — {{x.quantity}} available</option>{%endfor%}</select>
<input name="quantity" type="number" min="1" placeholder="Quantity" required>
<button>Record Sale</button>
</form>

<table>
<tr><th>Item</th><th>Qty</th><th>Revenue</th><th>Profit</th><th>Date</th></tr>
{%for x in sales%}
<tr><td>{{x.item}}</td><td>{{x.quantity}}</td><td>₹{{"%.2f"|format(x.total)}}</td><td>₹{{"%.2f"|format(x.profit)}}</td><td>{{x.date}}</td></tr>
{%endfor%}
</table>
""",items=items,sales=sales)

@app.route("/orders",methods=["GET","POST"])
def orders():
    if not auth(): return redirect("/login")

    if request.method=="POST":
        db.session.add(Order(
            item=request.form["item"],
            quantity=int(request.form["quantity"]),
            supplier=request.form["supplier"]
        ))
        db.session.commit()
        return redirect("/orders")

    orders=Order.query.order_by(Order.date.desc()).all()
    suppliers=Supplier.query.all()

    return page("""
<h1>📋 Purchase Orders</h1>

<form method="post">
<input name="item" placeholder="Item" required>
<input name="quantity" type="number" placeholder="Quantity" required>
<select name="supplier">
{%for s in suppliers%}<option>{{s.name}}</option>{%endfor%}
</select>
<input name="supplier" placeholder="Or type supplier">
<button>Create Purchase Order</button>
</form>

{%for x in orders%}
<div class="card">
<b>📦 {{x.item}}</b><br>
Quantity: {{x.quantity}}<br>
Supplier: {{x.supplier}}<br>
Status: <b>{{x.status}}</b><br>
{{x.date}}

<form method="post" action="/order/{{x.id}}">
<select name="status">
<option>Pending</option>
<option>Approved</option>
<option>Received</option>
<option>Cancelled</option>
</select>
<button>Update</button>
</form>
</div>
{%endfor%}
""",orders=orders,suppliers=suppliers)

@app.post("/order/<int:id>")
def order_update(id):
    if not auth():return redirect("/login")
    x=Order.query.get_or_404(id)
    x.status=request.form["status"]
    db.session.commit()
    return redirect("/orders")

@app.route("/suppliers",methods=["GET","POST"])
def suppliers():
    if not auth():return redirect("/login")

    if request.method=="POST":
        name=request.form["name"]
        if not Supplier.query.filter_by(name=name).first():
            db.session.add(Supplier(name=name,phone=request.form.get("phone",""),email=request.form.get("email","")))
            db.session.commit()
        return redirect("/suppliers")

    suppliers=Supplier.query.all()

    return page("""
<h1>🏭 Suppliers</h1>

<form method="post">
<input name="name" placeholder="Supplier name" required>
<input name="phone" placeholder="Phone">
<input name="email" placeholder="Email">
<button>Add Supplier</button>
</form>

<table>
<tr><th>Supplier</th><th>Phone</th><th>Email</th></tr>
{%for x in suppliers%}<tr><td>{{x.name}}</td><td>{{x.phone}}</td><td>{{x.email}}</td></tr>{%endfor%}
</table>
""",suppliers=suppliers)

@app.route("/invoices",methods=["GET","POST"])
def invoices():
    if not auth():return redirect("/login")

    if request.method=="POST":
        x=Item.query.get(int(request.form["item"]))
        q=int(request.form["quantity"])
        customer=request.form["customer"]

        if not x:return "❌ Item not found"
        if q>x.quantity:return "❌ Insufficient stock"

        amount=q*x.price
        x.quantity-=q

        inv=Invoice(customer=customer,item=x.name,quantity=q,amount=amount)
        db.session.add(inv)
        db.session.commit()

        return redirect(url_for("invoice",id=inv.id))

    items=Item.query.all()

    return page("""
<h1>🧾 Invoice Generator</h1>

<form method="post">
<input name="customer" placeholder="Customer name" required>
<select name="item">{%for x in items%}<option value="{{x.id}}">{{x.name}} — ₹{{x.price}}</option>{%endfor%}</select>
<input name="quantity" type="number" min="1" placeholder="Quantity" required>
<button>Generate Invoice</button>
</form>
""",items=items)

@app.route("/invoice/<int:id>")
def invoice(id):
    if not auth():return redirect("/login")
    x=Invoice.query.get_or_404(id)

    return render_template_string(CSS+"""
<main style="max-width:700px;margin:auto">
<div class="card">
<h1>🧾 SCM PRO INVOICE</h1>
<hr>
<p><b>Invoice #{{x.id}}</b></p>
<p>Date: {{x.date}}</p>
<p>Customer: <b>{{x.customer}}</b></p>

<table>
<tr><th>Item</th><th>Qty</th><th>Amount</th></tr>
<tr><td>{{x.item}}</td><td>{{x.quantity}}</td><td>₹{{"%.2f"|format(x.amount)}}</td></tr>
</table>

<h2>Total: ₹{{"%.2f"|format(x.amount)}}</h2>
<button onclick="window.print()">🖨️ Print / Save PDF</button>
<a class="btn" href="/invoices">Back</a>
</div>
</main>
""",x=x)

@app.route("/reports")
def reports():
    if not auth():return redirect("/login")

    items=Item.query.all()
    sales=Sale.query.all()

    revenue=sum(x.total for x in sales)
    profit=sum(x.profit for x in sales)
    stock=sum(x.quantity*x.price for x in items)

    return page("""
<h1>📈 Reports & Analytics</h1>

<div class="grid">
<div class="card">💵 Revenue<div class="big">₹{{"%.2f"|format(revenue)}}</div></div>
<div class="card">📈 Profit<div class="big">₹{{"%.2f"|format(profit)}}</div></div>
<div class="card">💰 Stock<div class="big">₹{{"%.2f"|format(stock)}}</div></div>
</div>

<div class="card">
<h2>Sales vs Profit</h2>
<canvas id="salesChart"></canvas>
</div>

<a class="btn" href="/export">📥 Download CSV</a>

<script>
new Chart(document.getElementById('salesChart'),{
type:'line',
data:{
labels:{{labels|tojson}},
datasets:[
{label:'Sales',data:{{salesdata|tojson}},tension:.3},
{label:'Profit',data:{{profitdata|tojson}},tension:.3}
]
},
options:{responsive:true}
});
</script>
""",
revenue=revenue,profit=profit,stock=stock,
labels=[str(x.date)[:10] for x in sales],
salesdata=[x.total for x in sales],
profitdata=[x.profit for x in sales])

@app.route("/export")
def export():
    if not auth():return redirect("/login")

    out=io.StringIO()
    w=csv.writer(out)
    w.writerow(["Item","Quantity","Price","Cost","Minimum","Supplier"])

    for x in Item.query.all():
        w.writerow([x.name,x.quantity,x.price,x.cost,x.minimum,x.supplier])

    mem=io.BytesIO(out.getvalue().encode())
    mem.seek(0)

    return send_file(mem,as_attachment=True,
                     download_name="SCM_V7_Inventory.csv",
                     mimetype="text/csv")

@app.route("/health")
def health():
    return {"status":"ok","version":"SCM Pro V7"}

app.run(host="0.0.0.0",port=int(os.environ.get("PORT",8080)))
