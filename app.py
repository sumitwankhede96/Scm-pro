from flask import Flask,request,redirect,render_template_string,session,send_file
import json,os,csv,io
from datetime import datetime

app=Flask(__name__)
app.secret_key="SCM_V6_2026"
FILE="scm_data.json"

def load():
    if os.path.exists(FILE):
        with open(FILE) as f:return json.load(f)
    return {"items":[],"suppliers":[],"orders":[],"sales":[]}

def save(d):
    with open(FILE,"w") as f:json.dump(d,f,indent=2)

def logged():
    return session.get("login",False)

CSS="""
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{font-family:Arial;background:#eef2f7;margin:0;padding:15px}
nav{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-bottom:15px}
nav a{background:#111;color:white;padding:10px;text-align:center;border-radius:8px;text-decoration:none}
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
.card,form,table{background:white;padding:15px;border-radius:15px;margin-bottom:15px}
input,select,button{width:100%;box-sizing:border-box;padding:11px;margin:5px 0;border-radius:8px;border:1px solid #ccc}
button{background:#111;color:white;border:0}
table{width:100%;border-collapse:collapse}
td,th{padding:9px;border-bottom:1px solid #ddd;text-align:left}
.low{color:red;font-weight:bold}.ok{color:green;font-weight:bold}
.bar{height:20px;background:#ddd;border-radius:10px;overflow:hidden}
.fill{height:100%;background:#111}
</style>
"""

LOGIN=CSS+"""
<form method="post" style="max-width:400px;margin:auto">
<h1>🔐 SCM PRO V6</h1>
<input name="user" placeholder="Username" required>
<input name="password" type="password" placeholder="Password" required>
<button>Login</button>
</form>
"""

NAV="""
<nav>
<a href="/">📊 Dashboard</a>
<a href="/inventory">📦 Inventory</a>
<a href="/orders">📋 Orders</a>
<a href="/sales">💵 Sales</a>
<a href="/suppliers">🏭 Suppliers</a>
<a href="/reports">📈 Reports</a>
<a href="/logout">🚪 Logout</a>
</nav>
"""

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        if request.form["user"]=="admin" and request.form["password"]=="admin123":
            session["login"]=True
            return redirect("/")
        return "❌ Wrong username or password"
    return LOGIN

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/")
def home():
    if not logged():return redirect("/login")

    d=load()
    items=d["items"]

    value=sum(x["quantity"]*x["price"] for x in items)
    low=sum(x["quantity"]<=x["minimum"] for x in items)
    sales=sum(x["total"] for x in d.get("sales",[]))
    profit=sum(x["profit"] for x in d.get("sales",[]))
    pending=sum(x["status"]=="Pending" for x in d.get("orders",[]))

    recent=d.get("sales",[])[-5:][::-1]

    return render_template_string(CSS+NAV+"""
<h1>📦 SCM PRO V6</h1>

<div class="grid">
<div class="card">📦 Items<br><b>{{n}}</b></div>
<div class="card">🏭 Suppliers<br><b>{{sup}}</b></div>
<div class="card">💰 Stock Value<br><b>₹{{"%.2f"|format(value)}}</b></div>
<div class="card">🚨 Low Stock<br><b>{{low}}</b></div>
<div class="card">💵 Sales<br><b>₹{{"%.2f"|format(sales)}}</b></div>
<div class="card">📈 Profit<br><b>₹{{"%.2f"|format(profit)}}</b></div>
<div class="card">📋 Pending PO<br><b>{{pending}}</b></div>
</div>

<h2>➕ Add Item</h2>
<form method="post" action="/add">
<input name="name" placeholder="Item name" required>
<input name="quantity" type="number" placeholder="Quantity" required>
<input name="price" type="number" step=".01" placeholder="Selling price" required>
<input name="cost" type="number" step=".01" placeholder="Purchase cost" required>
<input name="minimum" type="number" placeholder="Minimum stock" required>
<input name="supplier" placeholder="Supplier" required>
<button>Add Item</button>
</form>

<h2>🔄 Stock IN / OUT</h2>
<form method="post" action="/stock">
<select name="name">{%for x in items%}<option>{{x.name}}</option>{%endfor%}</select>
<input name="qty" type="number" placeholder="Quantity" required>
<select name="action">
<option value="in">📥 Stock IN</option>
<option value="out">📤 Stock OUT</option>
</select>
<button>Update Stock</button>
</form>

<h2>💵 Sale / Dispatch</h2>
<form method="post" action="/sale">
<select name="name">{%for x in items%}<option>{{x.name}}</option>{%endfor%}</select>
<input name="qty" type="number" placeholder="Quantity sold" required>
<button>Record Sale</button>
</form>

<h2>📋 Create Purchase Order</h2>
<form method="post" action="/order">
<input name="item" placeholder="Item" required>
<input name="qty" type="number" placeholder="Quantity" required>
<input name="supplier" placeholder="Supplier" required>
<button>Create PO</button>
</form>

<h2>🧾 Recent Sales</h2>
{%for x in recent%}
<div class="card">
<b>{{x.item}}</b> × {{x.qty}}<br>
Sales: ₹{{"%.2f"|format(x.total)}}<br>
Profit: ₹{{"%.2f"|format(x.profit)}}<br>
{{x.date}}
</div>
{%endfor%}
""",items=items,n=len(items),sup=len(d["suppliers"]),
value=value,low=low,sales=sales,profit=profit,pending=pending,recent=recent)

