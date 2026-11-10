# PriceWatch — E-Commerce Price Drop Tracker

A Flask, MySQL and vanilla JavaScript portfolio project that records product prices, checks tracked products every six hours, and emails alerts when a target price is reached.

## Features

- Add products by URL with a target price and alert email.
- Extract product details from Schema.org Product JSON-LD and common HTML metadata.
- Store current prices and price history in MySQL.
- Check tracked products every six hours with APScheduler.
- Send SMTP email alerts when a product reaches its target price.
- Responsive dashboard to list and remove tracked products.
- REST API for products and price history.
- Power BI reporting view and DAX examples.

## Technology

Python, Flask, Requests, BeautifulSoup4, APScheduler, mysql-connector-python, MySQL, HTML5, CSS3, Vanilla JavaScript, SMTP and Power BI Desktop.

## Project structure

```text
ecommerce-price-tracker/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── scraper.py
│   ├── email_service.py
│   ├── scheduler.py
│   ├── routes.py
│   └── templates/index.html
├── static/
│   ├── css/style.css
│   └── js/app.js
├── sql/schema.sql
├── tests/test_scraper.py
├── .env.example
├── .gitignore
├── pytest.ini
├── requirements.txt
└── run.py
```

## Run locally on Windows

### Prerequisites

- Windows 10/11
- Python 3.10+
- MySQL Server 8+
- VS Code
- Power BI Desktop (optional)

### 1. Clone and open

```powershell
git clone https://github.com/haady7/ecommerce-price-tracker.git
cd ecommerce-price-tracker
```

### 2. Create a virtual environment

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and activate again.

### 3. Create the MySQL schema

Open `sql/schema.sql` in MySQL Workbench and execute it. Alternatively:

```powershell
mysql -u root -p < sql/schema.sql
```

Create an application user, replacing the password:

```sql
CREATE USER 'price_tracker'@'localhost' IDENTIFIED BY 'change-this-password';
GRANT SELECT, INSERT, UPDATE, DELETE ON price_tracker.* TO 'price_tracker'@'localhost';
FLUSH PRIVILEGES;
```

### 4. Configure environment variables

```powershell
Copy-Item .env.example .env
```

Edit `.env` with your MySQL credentials and SMTP settings. For Gmail, use a Google App Password with 2-Step Verification enabled, not your normal account password. Never commit `.env`.

### 5. Start the application

```powershell
python run.py
```

Open http://127.0.0.1:5000.

## REST API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Database health check |
| GET | `/api/products` | List tracked products |
| POST | `/api/products` | Add a product |
| DELETE | `/api/products/<id>` | Delete product and history |
| GET | `/api/products/<id>/history` | Get recorded price history |

POST JSON example:

```json
{
  "url": "https://shop.example/product",
  "target_price": 4999,
  "email": "you@example.com"
}
```

## Power BI

1. Install the MySQL Connector/NET or supported MySQL connector required by your Power BI Desktop build.
2. In Power BI Desktop choose **Get data → More → MySQL database**.
3. Enter server `127.0.0.1:3306` and database `price_tracker`.
4. Authenticate with a read-only reporting user. Example:

   ```sql
   CREATE USER 'powerbi_reader'@'localhost' IDENTIFIED BY 'use-a-strong-password';
   GRANT SELECT ON price_tracker.vw_powerbi_price_tracking TO 'powerbi_reader'@'localhost';
   FLUSH PRIVILEGES;
   ```

5. Select `vw_powerbi_price_tracking` and load it.
6. Create a calculated date column:

   ```dax
   Price Date = DATE(
       YEAR('vw_powerbi_price_tracking'[recorded_at]),
       MONTH('vw_powerbi_price_tracking'[recorded_at]),
       DAY('vw_powerbi_price_tracking'[recorded_at])
   )
   ```

7. Create these measures:

   ```dax
   Average Price (30 Days) =
   CALCULATE(
       AVERAGE('vw_powerbi_price_tracking'[historical_price]),
       DATESINPERIOD(
           'vw_powerbi_price_tracking'[Price Date],
           MAX('vw_powerbi_price_tracking'[Price Date]),
           -30,
           DAY
       )
   )
   ```

   ```dax
   Lowest Price (30 Days) =
   CALCULATE(
       MIN('vw_powerbi_price_tracking'[historical_price]),
       DATESINPERIOD(
           'vw_powerbi_price_tracking'[Price Date],
           MAX('vw_powerbi_price_tracking'[Price Date]),
           -30,
           DAY
       )
   )
   ```

   ```dax
   Discount to Target % =
   VAR CurrentPrice = MAX('vw_powerbi_price_tracking'[current_price])
   VAR TargetPrice = MAX('vw_powerbi_price_tracking'[target_price])
   RETURN IF(
       CurrentPrice > 0,
       DIVIDE(CurrentPrice - TargetPrice, CurrentPrice),
       BLANK()
   )
   ```

8. Recommended visuals: 30-day price line chart, KPI cards for average and lowest price, discount-to-target bar chart, product table, and product/date slicers. Format the discount measure as Percentage. For robust time intelligence, use a dedicated calendar table marked as the date table.

## Tests

```powershell
python -m pytest
```

## Scraping and production limitations

The scraper reads Product JSON-LD first, then common Open Graph and HTML price metadata. There is no universal scraper for all retailers: some sites render prices with JavaScript, require APIs, or restrict automated access. Respect site terms, robots policies, rate limits, and applicable law. Do not bypass CAPTCHAs or access controls.

The URL validator rejects private and non-public IP destinations. This is a baseline, not a substitute for a hardened egress proxy and DNS-rebinding protection.

APScheduler runs inside the Flask process. Keep one app process on the Windows machine; multiple worker processes would each start a scheduler. The job runs only while the app is running and does not catch up missed checks after shutdown. For reliable production deployment, move scheduled checks to a separately managed worker with a distributed lock.

Before public multi-user deployment, add authentication, CSRF protection, HTTPS, user ownership, rate limiting, hardened outbound network controls, audit logging and monitoring. Do not expose Flask's development server directly to the public internet.
