# ================================================
# app.py – Glavni Flask server
# Pokreni sa: python app.py
# ================================================

from flask import Flask, request, jsonify, render_template_string
import sqlite3
import os

# Kreiramo Flask aplikaciju
app = Flask(__name__)

# Putanja do SQLite baze (kreira se automatski)
DB_PATH = "products.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
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
    conn.commit()
    conn.close()




#red u dict
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



# GET /api/products
# Vraca sve proizvode,filtracija i pretraga

@app.route("/api/products", methods=["GET"])
def get_products():
    category  = request.args.get("category", "").strip()
    search    = request.args.get("search", "").strip()
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)

    # Gradimo SQL upit dinamicki
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



# GET /api/products/<id>
# Vraca jedan proizvod po ID-u

@app.route("/api/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    row = c.fetchone()
    conn.close()

    if row is None:
        return jsonify({"error": "Proizvod nije pronađen"}), 404

    return jsonify(row_to_dict(row))




# Dodaje novi proizvod

@app.route("/api/products", methods=["POST"])
def add_product():
    data = request.get_json()

    # Validacija obaveznih polja
    required = ["name", "category", "price"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"Polje '{field}' je obavezno"}), 400

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO products (name, category, description, price, img_url) VALUES (?,?,?,?,?)",
        (
            data["name"],
            data["category"],
            data.get("description", ""),
            data["price"],
            data.get("img_url", ""),
        )
    )
    new_id = c.lastrowid
    conn.commit()
    conn.close()

    return jsonify({"message": "Proizvod dodat", "id": new_id}), 201



# Azurira postojeci proizvod

@app.route("/api/products/<int:product_id>", methods=["PUT"])
def update_product(product_id):
    data = request.get_json()

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # da li postoji
    c.execute("SELECT id FROM products WHERE id = ?", (product_id,))
    if c.fetchone() is None:
        conn.close()
        return jsonify({"error": "Proizvod nije pronađen"}), 404

    c.execute("""
        UPDATE products
        SET name=?, category=?, description=?, price=?, img_url=?
        WHERE id=?
    """, (
        data["name"],
        data["category"],
        data.get("description", ""),
        data["price"],
        data.get("img_url", ""),
        product_id
    ))
    conn.commit()
    conn.close()

    return jsonify({"message": "Proizvod azuriran"})



# Brisanje proizvoda

@app.route("/api/products/<int:product_id>", methods=["DELETE"])
def delete_product(product_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT id FROM products WHERE id = ?", (product_id,))
    if c.fetchone() is None:
        conn.close()
        return jsonify({"error": "Proizvod nije pronađen"}), 404

    c.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()

    return jsonify({"message": "Proizvod obrisan"})



# GET /admin

@app.route("/admin")
def admin():
    with open("admin.html", "r", encoding="utf-8") as f:
        return f.read()



# vracanje glavnog sajta

@app.route("/")
def index():
    with open("hladnjak-shop.html", "r", encoding="utf-8") as f:
        return f.read()


# ================================================
# START
# ================================================
if __name__ == "__main__":
    init_db() 
    print("Server pokrenut: http://localhost:5000")
    app.run(debug=True)