@app.post("/add")
def add():
    d=load()

    x={
    "name":request.form["name"],
    "quantity":int(request.form["quantity"]),
    "price":float(request.form["price"]),
    "cost":float(request.form["cost"]),
    "minimum":int(request.form["minimum"]),
    "supplier":request.form["supplier"]
    }

    d["items"].append(x)

    if x["supplier"] not in d["suppliers"]:
        d["suppliers"].append(x["supplier"])

    save(d)
    return redirect("/")

@app.post("/stock")
def stock():
    d=load()

    for x in d["items"]:
        if x["name"]==request.form["name"]:

            q=int(request.form["qty"])

            if request.form["action"]=="in":
                x["quantity"]+=q

            elif q<=x["quantity"]:
                x["quantity"]-=q

            break

    save(d)
    return redirect("/")

@app.post("/sale")
def sale():
    d=load()
    name=request.form["name"]
    q=int(request.form["qty"])

    for x in d["items"]:

        if x["name"]==name:

            if q>x["quantity"]:
                return "❌ Not enough stock"

            total=q*x["price"]
            profit=q*(x["price"]-x["cost"])

            x["quantity"]-=q

            d.setdefault("sales",[]).append({
            "item":name,
            "qty":q,
            "total":total,
            "profit":profit,
            "date":datetime.now().strftime("%Y-%m-%d %H:%M")
            })

            save(d)
            return redirect("/")

    return "❌ Item not found"

@app.post("/order")
def order():
    d=load()

    d.setdefault("orders",[]).append({
    "item":request.form["item"],
    "qty":int(request.form["qty"]),
    "supplier":request.form["supplier"],
    "status":"Pending",
    "date":datetime.now().strftime("%Y-%m-%d %H:%M")
    })

    save(d)
    return redirect("/")

@app.post("/order_status")
def order_status():
    d=load()

    i=int(request.form["index"])

    if 0<=i<len(d["orders"]):
        d["orders"][i]["status"]=request.form["status"]

    save(d)
    return redirect("/orders")

@app.route("/inventory")
def inventory():
    if not logged():return redirect("/login")

    d=load()
    q=request.args.get("q","").lower()

    items=[
    x for x in d["items"]
    if q in x["name"].lower() or q in x["supplier"].lower()
    ]

    return render_template_string(CSS+NAV+"""
<h1>📦 Inventory</h1>

<form>
<input name="q" placeholder="🔎 Search item / supplier" value="{{q}}">
<button>Search</button>
</form>

<table>
<tr><th>Item</th><th>Qty</th><th>Value</th><th>Status</th></tr>

{%for x in items%}
<tr>
<td>{{x.name}}</td>
<td>{{x.quantity}}</td>
<td>₹{{"%.2f"|format(x.quantity*x.price)}}</td>
<td class="{{'low' if x.quantity<=x.minimum else 'ok'}}">
{{'⚠️ LOW' if x.quantity<=x.minimum else '✅ OK'}}
</td>
</tr>
{%endfor%}
</table>
""",items=items,q=q)

