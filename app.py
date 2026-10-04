
import os
import hmac
from functools import wraps

from flask import (
    Flask,
    request,
    jsonify,
    session,
    redirect,
    render_template_string
)

import database as db


app = Flask(__name__)

app.secret_key = os.environ["FLASK_SECRET_KEY"]
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=True,
    PERMANENT_SESSION_LIFETIME=1800
)


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect("/login")
        return func(*args, **kwargs)
    return wrapper


LOGIN_PAGE = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FREE ARPIT - Admin Login</title>
<style>
body {
    background:#0f172a;
    color:white;
    font-family:Arial,sans-serif;
    display:flex;
    align-items:center;
    justify-content:center;
    min-height:100vh;
    margin:0;
}
.card {
    background:#1e293b;
    padding:30px;
    border-radius:16px;
    width:85%;
    max-width:350px;
}
input,button {
    width:100%;
    padding:13px;
    margin-top:12px;
    border-radius:8px;
    border:0;
    box-sizing:border-box;
}
button {
    background:#2563eb;
    color:white;
    font-weight:bold;
}
</style>
</head>
<body>
<div class="card">
<h2>🔐 FREE ARPIT</h2>
<p>Admin Dashboard Login</p>
<form method="POST">
<input type="password" name="password"
placeholder="Admin Password" required>
<button type="submit">Login</button>
</form>
{% if error %}
<p style="color:#f87171">{{ error }}</p>
{% endif %}
</div>
</body>
</html>
"""


DASHBOARD = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FREE ARPIT Dashboard</title>
<style>
* {box-sizing:border-box}
body {
    margin:0;
    background:#0f172a;
    color:#f8fafc;
    font-family:Arial,sans-serif;
}
header {
    padding:20px;
    background:#1e293b;
    display:flex;
    justify-content:space-between;
    align-items:center;
}
header a {color:#f87171;text-decoration:none}
main {padding:18px;max-width:1100px;margin:auto}
.grid {
    display:grid;
    grid-template-columns:repeat(2,minmax(0,1fr));
    gap:12px;
}
.card {
    background:#1e293b;
    padding:18px;
    border-radius:12px;
    margin-bottom:15px;
    overflow-wrap:anywhere;
}
.number {font-size:27px;font-weight:bold;margin-top:10px}
.muted {color:#94a3b8;font-size:13px}
button,input {
    padding:11px;
    border-radius:7px;
    border:0;
    margin:4px 0;
}
button {background:#2563eb;color:white;cursor:pointer}
input {max-width:100%;width:100%;background:#334155;color:white}
.danger {background:#dc2626}
.success {background:#15803d}
table {width:100%;border-collapse:collapse;font-size:13px}
td,th {padding:10px;border-bottom:1px solid #334155;text-align:left}
.table-wrap {overflow-x:auto}
@media(max-width:480px) {
    main {padding:12px}
    .card {padding:14px}
}
</style>
</head>
<body>
<header>
<strong>🛡️ FREE ARPIT</strong>
<a href="/logout">Logout</a>
</header>

<main>
<h2>Admin Dashboard</h2>
<p class="muted">Bot management and analytics</p>

<div class="grid">
<div class="card">
<div class="muted">Total Users</div>
<div class="number" id="users">0</div>
</div>
<div class="card">
<div class="muted">Total Searches</div>
<div class="number" id="searches">0</div>
</div>
<div class="card">
<div class="muted">Blocked Users</div>
<div class="number" id="blocked">0</div>
</div>
<div class="card">
<div class="muted">Available Credits</div>
<div class="number" id="credits">0</div>
</div>
</div>

<div class="card">
<h3>⚙️ Bot Settings</h3>
<p>Maintenance mode:
<strong id="maintenance">Loading</strong></p>
<button onclick="setMaintenance(true)">Enable</button>
<button class="success" onclick="setMaintenance(false)">Disable</button>
</div>

<div class="card">
<h3>💳 Manage Credits</h3>
<input id="creditUser" placeholder="Telegram User ID">
<input id="creditAmount" type="number" min="1" placeholder="Credits to add">
<button onclick="addCredits()">Add Credits</button>
</div>

<div class="card">
<h3>👥 User Management</h3>
<div class="table-wrap">
<table>
<thead>
<tr>
<th>User ID</th>
<th>Username</th>
<th>Credits</th>
<th>Status</th>
<th>Action</th>
</tr>
</thead>
<tbody id="userRows"></tbody>
</table>
</div>
</div>

<div class="card">
<h3>📊 Recent Searches</h3>
<div class="table-wrap">
<table>
<thead>
<tr>
<th>User</th>
<th>Type</th>
<th>Query</th>
<th>Date</th>
</tr>
</thead>
<tbody id="searchRows"></tbody>
</table>
</div>
</div>
</main>

<script>
async function api(url, options={}) {
    const response = await fetch(url, options);
    if (response.status === 401) {
        location.href = "/login";
        return {};
    }
    return response.json();
}

async function loadDashboard() {
    const data = await api("/api/dashboard");

    if (!data.stats) return;

    document.getElementById("users").textContent =
        data.stats.total_users;
    document.getElementById("searches").textContent =
        data.stats.total_searches;
    document.getElementById("blocked").textContent =
        data.stats.blocked_users;
    document.getElementById("credits").textContent =
        data.stats.total_credits;

    document.getElementById("maintenance").textContent =
        data.maintenance ? "ON" : "OFF";

    const rows = document.getElementById("userRows");
    rows.replaceChildren();

    data.users.forEach(user => {
        const tr = document.createElement("tr");

        const values = [
            user.user_id,
            user.username || "N/A",
            user.credits,
            user.is_blocked ? "Blocked" : "Active"
        ];

        values.forEach(value => {
            const td = document.createElement("td");
            td.textContent = value;
            tr.appendChild(td);
        });

        const action = document.createElement("td");
        const button = document.createElement("button");

        button.textContent = user.is_blocked ? "Unblock" : "Block";
        button.className = user.is_blocked ? "success" : "danger";
        button.onclick = () => toggleBlock(
            user.user_id,
            !user.is_blocked
        );

        action.appendChild(button);
        tr.appendChild(action);
        rows.appendChild(tr);
    });

    const searchRows = document.getElementById("searchRows");
    searchRows.replaceChildren();

    data.searches.forEach(item => {
        const tr = document.createElement("tr");

        [
            item.user_id,
            item.search_type,
            item.query,
            item.created_at
        ].forEach(value => {
            const td = document.createElement("td");
            td.textContent = value;
            tr.appendChild(td);
        });

        searchRows.appendChild(tr);
    });
}

async function addCredits() {
    const user_id = document.getElementById("creditUser").value;
    const amount = document.getElementById("creditAmount").value;

    const result = await api("/api/credits", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({user_id, amount})
    });

    alert(result.message || result.error);
    loadDashboard();
}

async function toggleBlock(user_id, blocked) {
    const result = await api("/api/block", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({user_id, blocked})
    });

    alert(result.message || result.error);
    loadDashboard();
}

async function setMaintenance(enabled) {
    const result = await api("/api/maintenance", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({enabled})
    });

    alert(result.message || result.error);
    loadDashboard();
}

loadDashboard();
setInterval(loadDashboard, 15000);
</script>
</body>
</html>
"""


