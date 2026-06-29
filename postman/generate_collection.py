#!/usr/bin/env python3
"""Generate postman/GoLuto-API.postman_collection.json from endpoint definitions."""

from __future__ import annotations

import json
import uuid
from copy import deepcopy
from pathlib import Path

COLLECTION_ID = str(uuid.uuid4())
ROOT = Path(__file__).resolve().parent

CONSUMER_LOGIN_TEST = """
if (pm.response.code === 200 || pm.response.code === 201) {
    const json = pm.response.json();
    if (json.access) {
        pm.environment.set('consumer_token', json.access);
        pm.collectionVariables.set('consumer_token', json.access);
    }
}
""".strip()

BUSINESS_LOGIN_TEST = """
if (pm.response.code === 200 || pm.response.code === 201) {
    const json = pm.response.json();
    if (json.access) {
        pm.environment.set('business_token', json.access);
        pm.collectionVariables.set('business_token', json.access);
    }
}
""".strip()

SAVE_QR_CODE_TEST = """
if (pm.response.code === 200) {
    const json = pm.response.json();
    const offers = Array.isArray(json) ? json : (json.results || []);
    const offer = offers.find(o => String(o.id) === pm.environment.get('offer_id')) || offers[0];
    if (offer && offer.qr_code) {
        pm.environment.set('qr_code', offer.qr_code);
        pm.collectionVariables.set('qr_code', offer.qr_code);
    }
}
""".strip()


def req(
    name: str,
    method: str,
    path: str,
    *,
    body: dict | None = None,
    query: list[tuple[str, str]] | None = None,
    description: str = "",
    test: str | None = None,
    auth_bearer: str | None = None,
):
    url_parts = ["{{base_url}}"] + [p for p in path.strip("/").split("/") if p]
    raw = "{{base_url}}/" + path.strip("/")
    item: dict = {
        "name": name,
        "request": {
            "method": method,
            "header": [],
            "url": {
                "raw": raw,
                "host": ["{{base_url}}"],
                "path": [p for p in path.strip("/").split("/") if p],
            },
            "description": description,
        },
    }
    if method in ("POST", "PUT", "PATCH"):
        item["request"]["header"].append(
            {"key": "Content-Type", "value": "application/json"}
        )
    if query:
        item["request"]["url"]["query"] = [
            {"key": k, "value": v, "disabled": False} for k, v in query
        ]
    if body is not None:
        item["request"]["body"] = {
            "mode": "raw",
            "raw": json.dumps(body, indent=2),
            "options": {"raw": {"language": "json"}},
        }
    if auth_bearer:
        item["request"]["auth"] = {
            "type": "bearer",
            "bearer": [{"key": "token", "value": auth_bearer, "type": "string"}],
        }
    if test:
        item["event"] = [
            {"listen": "test", "script": {"type": "text/javascript", "exec": test.split("\n")}}
        ]
    return item


def folder(name: str, items: list, *, auth_bearer: str | None = None, description: str = ""):
    node: dict = {"name": name, "item": items, "description": description}
    if auth_bearer:
        node["auth"] = {
            "type": "bearer",
            "bearer": [{"key": "token", "value": auth_bearer, "type": "string"}],
        }
    return node


