
import bot_runner
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
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FREE ARPIT | Secure Access</title>

<style>
* {
    box-sizing: border-box;
    font-family: Arial, Helvetica, sans-serif !important;
}

body {
    margin: 0;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
    background: #030807;
    color: #d1fae5;
    font-size: 19px;
    line-height: 1.7;
    overflow-x: hidden;
}

body::before {
    content: "";
    position: fixed;
    inset: 0;
    background:
        linear-gradient(rgba(0,255,120,.035) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,255,120,.035) 1px, transparent 1px);
    background-size: 35px 35px;
    pointer-events: none;
}

.glow {
    position: fixed;
    width: 300px;
    height: 300px;
    background: #00ff8840;
    filter: blur(120px);
    border-radius: 50%;
    pointer-events: none;
}

.card {
    position: relative;
    width: 100%;
    max-width: 430px;
    padding: 35px 28px;
    background: rgba(5, 18, 13, .94);
    border: 1px solid #00ff8870;
    border-radius: 15px;
    box-shadow: 0 0 35px #00ff881c;
    animation: appear .7s ease;
}

@keyframes appear {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.logo {
    text-align: center;
    font-size: 34px;
    font-weight: 800;
    color: #00ff88;
    text-shadow: 0 0 15px #00ff88;
    letter-spacing: 1px;
}

.subtitle {
    text-align: center;
    color: #6ee7b7;
    font-size: 17px;
    margin-top: 10px;
    letter-spacing: 1px;
}

.status {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 10px;
    margin: 27px 0;
    color: #4ade80;
    font-size: 16px;
    text-align: center;
}

.dot {
    width: 9px;
    height: 9px;
    flex-shrink: 0;
    background: #00ff88;
    border-radius: 50%;
    box-shadow: 0 0 12px #00ff88;
    animation: blink 1.5s infinite;
}

@keyframes blink {
    50% { opacity: .3; }
}

label {
    display: block;
    color: #86efac;
    font-size: 18px;
    font-weight: 700;
    margin-bottom: 10px;
}

input {
    width: 100%;
    padding: 17px;
    background: #07130e;
    border: 1px solid #166534;
    border-radius: 8px;
    color: #d1fae5;
    outline: none;
    font-family: Arial, Helvetica, sans-serif !important;
    font-size: 19px;
}

input:focus {
    border-color: #00ff88;
    box-shadow: 0 0 12px #00ff8830;
}

input::placeholder {
    color: #7b9b87;
    opacity: 1;
}

button {
    width: 100%;
    margin-top: 18px;
    padding: 17px;
    background: #00ff88;
    color: #031108;
    border: none;
    border-radius: 8px;
    font-family: Arial, Helvetica, sans-serif !important;
    font-size: 19px;
    font-weight: 800;
    cursor: pointer;
    transition: .2s;
}

button:hover {
    background: #86efac;
    box-shadow: 0 0 20px #00ff8860;
}

.error {
    color: #fb7185;
    background: #450a0a50;
    border: 1px solid #be123c70;
    border-radius: 7px;
    padding: 12px;
    font-size: 17px;
    text-align: center;
    margin-top: 15px;
}

.footer {
    text-align: center;
    color: #4b8064;
    font-size: 14px;
    line-height: 1.8;
    margin-top: 27px;
    letter-spacing: .5px;
}

@media(max-width: 480px) {
    .card {
        padding: 28px 20px;
    }

    .logo {
        font-size: 30px;
    }

    .subtitle {
        font-size: 15px;
    }

    .status {
        font-size: 15px;
    }

    input, button {
        font-size: 18px;
    }
}
</style>
</head>

<body>
<div class="glow"></div>

<div class="card">
    <div class="logo">FREE ARPIT</div>
    <div class="subtitle">OSINT CONTROL SYSTEM</div>

    <div class="status">
        <span class="dot"></span>
        SECURE CONNECTION READY
    </div>

    <form method="POST">
        <label>ADMIN AUTHENTICATION</label>

        <input
            type="password"
            name="password"
            placeholder="Enter access password"
            autocomplete="current-password"
            required
        >

        <button type="submit">ACCESS DASHBOARD →</button>
    </form>

    {% if error %}
    <div class="error">{{ error }}</div>
    {% endif %}

    <div class="footer">
        AUTHORIZED ACCESS ONLY<br>
        FREE ARPIT SECURITY SYSTEM
    </div>
</div>
</body>
</html>
"""


DASHBOARD = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<title>FREE ARPIT | Control Panel</title>

<style>
:root {
    --bg: #030807;
    --panel: #08130e;
    --panel2: #0b1b12;
    --green: #00ff88;
    --green2: #4ade80;
    --muted: #7b9b87;
    --border: #16452c;
    --red: #fb7185;
}

* {
    box-sizing: border-box;
    font-family: Arial, Helvetica, sans-serif !important;
}

body {
    margin: 0;
    background: var(--bg);
    color: #d1fae5;
    font-size: 19px;
    line-height: 1.7;
}

header {
    position: sticky;
    top: 0;
    z-index: 10;
    padding: 18px 22px;
    background: rgba(5, 17, 11, .96);
    border-bottom: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
    backdrop-filter: blur(12px);
}

.brand {
    color: var(--green);
    font-size: 20px;
    font-weight: 800;
    letter-spacing: .5px;
    text-shadow: 0 0 12px #00ff8850;
}

.logout {
    color: var(--red);
    text-decoration: none;
    font-size: 17px;
    font-weight: 700;
    border: 1px solid #7f1d1d;
    padding: 12px 16px;
    border-radius: 7px;
}

main {
    width: 100%;
    max-width: 1200px;
    margin: auto;
    padding: 24px;
}

.heading {
    margin-bottom: 24px;
}

.heading h2 {
    color: var(--green);
    font-size: 30px;
    font-weight: 800;
    margin: 0 0 9px;
}

.muted {
    color: var(--muted);
    font-size: 17px;
}

.system-status {
    display: inline-flex;
    align-items: center;
    gap: 9px;
    color: var(--green2);
    font-size: 16px;
    margin-top: 12px;
    flex-wrap: wrap;
}

.dot {
    width: 9px;
    height: 9px;
    background: var(--green);
    border-radius: 50%;
    box-shadow: 0 0 10px var(--green);
}

.grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 14px;
    margin-bottom: 20px;
}

.card {
    background: linear-gradient(145deg, var(--panel2), var(--panel));
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 17px;
    overflow: hidden;
    box-shadow: 0 5px 20px #00000030;
}

.stat {
    position: relative;
    min-height: 140px;
}

.stat-label {
    color: var(--muted);
    font-size: 16px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .5px;
}

.number {
    color: var(--green);
    font-size: 36px;
    font-weight: 800;
    margin-top: 20px;
    text-shadow: 0 0 14px #00ff8840;
    overflow-wrap: anywhere;
}

.stat-icon {
    position: absolute;
    right: 15px;
    top: 13px;
    font-size: 25px;
    opacity: .65;
}

h3 {
    color: var(--green2);
    font-size: 22px;
    font-weight: 800;
    margin: 0 0 18px;
}

.section-label {
    color: var(--muted);
    font-size: 16px;
    margin-bottom: 14px;
}

button, input {
    font-family: Arial, Helvetica, sans-serif !important;
    font-size: 18px;
    border-radius: 7px;
    padding: 15px;
    margin: 4px 0;
}

input {
    width: 100%;
    background: #041009;
    color: #d1fae5;
    border: 1px solid #22543d;
    outline: none;
}

input:focus {
    border-color: var(--green);
    box-shadow: 0 0 10px #00ff8825;
}

input::placeholder {
    color: #7b9b87;
    opacity: 1;
}

button {
    background: var(--green);
    color: #031108;
    border: none;
    font-weight: 800;
    cursor: pointer;
    transition: .2s;
}

button:hover {
    filter: brightness(1.15);
    box-shadow: 0 0 13px #00ff8830;
}

.success {
    background: #166534;
    color: white;
}

.danger {
    background: #9f1239;
    color: white;
}

.controls {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
}

.controls button {
    flex: 1;
    min-width: 150px;
}

.form-row {
    display: grid;
    grid-template-columns: 1fr 1fr auto;
    gap: 9px;
    align-items: center;
}

.form-row button {
    white-space: nowrap;
}

.table-wrap {
    overflow-x: auto;
    width: 100%;
    -webkit-overflow-scrolling: touch;
}

table {
    width: 100%;
    min-width: 550px;
    border-collapse: collapse;
    font-size: 17px;
}

th {
    color: var(--green);
    text-align: left;
    background: #0d2115;
    font-size: 18px;
    font-weight: 800;
    letter-spacing: .3px;
}

td, th {
    padding: 16px 12px;
    border-bottom: 1px solid #173522;
    white-space: nowrap;
}

td {
    color: #b7d9c3;
    font-size: 17px;
}

tr:hover td {
    background: #0c1e13;
}

.badge {
    display: inline-block;
    padding: 7px 10px;
    border-radius: 5px;
    font-size: 15px;
    font-weight: 700;
    background: #14532d;
    color: #86efac;
}

.badge.blocked {
    background: #4c0519;
    color: #fda4af;
}

footer {
    text-align: center;
    color: #456c53;
    padding: 22px;
    font-size: 15px;
}

@media(max-width: 800px) {
    .grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}

@media(max-width: 600px) {
    body {
        font-size: 19px;
    }

    main {
        padding: 14px;
    }

    header {
        padding: 14px;
    }

    .brand {
        font-size: 17px;
    }

    .logout {
        font-size: 15px;
        padding: 10px 12px;
    }

    .grid {
        gap: 10px;
    }

    .card {
        padding: 15px;
        margin-bottom: 13px;
    }

    .stat {
        min-height: 120px;
    }

    .stat-label {
        font-size: 14px;
    }

    .number {
        font-size: 30px;
    }

    .heading h2 {
        font-size: 27px;
    }

    h3 {
        font-size: 21px;
    }

    .section-label {
        font-size: 15px;
    }

    .form-row {
        grid-template-columns: 1fr;
    }

    .form-row button {
        width: 100%;
    }

    button, input {
        font-size: 18px;
        padding: 15px;
    }

    .controls {
        flex-direction: column;
    }

    .controls button {
        width: 100%;
    }

    table {
        font-size: 16px;
    }

    th {
        font-size: 17px;
    }

    td {
        font-size: 16px;
    }
}
</style>
</head>

<body>

<header>
    <div class="brand">☠ FREE ARPIT // OSINT</div>
    <a class="logout" href="/logout">LOGOUT ↗</a>
</header>

<main>

    <div class="heading">
        <h2>CONTROL CENTER</h2>
        <div class="muted">Bot management and system analytics</div>

        <div class="system-status">
            <span class="dot"></span>
            SYSTEM CONNECTED
            <span id="lastUpdate"></span>
        </div>
    </div>

    <div class="grid">

        <div class="card stat">
            <div class="stat-icon">👥</div>
            <div class="stat-label">Total Users</div>
            <div class="number" id="users">0</div>
        </div>

        <div class="card stat">
            <div class="stat-icon">⌕</div>
            <div class="stat-label">Total Searches</div>
            <div class="number" id="searches">0</div>
        </div>

        <div class="card stat">
            <div class="stat-icon">⛔</div>
            <div class="stat-label">Blocked Users</div>
            <div class="number" id="blocked">0</div>
        </div>

        <div class="card stat">
            <div class="stat-icon">◈</div>
            <div class="stat-label">Available Credits</div>
            <div class="number" id="credits">0</div>
        </div>

    </div>

    <div class="card">
        <h3>⚙ SYSTEM CONFIGURATION</h3>

        <div class="section-label">
            MAINTENANCE MODE:
            <strong id="maintenance">LOADING...</strong>
        </div>

        <div class="controls">
            <button onclick="setMaintenance(true)">
                ENABLE MAINTENANCE
            </button>

            <button class="success" onclick="setMaintenance(false)">
                DISABLE MAINTENANCE
            </button>
        </div>
    </div>

    <div class="card">
        <h3>◈ CREDIT MANAGEMENT</h3>

        <div class="form-row">
            <input
                id="creditUser"
                inputmode="numeric"
                placeholder="Telegram User ID"
            >

            <input
                id="creditAmount"
                type="number"
                min="1"
                max="100000"
                placeholder="Credits amount"
            >

            <button onclick="addCredits()">ADD CREDITS</button>
        </div>
    </div>

    <div class="card">
        <h3>👥 USER DATABASE</h3>
        <div class="section-label">REGISTERED USERS AND ACCOUNT STATUS</div>

        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>USER ID</th>
                        <th>USERNAME</th>
                        <th>CREDITS</th>
                        <th>STATUS</th>
                        <th>ACTION</th>
                    </tr>
                </thead>
                <tbody id="userRows"></tbody>
            </table>
        </div>
    </div>

    <div class="card">
        <h3>⌕ RECENT SEARCH ACTIVITY</h3>
        <div class="section-label">LATEST 20 SEARCH RECORDS</div>

        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>USER</th>
                        <th>TYPE</th>
                        <th>QUERY</th>
                        <th>DATE</th>
                    </tr>
                </thead>
                <tbody id="searchRows"></tbody>
            </table>
        </div>
    </div>

</main>

<footer>
    FREE ARPIT OSINT BOT // SECURE ADMIN PANEL
</footer>

<script>
async function api(url, options = {}) {
    const response = await fetch(url, options);

    if (response.status === 401) {
        location.href = "/login";
        return {};
    }

    return response.json();
}


async function loadDashboard() {
    try {
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

        document.getElementById("lastUpdate").textContent =
            " | UPDATED " + new Date().toLocaleTimeString();

        const rows = document.getElementById("userRows");
        rows.replaceChildren();

        data.users.forEach(user => {
            const tr = document.createElement("tr");

            const values = [
                user.user_id,
                user.username || "N/A",
                user.credits
            ];

            values.forEach(value => {
                const td = document.createElement("td");
                td.textContent = value;
                tr.appendChild(td);
            });

            const status = document.createElement("td");
            const badge = document.createElement("span");

            badge.className = user.is_blocked
                ? "badge blocked"
                : "badge";

            badge.textContent = user.is_blocked
                ? "BLOCKED"
                : "ACTIVE";

            status.appendChild(badge);
            tr.appendChild(status);

            const action = document.createElement("td");
            const button = document.createElement("button");

            button.textContent = user.is_blocked
                ? "UNBLOCK"
                : "BLOCK";

            button.className = user.is_blocked
                ? "success"
                : "danger";

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
                td.textContent = value ?? "N/A";
                tr.appendChild(td);
            });

            searchRows.appendChild(tr);
        });

    } catch (error) {
        console.error("Dashboard refresh failed:", error);
    }
}


async function addCredits() {
    const user_id =
        document.getElementById("creditUser").value;

    const amount =
        document.getElementById("creditAmount").value;

    const result = await api("/api/credits", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({user_id, amount})
    });

    alert(result.message || result.error || "Request failed");

    loadDashboard();
}


async function toggleBlock(user_id, blocked) {
    const result = await api("/api/block", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({user_id, blocked})
    });

    alert(result.message || result.error || "Request failed");

    loadDashboard();
}


async function setMaintenance(enabled) {
    const result = await api("/api/maintenance", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({enabled})
    });

    alert(result.message || result.error || "Request failed");

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
        return jsonify({
            "error": "Invalid user ID or amount"
        }), 400

    if not db.get_user(user_id):
        return jsonify({"error": "User not found"}), 404

    db.add_credits(user_id, amount)

    return jsonify({
        "message": "Credits added successfully"
    })


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
        return jsonify({
            "error": "Cannot block primary admin"
        }), 400

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
