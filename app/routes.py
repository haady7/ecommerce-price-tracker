import re
from decimal import Decimal, InvalidOperation
from flask import Blueprint, jsonify, render_template, request
from app.database import fetch_all, fetch_one, execute
from app.scraper import scrape_product, ScrapeError, validate_public_url

api = Blueprint("api", __name__)

def valid_email(value):
    return bool(re.fullmatch(r"[^\\s@]+@[^\\s@]+\\.[^\\s@]+", value or ""))

@api.get("/")
def home():
    return render_template("index.html")

@api.get("/api/health")
def health():
    try:
        fetch_one("SELECT 1 AS ok")
        return jsonify({"status": "ok", "database": "connected"})
    except Exception:
        return jsonify({"status": "error", "database": "unavailable"}), 503

@api.get("/api/products")
def list_products():
    rows = fetch_all(
        "SELECT id, product_url, product_name, current_price, target_price, currency, "
        "alert_email, is_active, last_checked_at, created_at FROM products ORDER BY created_at DESC"
    )
    for row in rows:
        for key in ("current_price", "target_price"):
            row[key] = float(row[key])
        for key in ("last_checked_at", "created_at"):
            row[key] = row[key].isoformat(sep=" ") if row[key] else None
        row["is_active"] = bool(row["is_active"])
    return jsonify(rows)

@api.post("/api/products")
def add_product():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    email = (data.get("email") or "").strip()
    try:
        target = Decimal(str(data.get("target_price", "")))
        if target <= 0 or target > Decimal("9999999999"):
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        return jsonify({"error": "Enter a valid positive target price."}), 400
    if not valid_email(email):
        return jsonify({"error": "Enter a valid email address."}), 400
    try:
        validate_public_url(url)
        product = scrape_product(url)
    except ScrapeError as exc:
        return jsonify({"error": str(exc)}), 422
    existing = fetch_one(
        "SELECT id FROM products WHERE product_url=%s AND alert_email=%s", (url, email)
    )
    if existing:
        return jsonify({"error": "This URL is already tracked for that email address."}), 409
    product_id, _ = execute(
        "INSERT INTO products (product_url, product_name, current_price, target_price, alert_email) "
        "VALUES (%s,%s,%s,%s,%s)",
        (url, product["name"], product["price"], target, email)
    )
    execute(
        "INSERT INTO price_history (product_id, price, currency) VALUES (%s,%s,%s)",
        (product_id, product["price"], product["currency"])
    )
    return jsonify({
        "message": "Product added successfully.",
        "product": {
            "id": product_id, "product_name": product["name"],
            "current_price": float(product["price"]), "target_price": float(target)
        }
    }), 201

@api.delete("/api/products/<int:product_id>")
def delete_product(product_id):
    _, count = execute("DELETE FROM products WHERE id=%s", (product_id,))
    if not count:
        return jsonify({"error": "Product not found."}), 404
    return jsonify({"message": "Product and its price history deleted."})

@api.get("/api/products/<int:product_id>/history")
def product_history(product_id):
    product = fetch_one("SELECT id FROM products WHERE id=%s", (product_id,))
    if not product:
        return jsonify({"error": "Product not found."}), 404
    rows = fetch_all(
        "SELECT price, currency, recorded_at FROM price_history "
        "WHERE product_id=%s ORDER BY recorded_at ASC", (product_id,)
    )
    return jsonify([
        {"price": float(r["price"]), "currency": r["currency"],
         "recorded_at": r["recorded_at"].isoformat(sep=" ")}
        for r in rows
    ])