@app.route("/")
def home():
    if session.get("admin_logged_in"):
        return redirect("/dashboard")
    return redirect("/login")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password", "")

        if hmac.compare_digest(password, ADMIN_PASSWORD):
            session.clear()
            session["admin_logged_in"] = True
            session.permanent = True
            return redirect("/dashboard")

        return render_template_string(
            LOGIN_PAGE,
            error="Incorrect password"
        )

    return render_template_string(LOGIN_PAGE, error=None)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template_string(DASHBOARD)


@app.route("/api/dashboard")
@login_required
def dashboard_data():
    users = db.get_all_users()
    searches = db.get_recent_searches(20)

    return jsonify({
        "stats": db.get_stats(),
        "maintenance": db.get_setting(
            "maintenance_mode", "0"
        ) == "1",
        "users": [
            {
                "user_id": user["user_id"],
                "username": user["username"],
                "credits": user["credits"],
                "is_blocked": user["is_blocked"]
            }
            for user in users
        ],
        "searches": [
            {
                "user_id": item["user_id"],
                "search_type": item["search_type"],
                "query": item["query"],
                "created_at": item["created_at"]
            }
            for item in searches
        ]
    })


@app.route("/api/credits", methods=["POST"])
@login_required
def credits_api():
    data = request.get_json(silent=True) or {}

    try:
        user_id = int(data.get("user_id"))
        amount = int(data.get("amount"))

        if amount <= 0 or amount > 100000:
            raise ValueError

    except (ValueError, TypeError):
        return jsonify({"error": "Invalid user ID or amount"}), 400

    if not db.get_user(user_id):
        return jsonify({"error": "User not found"}), 404

    db.add_credits(user_id, amount)

    return jsonify({"message": "Credits added successfully"})


@app.route("/api/block", methods=["POST"])
@login_required
def block_api():
    data = request.get_json(silent=True) or {}

    try:
        user_id = int(data.get("user_id"))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid user ID"}), 400

    blocked = data.get("blocked")

    if not isinstance(blocked, bool):
        return jsonify({"error": "Invalid status"}), 400

    if user_id == int(os.environ["ADMIN_ID"]):
        return jsonify({"error": "Cannot block primary admin"}), 400

    if not db.get_user(user_id):
        return jsonify({"error": "User not found"}), 404

    db.set_blocked(user_id, blocked)

    return jsonify({
        "message": "User blocked" if blocked else "User unblocked"
    })


@app.route("/api/maintenance", methods=["POST"])
@login_required
def maintenance_api():
    data = request.get_json(silent=True) or {}
    enabled = data.get("enabled")

    if not isinstance(enabled, bool):
        return jsonify({"error": "Invalid setting"}), 400

    db.set_setting(
        "maintenance_mode",
        "1" if enabled else "0"
    )

    return jsonify({
        "message": "Maintenance setting updated"
    })


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