@app.route("/orders")
def orders():
    if not logged():return redirect("/login")

    d=load()

    return render_template_string(CSS+NAV+"""
<h1>📋 Purchase Orders</h1>

{%for x in orders%}

<div class="card">
📦 <b>{{x.item}}</b><br>
Quantity: {{x.qty}}<br>
🏭 Supplier: {{x.supplier}}<br>
Date: {{x.date}}<br>
Status: <b>{{x.status}}</b>

<form method="post" action="/order_status">
<input type="hidden" name="index" value="{{loop.index0}}">

<select name="status">
<option>Pending</option>
<option>Approved</option>
<option>Received</option>
<option>Cancelled</option>
</select>

<button>Update Status</button>
</form>
</div>

{%endfor%}
""",orders=d.get("orders",[]))

@app.route("/sales")
def sales_page():
    if not logged():return redirect("/login")

    d=load()

    return render_template_string(CSS+NAV+"""
<h1>💵 Sales & Dispatch</h1>

{%for x in sales%}
<div class="card">
🧾 <b>{{x.item}}</b> × {{x.qty}}<br>
Sales: ₹{{"%.2f"|format(x.total)}}<br>
Profit: ₹{{"%.2f"|format(x.profit)}}<br>
{{x.date}}
</div>
{%endfor%}
""",sales=d.get("sales",[])[::-1])

@app.route("/suppliers")
def suppliers():
    if not logged():return redirect("/login")

    d=load()

    return render_template_string(CSS+NAV+"""
<h1>🏭 Suppliers</h1>

{%for s in suppliers%}
<div class="card">🏭 <b>{{s}}</b></div>
{%endfor%}
""",suppliers=d["suppliers"])

@app.route("/reports")
def reports():
    if not logged():return redirect("/login")

    d=load()

    sales=sum(x["total"] for x in d.get("sales",[]))
    profit=sum(x["profit"] for x in d.get("sales",[]))
    value=sum(x["quantity"]*x["price"] for x in d["items"])
    low=sum(x["quantity"]<=x["minimum"] for x in d["items"])

    max_sale=max([x["total"] for x in d.get("sales",[])],default=0)

    return render_template_string(CSS+NAV+"""
<h1>📈 Analytics</h1>

<div class="grid">
<div class="card">💵 Sales<br><b>₹{{"%.2f"|format(sales)}}</b></div>
<div class="card">📈 Profit<br><b>₹{{"%.2f"|format(profit)}}</b></div>
<div class="card">💰 Inventory Value<br><b>₹{{"%.2f"|format(value)}}</b></div>
<div class="card">🚨 Low Stock<br><b>{{low}}</b></div>
</div>

<h2>📊 Profit Indicator</h2>
<div class="bar">
<div class="fill" style="width:{{profit_percent}}%"></div>
</div>

<h2>🏆 Highest Sale</h2>
<div class="card">₹{{"%.2f"|format(max_sale)}}</div>

<h2>📥 Export</h2>
<a href="/csv">Download CSV Report</a>
""",
sales=sales,profit=profit,value=value,low=low,
max_sale=max_sale,
profit_percent=min(100,max(0,(profit/max(sales,1))*100)))

@app.route("/csv")
def csv_report():

    d=load()

    out=io.StringIO()
    w=csv.writer(out)

    w.writerow([
    "Item","Quantity","Selling Price",
    "Purchase Cost","Minimum Stock","Supplier"
    ])

    for x in d["items"]:
        w.writerow([
        x["name"],
        x["quantity"],
        x["price"],
        x["cost"],
        x["minimum"],
        x["supplier"]
        ])

    mem=io.BytesIO(out.getvalue().encode())
    mem.seek(0)

    return send_file(
    mem,
    as_attachment=True,
    download_name="SCM_V6_Report.csv",
    mimetype="text/csv"
    )

app.run(host="0.0.0.0",port=8080)
