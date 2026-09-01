"""
Single-record JSON store for site-wide content the admin controls:
author name/photo/bio and the homepage hero text. Separate from db.py
because it's one object, not a list of rows.
"""
import json
import os

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "settings.json")

DEFAULTS = {
    "penName": "Your Pen Name",
    "heroHeadline": "Stories You'll Still Be Thinking About At 2am",
    "heroSubheadline": "Slow-burn, forbidden, impossible to put down. Pay by card or crypto — instant download, every time.",
    "authorPhotoUrl": "",
    "authorBio": "A short, genre-appropriate bio — what draws you to writing dark/paranormal romance, and what readers can expect across your catalog.",
    "contactEmail": "",
    "cardEnabled": False,
    "stripeSecretKey": "",
    "stripeWebhookSecret": "",
    "stripeSubscriptionPriceId": "",
    "cryptoEnabled": False,
    "nowpaymentsApiKey": "",
    "nowpaymentsIpnSecret": "",
    "subscriptionPriceLabel": "$9.99/mo",
    "subscriptionCtaText": "Want unlimited access? Become a premium member.",
    "subscriptionBenefitsRegular": ["Buy books one at a time", "Standard download access", "Email support"],
    "subscriptionBenefitsPremium": ["Unlimited access to the entire catalog", "Every new release, included automatically", "Priority support"],
}

if not os.path.exists(SETTINGS_FILE):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(DEFAULTS, f, indent=2)


def read_settings() -> dict:
    with open(SETTINGS_FILE, "r") as f:
        data = json.load(f)
    return {**DEFAULTS, **data}


PUBLIC_FIELDS = [
    "penName", "heroHeadline", "heroSubheadline", "authorPhotoUrl", "authorBio",
    "contactEmail", "cardEnabled", "cryptoEnabled",
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
