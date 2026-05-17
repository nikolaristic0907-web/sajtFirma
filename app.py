# ================================================
# app.py – Glavni Flask server
# Pokreni sa: python app.py
# ================================================

from flask import Flask, request, jsonify
import sqlite3

app = Flask(__name__)
DB_PATH = "products.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Tabela kategorija
    c.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name  TEXT NOT NULL UNIQUE,
            label TEXT NOT NULL
        )
    """)

    # Ubaci podrazumevane kategorije ako tabela prazna
    c.execute("SELECT COUNT(*) FROM categories")
    if c.fetchone()[0] == 0:
        default_cats = [
            ("frižider",  "Frižideri"),
            ("zamrzivač", "Zamrzivači"),
            ("vitrina",   "Vitrine"),
            ("klima",     "Klime"),
        ]
        c.executemany("INSERT OR IGNORE INTO categories (name, label) VALUES (?,?)", default_cats)

    # Tabela proizvoda (bez emoji i badge)
    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            category    TEXT    NOT NULL,
            description TEXT,
            price       REAL    NOT NULL,
            img_url     TEXT,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── Migracija: ukloni emoji/badge kolone ako postoje ─────────────────────
    c.execute("PRAGMA table_info(products)")
    cols = {row[1] for row in c.fetchall()}

    if "emoji" in cols or "badge" in cols:
        c.execute("ALTER TABLE products RENAME TO products_old")
        c.execute("""
            CREATE TABLE products (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                category    TEXT    NOT NULL,
                description TEXT,
                price       REAL    NOT NULL,
                img_url     TEXT,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            INSERT INTO products (id, name, category, description, price, img_url, created_at)
            SELECT id, name, category, description, price, img_url, created_at
            FROM products_old
        """)
        c.execute("DROP TABLE products_old")
        print("[DB] Migracija zavrsena: uklonjene kolone emoji i badge.")

    conn.commit()
    conn.close()


def row_to_dict(row):
    return {
        "id":          row[0],
        "name":        row[1],
        "category":    row[2],
        "description": row[3],
        "price":       row[4],
        "img_url":     row[5],
        "created_at":  row[6],
    }


# ═══════════════════════════════════════════════
# KATEGORIJE – API
# ═══════════════════════════════════════════════

@app.route("/api/categories", methods=["GET"])
def get_categories():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, label FROM categories ORDER BY id ASC")
    rows = c.fetchall()
    conn.close()
    return jsonify([{"id": r[0], "name": r[1], "label": r[2]} for r in rows])


@app.route("/api/categories", methods=["POST"])
def add_category():
    data  = request.get_json()
    name  = (data.get("name")  or "").strip()
    label = (data.get("label") or "").strip()
    if not name or not label:
        return jsonify({"error": "Polja 'name' i 'label' su obavezna"}), 400
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO categories (name, label) VALUES (?,?)", (name, label))
        new_id = c.lastrowid
        conn.commit()
        conn.close()
        return jsonify({"message": "Kategorija dodata", "id": new_id}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": f"Kategorija '{name}' vec postoji"}), 409


@app.route("/api/categories/<int:cat_id>", methods=["DELETE"])
def delete_category(cat_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM categories WHERE id = ?", (cat_id,))
    if c.fetchone() is None:
        conn.close()
        return jsonify({"error": "Kategorija nije pronadjena"}), 404
    c.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Kategorija obrisana"})


# ═══════════════════════════════════════════════
# PROIZVODI – API
# ═══════════════════════════════════════════════

@app.route("/api/products", methods=["GET"])
def get_products():
    category  = request.args.get("category", "").strip()
    search    = request.args.get("search", "").strip()
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)

    query  = "SELECT * FROM products WHERE 1=1"
    params = []

    if category:
        query += " AND category = ?"
        params.append(category)
    if search:
        query += " AND (name LIKE ? OR description LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    if min_price is not None:
        query += " AND price >= ?"
        params.append(min_price)
    if max_price is not None:
        query += " AND price <= ?"
        params.append(max_price)

    query += " ORDER BY id ASC"

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return jsonify([row_to_dict(r) for r in rows])


@app.route("/api/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    row = c.fetchone()
    conn.close()
    if row is None:
        return jsonify({"error": "Proizvod nije pronadjen"}), 404
    return jsonify(row_to_dict(row))


@app.route("/api/products", methods=["POST"])
def add_product():
    data = request.get_json()
    for field in ["name", "category", "price"]:
        if not data.get(field):
            return jsonify({"error": f"Polje '{field}' je obavezno"}), 400
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO products (name, category, description, price, img_url) VALUES (?,?,?,?,?)",
        (data["name"], data["category"], data.get("description", ""),
         data["price"], data.get("img_url", ""))
    )
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return jsonify({"message": "Proizvod dodat", "id": new_id}), 201


@app.route("/api/products/<int:product_id>", methods=["PUT"])
def update_product(product_id):
    data = request.get_json()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM products WHERE id = ?", (product_id,))
    if c.fetchone() is None:
        conn.close()
        return jsonify({"error": "Proizvod nije pronadjen"}), 404
    c.execute("""
        UPDATE products SET name=?, category=?, description=?, price=?, img_url=?
        WHERE id=?
    """, (data["name"], data["category"], data.get("description", ""),
          data["price"], data.get("img_url", ""), product_id))
    conn.commit()
    conn.close()
    return jsonify({"message": "Proizvod azuriran"})


@app.route("/api/products/<int:product_id>", methods=["DELETE"])
def delete_product(product_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM products WHERE id = ?", (product_id,))
    if c.fetchone() is None:
        conn.close()
        return jsonify({"error": "Proizvod nije pronadjen"}), 404
    c.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Proizvod obrisan"})


# ═══════════════════════════════════════════════
# STRANICE
# ═══════════════════════════════════════════════

@app.route("/admin")
def admin():
    with open("admin.html", "r", encoding="utf-8") as f:
        return f.read()


@app.route("/")
def index():
    with open("hladnjak-shop.html", "r", encoding="utf-8") as f:
        return f.read()


# ═══════════════════════════════════════════════
# START
# ═══════════════════════════════════════════════
if __name__ == "__main__":
    init_db()
    print("Server pokrenut: http://localhost:5000")
    app.run(debug=True)
