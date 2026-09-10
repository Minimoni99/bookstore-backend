"""
Single-record JSON store for site-wide content the admin controls:
author name/photo/bio and the homepage hero text. Separate from db.py
because it's one object, not a list of rows.
"""
import json
import os

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "settings.json")

DEFAULTS = {
    "heroHeadline": "Built For Men Who Build Real Businesses.",
    "heroSubheadline": "A private network of construction and real estate operators. Rooms built around the work you actually do.",
    "heroVideoUrl": "",
    "contactEmail": "",
    "whatsappLink": "",
    "telegramLink": "",
    "membershipMessageTemplate": "Hi, I'm interested in joining the membership. My name is {name}.",
    "subscriptionPriceLabel": "$37/mo",
    "subscriptionCtaText": "GET ACCESS",
    "subscriptionBenefitsRegular": [],
    "subscriptionBenefitsPremium": ["Full access to every room — Construction and Real Estate", "Live weekly coach sessions, plus every past recording", "The Vault — guides, templates, quotes, and contracts", "Direct access to operators at every level"],
}

if not os.path.exists(SETTINGS_FILE):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(DEFAULTS, f, indent=2)


def read_settings() -> dict:
    with open(SETTINGS_FILE, "r") as f:
        data = json.load(f)
    return {**DEFAULTS, **data}


PUBLIC_FIELDS = [
    "heroHeadline", "heroSubheadline", "heroVideoUrl",
    "contactEmail", "whatsappLink", "telegramLink", "membershipMessageTemplate",
    "subscriptionPriceLabel", "subscriptionCtaText", "subscriptionBenefitsRegular", "subscriptionBenefitsPremium",
]


def public_settings() -> dict:
    """What the storefront (non-admin) is allowed to see — no keys/secrets."""
    full = read_settings()
    return {k: full[k] for k in PUBLIC_FIELDS}


def write_settings(patch: dict) -> dict:
    current = read_settings()
    updated = {**current, **patch}
    with open(SETTINGS_FILE, "w") as f:
        json.dump(updated, f, indent=2)
    return updated