collection = {
    "info": {
        "_postman_id": COLLECTION_ID,
        "name": "GoLuto API",
        "description": (
            "Discount Discovery API — categories, offers, map, consumer & business accounts.\n\n"
            "**Quick start**\n"
            "1. Import `GoLuto-Production.postman_environment.json` (or Local).\n"
            "2. Select the environment in Postman.\n"
            "3. Run **Auth → Consumer Login** or **Business Login** to store JWT tokens.\n"
            "4. Call protected endpoints in the Consumer / Business folders.\n\n"
            "**Live docs:** https://goluto-backend.onrender.com/api/docs/\n"
            "**OpenAPI schema:** https://goluto-backend.onrender.com/api/schema/"
        ),
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
    },
    "variable": [
        {"key": "base_url", "value": "https://goluto-backend.onrender.com"},
        {"key": "consumer_token", "value": ""},
        {"key": "business_token", "value": ""},
        {"key": "offer_id", "value": "1"},
        {"key": "branch_id", "value": "1"},
        {"key": "business_id", "value": "1"},
        {"key": "address_id", "value": "addr_1"},
        {"key": "qr_code", "value": ""},
    ],
    "item": [
        folder(
            "Auth — Consumer",
            [
                req(
                    "Register",
                    "POST",
                    "api/auth/register",
                    body={
                        "name": "Jane Doe",
                        "email": "jane@example.com",
                        "password": "SecurePass123!",
                        "password_confirm": "SecurePass123!",
                    },
                    description="Create a consumer account.",
                ),
                req(
                    "Login",
                    "POST",
                    "api/auth/token",
                    body={
                        "email": "consumer@example.com",
                        "password": "your-password",
                    },
                    description="Returns JWT access token. Saves token to environment automatically.",
                    test=CONSUMER_LOGIN_TEST,
                ),
                req(
                    "Refresh Token",
                    "POST",
                    "api/auth/token/refresh",
                    body={"refresh": "<paste refresh token if you have one>"},
                    description="Login response may omit refresh; use only if your client stores it.",
                ),
                req(
                    "Verify Token",
                    "POST",
                    "api/auth/token/verify",
                    body={"token": "{{consumer_token}}"},
                ),
                req(
                    "Logout",
                    "POST",
                    "api/auth/logout",
                    auth_bearer="{{consumer_token}}",
                    description="Invalidates refresh tokens for the user. Discard the access token on the client.",
                ),
                req(
                    "Forgot Password",
                    "POST",
                    "api/auth/password/forgot",
                    body={"email": "consumer@example.com"},
                ),
                req(
                    "Reset Password",
                    "POST",
                    "api/auth/password/reset",
                    body={
                        "token": "<uuid from email>",
                        "password": "NewSecurePass123!",
                        "password_confirm": "NewSecurePass123!",
                    },
                ),
            ],
        ),
        folder(
            "Auth — Business",
            [
                req(
                    "Register",
                    "POST",
                    "api/business/auth/register",
                    body={
                        "name": "My Cafe",
                        "email": "cafe@example.com",
                        "password": "SecurePass123!",
                        "password_confirm": "SecurePass123!",
                        "category_id": 1,
                    },
                    description="JSON body. For logo upload use form-data in Postman instead.",
                ),
                req(
                    "Login",
                    "POST",
                    "api/business/auth/token",
                    body={
                        "email": "business@example.com",
                        "password": "your-password",
                    },
                    description="Business JWT. Saves token to environment automatically.",
                    test=BUSINESS_LOGIN_TEST,
                ),
                req(
                    "Logout",
                    "POST",
                    "api/business/auth/logout",
                    auth_bearer="{{business_token}}",
                    description="Invalidates refresh tokens for the business user. Discard the access token on the client.",
                ),
            ],
        ),
        folder(
            "Public",
            [
                req("List Categories", "GET", "api/categories"),
                req(
                    "List Offers",
                    "GET",
                    "api/offers",
                    query=[
                        ("category_id", ""),
                        ("branch_id", ""),
                    ],
                    description="Optional filters — enable query params and set values as needed.",
                    test=SAVE_QR_CODE_TEST,
                ),
                req(
                    "Map Branches",
                    "GET",
                    "api/map/branches",
                    query=[("category_id", "")],
                ),
                req(
                    "Map Businesses",
                    "GET",
                    "api/map/businesses",
                    query=[("category_id", "")],
                ),
                req(
                    "Business Offers",
                    "GET",
                    "api/business/{{business_id}}/offers",
                ),
                req(
                    "Branch Offers",
                    "GET",
                    "api/branch/{{branch_id}}/offers",
                ),
            ],
        ),
        folder(
            "Consumer",
            [
                req(
                    "Get Offer Usage",
                    "GET",
                    "api/offers/{{offer_id}}/usage",
                    auth_bearer="{{consumer_token}}",
                ),
                req(
                    "List Availed Offers",
                    "GET",
                    "api/user/offers/availed",
                    auth_bearer="{{consumer_token}}",
                    description="All offers the user has redeemed, newest first, with branch details.",
                ),
                req(
                    "Resolve Poster QR",
                    "GET",
                    "api/offers/by-qr/{{qr_code}}?branch_id={{branch_id}}",
                    auth_bearer="{{consumer_token}}",
                    description="Poster QR flow: resolve offer + branch + payment. Add &bill_amount=80.00 for percentage offers. No business dashboard needed.",
                ),
                req(
                    "Payment Preview",
                    "POST",
                    "api/offers/{{offer_id}}/payment-preview",
                    body={"bill_amount": "80.00"},
                    auth_bearer="{{consumer_token}}",
                    description="Preview amount to pay before scanning. bill_amount required for percentage_bill offers; omit for item offers.",
                ),
                req(
                    "Scan Offer",
                    "POST",
                    "api/offers/{{offer_id}}/scan",
                    body={
                        "branch_id": "{{branch_id}}",
                        "qr_code": "{{qr_code}}",
                        "bill_amount": "80.00",
                    },
                    auth_bearer="{{consumer_token}}",
                    description="Get qr_code from an offer list/detail response first. bill_amount required for percentage_bill offers. Response includes payment.amount_to_pay.",
                ),
                req(
                    "Avail Offer (Poster QR)",
                    "POST",
                    "api/offers/{{offer_id}}/avail",
                    body={
                        "branch_id": "{{branch_id}}",
                        "qr_code": "{{qr_code}}",
                        "bill_amount": "80.00",
                    },
                    auth_bearer="{{consumer_token}}",
                    description="Single-step poster flow: scan + redeem. Customer shows payment.summary screen at counter. bill_amount required for percentage offers.",
                ),
                req(
                    "Redeem Offer",
                    "POST",
                    "api/offers/{{offer_id}}/redeem",
                    body={
                        "branch_id": "{{branch_id}}",
                        "qr_code": "{{qr_code}}",
                        "bill_amount": "80.00",
                    },
                    auth_bearer="{{consumer_token}}",
                    description="bill_amount required for percentage_bill offers. Response includes payment.amount_to_pay.",
                ),
                req(
                    "Get Preferences",
                    "GET",
                    "api/user/preferences",
                    auth_bearer="{{consumer_token}}",
                ),
                req(
                    "Update Preferences",
                    "PUT",
                    "api/user/preferences",
                    body={
                        "notifications_enabled": True,
                        "preferred_categories": [1, 2],
                    },
                    auth_bearer="{{consumer_token}}",
                ),
                req(
                    "List Addresses",
                    "GET",
                    "api/user/addresses",
                    auth_bearer="{{consumer_token}}",
                ),
                req(
                    "Create Address",
                    "POST",
                    "api/user/addresses",
                    body={
                        "street": "Main St",
                        "houseNumber": "12",
                        "postalCode": "10115",
                        "city": "Berlin",
                        "county": "Berlin",
                        "latitude": 52.52,
                        "longitude": 13.405,
                        "isDefault": True,
                    },
                    auth_bearer="{{consumer_token}}",
                ),
                req(
                    "Get Address",
                    "GET",
                    "api/user/addresses/{{address_id}}",
                    auth_bearer="{{consumer_token}}",
                ),
                req(
                    "Update Address",
                    "PUT",
                    "api/user/addresses/{{address_id}}",
                    body={
                        "street": "Main St",
                        "houseNumber": "12A",
                        "postalCode": "10115",
                        "city": "Berlin",
                        "county": "Berlin",
                        "latitude": 52.52,
                        "longitude": 13.405,
                        "isDefault": True,
                    },
                    auth_bearer="{{consumer_token}}",
                ),
                req(
                    "Delete Address",
                    "DELETE",
                    "api/user/addresses/{{address_id}}",
                    auth_bearer="{{consumer_token}}",
                ),
            ],
            auth_bearer="{{consumer_token}}",
            description="Requires consumer JWT. Run Auth → Consumer Login first.",
        ),
        folder(
            "Business",
            [
                req(
                    "Get Profile",
                    "GET",
                    "api/business/profile",
                    auth_bearer="{{business_token}}",
                ),
                req(
                    "Update Profile",
                    "PUT",
                    "api/business/profile",
                    body={"name": "Updated Business Name", "category_id": 1},
                    auth_bearer="{{business_token}}",
                ),
                req(
                    "List Branches",
                    "GET",
                    "api/business/branches",
                    auth_bearer="{{business_token}}",
                ),
                req(
                    "Create Branch",
                    "POST",
                    "api/business/branches",
                    body={
                        "name": "Downtown",
                        "street": "Alexanderplatz",
                        "house_number": "1",
                        "postal_code": "10178",
                        "city": "Berlin",
                        "latitude": 52.5219,
                        "longitude": 13.4132,
                    },
                    auth_bearer="{{business_token}}",
                ),
                req(
                    "Get Branch",
                    "GET",
                    "api/business/branches/{{branch_id}}",
                    auth_bearer="{{business_token}}",
                ),
                req(
                    "Update Branch",
                    "PUT",
                    "api/business/branches/{{branch_id}}",
                    body={
                        "name": "Downtown",
                        "street": "Alexanderplatz",
                        "house_number": "1",
                        "postal_code": "10178",
                        "city": "Berlin",
                        "latitude": 52.5219,
                        "longitude": 13.4132,
                    },
                    auth_bearer="{{business_token}}",
                ),
                req(
                    "Delete Branch",
                    "DELETE",
                    "api/business/branches/{{branch_id}}",
                    auth_bearer="{{business_token}}",
                ),
                req(
                    "List Offers",
                    "GET",
                    "api/business/offers",
                    auth_bearer="{{business_token}}",
                    test=SAVE_QR_CODE_TEST,
                ),
                req(
                    "Create Offer (percentage)",
                    "POST",
                    "api/business/offers",
                    body={
                        "offer_type": "percentage_bill",
                        "title": "10% off entire bill",
                        "description": "Weekday lunch special",
                        "discount_percent": "10.00",
                        "usage_limit_type": "one_time",
                        "usage_limit_count": 1,
                        "branch_ids": [1],
                        "is_enabled": True,
                        "is_time_limited": False,
                    },
                    auth_bearer="{{business_token}}",
                ),
                req(
                    "Create Offer (item)",
                    "POST",
                    "api/business/offers",
                    body={
                        "offer_type": "item",
                        "title": "Burger deal",
                        "item_name": "Classic Burger",
                        "original_price": "12.00",
                        "discounted_price": "8.00",
                        "usage_limit_type": "once_per_week",
                        "usage_limit_count": 1,
                        "branch_ids": [1],
                        "is_enabled": True,
                    },
                    auth_bearer="{{business_token}}",
                ),
                req(
                    "Get Offer",
                    "GET",
                    "api/business/offers/{{offer_id}}",
                    auth_bearer="{{business_token}}",
                ),
                req(
                    "Update Offer",
                    "PUT",
                    "api/business/offers/{{offer_id}}",
                    body={
                        "offer_type": "percentage_bill",
                        "title": "Updated offer title",
                        "discount_percent": "15.00",
                        "usage_limit_type": "one_time",
                        "usage_limit_count": 1,
                        "branch_ids": [1],
                        "is_enabled": True,
                    },
                    auth_bearer="{{business_token}}",
                ),
                req(
                    "Delete Offer",
                    "DELETE",
                    "api/business/offers/{{offer_id}}",
                    auth_bearer="{{business_token}}",
                ),
            ],
            auth_bearer="{{business_token}}",
            description="Requires business JWT. Run Auth → Business Login first.",
        ),
    ],
}

out = ROOT / "GoLuto-API.postman_collection.json"
out.write_text(json.dumps(collection, indent=2) + "\n", encoding="utf-8")
print(f"Wrote {out}")
