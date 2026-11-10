import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from app.database import fetch_all, execute
from app.scraper import scrape_product, ScrapeError
from app.email_service import send_price_alert

logger = logging.getLogger(__name__)
_scheduler = None

def check_all_products(app):
    with app.app_context():
        products = fetch_all(
            "SELECT id, product_url, product_name, target_price, alert_email, last_alerted_at "
            "FROM products WHERE is_active = TRUE"
        )
        for product in products:
            try:
                result = scrape_product(product["product_url"])
                execute(
                    "INSERT INTO price_history (product_id, price, currency) VALUES (%s,%s,%s)",
                    (product["id"], result["price"], result["currency"])
                )
                execute(
                    "UPDATE products SET product_name=%s, current_price=%s, last_checked_at=NOW() WHERE id=%s",
                    (result["name"], result["price"], product["id"])
                )
                if result["price"] > product["target_price"]:
                    execute("UPDATE products SET last_alerted_at=NULL WHERE id=%s", (product["id"],))
                elif not product["last_alerted_at"]:
                    try:
                        send_price_alert(
                            product["alert_email"], result["name"], product["product_url"],
                            result["price"], product["target_price"]
                        )
                        execute("UPDATE products SET last_alerted_at=NOW() WHERE id=%s", (product["id"],))
                    except Exception:
                        logger.exception("Price alert email failed for product %s", product["id"])
            except ScrapeError:
                logger.warning("Scraping failed for product %s", product["id"], exc_info=True)
            except Exception:
                logger.exception("Price check failed for product %s", product["id"])

def start_scheduler(app):
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler
    _scheduler = BackgroundScheduler(
        timezone="Asia/Kolkata",
        executors={"default": ThreadPoolExecutor(3)},
        job_defaults={"coalesce": True, "max_instances": 1}
    )
    _scheduler.add_job(
        check_all_products, "interval", hours=6, args=[app],
        id="six_hour_price_check", replace_existing=True
    )
    _scheduler.start()
    return _scheduler
