# ================================================
# create_user.py – Kreiranje admin korisnika
# Pokretanje: python create_user.py
# ================================================

import sqlite3
from werkzeug.security import generate_password_hash

DB_PATH = "products.db"

def create_user():
    print("=== Kreiranje novog korisnika ===\n")
    username = input("Korisnicko ime: ").strip()
    password = input("Lozinka:        ").strip()

    if not username or not password:
        print("Greska: korisnicko ime i lozinka ne mogu biti prazni.")
        return

    if len(password) < 6:
        print("Greska: lozinka mora imati najmanje 6 karaktera.")
        return

    password_hash = generate_password_hash(password)

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash)
        )
        conn.commit()
        conn.close()
        print(f"\nKorisnik '{username}' uspesno kreiran!")
    except sqlite3.IntegrityError:
        print(f"\nGreska: korisnik '{username}' vec postoji.")

if __name__ == "__main__":
    create_user()
