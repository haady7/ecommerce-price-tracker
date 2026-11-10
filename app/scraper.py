import ipaddress
import json
import re
import socket
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup
from flask import current_app

PRICE_PATTERN = re.compile(r"(?:₹|INR|Rs\.?|रु\.?)?\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)", re.I)

class ScrapeError(Exception):
    pass

def validate_public_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ScrapeError("Only valid HTTP and HTTPS product URLs are accepted.")
    host = parsed.hostname.lower()
    if host == "localhost" or host.endswith(".local"):
        raise ScrapeError("Local network addresses are not permitted.")
    try:
        addresses = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
        for item in addresses:
            ip = ipaddress.ip_address(item[4][0])
            if not ip.is_global:
                raise ScrapeError("Private or non-public network destinations are not permitted.")
    except socket.gaierror as exc:
        raise ScrapeError("The product website hostname could not be resolved.") from exc
    return url

def parse_price(value):
    if value is None:
        return None
    match = PRICE_PATTERN.search(str(value).replace("\u00a0", " "))
    if not match:
        return None
    try:
        amount = Decimal(match.group(1).replace(",", ""))
        if amount <= 0 or amount > Decimal("9999999999"):
            return None
        return amount.quantize(Decimal("0.01"))
    except InvalidOperation:
        return None

def _jsonld_product(soup):
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or script.get_text())
        except (json.JSONDecodeError, TypeError):
            continue
        candidates = data if isinstance(data, list) else [data]
        while candidates:
            obj = candidates.pop(0)
            if isinstance(obj, list):
                candidates.extend(obj)
                continue
            if not isinstance(obj, dict):
                continue
            if isinstance(obj.get("@graph"), list):
                candidates.extend(obj["@graph"])
            kind = obj.get("@type", [])
            if isinstance(kind, str):
                kind = [kind]
            if any(str(k).lower() == "product" for k in kind):
                offers = obj.get("offers", {})
                if isinstance(offers, list):
                    offers = offers[0] if offers else {}
                if isinstance(offers, dict):
                    price = offers.get("price") or offers.get("lowPrice")
                    name = obj.get("name")
                    parsed = parse_price(price)
                    if parsed and name:
                        return str(name).strip(), parsed
    return None, None

def scrape_product(url):
    validate_public_url(url)
    headers = {
        "User-Agent": current_app.config["SCRAPE_USER_AGENT"],
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-IN,en;q=0.9",
    }
    session = requests.Session()
    try:
        response = session.get(
            url, headers=headers, timeout=current_app.config["SCRAPE_TIMEOUT_SECONDS"],
            allow_redirects=False
        )
        if response.is_redirect:
            location = response.headers.get("Location")
            if not location:
                raise ScrapeError("The website returned an invalid redirect.")
            redirected = urljoin(url, location)
            validate_public_url(redirected)
            response = session.get(
                redirected, headers=headers,
                timeout=current_app.config["SCRAPE_TIMEOUT_SECONDS"], allow_redirects=False
            )
        response.raise_for_status()
        if "text/html" not in response.headers.get("Content-Type", "").lower():
            raise ScrapeError("The URL did not return an HTML product page.")
    except requests.RequestException as exc:
        raise ScrapeError(f"Could not retrieve product page: {exc}") from exc
    finally:
        session.close()

    soup = BeautifulSoup(response.text, "html.parser")
    name, price = _jsonld_product(soup)
    if not name:
        title = soup.find("meta", property="og:title") or soup.find("meta", attrs={"name": "title"})
        name = title.get("content", "").strip() if title else ""
        if not name and soup.title:
            name = soup.title.get_text(" ", strip=True)

    if not price:
        selectors = [
            ("meta", {"property": "product:price:amount"}, "content"),
            ("meta", {"itemprop": "price"}, "content"),
            ("meta", {"name": "price"}, "content"),
            ("span", {"class": re.compile(r"(price|sellingPrice|a-price-whole)", re.I)}, None),
            ("div", {"class": re.compile(r"(price|sellingPrice)", re.I)}, None),
            ("span", {"itemprop": "price"}, None),
        ]
        for tag, attrs, field in selectors:
            node = soup.find(tag, attrs=attrs)
            if node:
                price = parse_price(node.get(field) if field else node.get_text(" ", strip=True))
                if price:
                    break
    if not name or not price:
        raise ScrapeError(
            "Could not identify both product name and price. The site may use JavaScript "
            "rendering or a different page layout; use a supported page or authorized data feed."
        )
    return {"name": name[:500], "price": price, "currency": "INR"}
