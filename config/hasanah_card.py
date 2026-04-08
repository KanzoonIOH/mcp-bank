"""
BSI Hasanah Card — Calculation Configuration
=============================================
All tunable variables for the Hasanah Card MCP calculator live here.
Change any value in this file and it takes effect across every tool
without touching the logic code.

Sources:
  - FAQ BSI Hasanah Card (suf0YQwxHuGXLCErBUIypEdgExbYGiLvxObdHpXR.pdf)
  - E-welcome Pack Petunjuk Layanan BSI Hasanah Card
    (eQw4Yyozf4oVklImj5IhXhUTR6fGErZWHn51tWxd.pdf)
  - Fatwa DSN-MUI No. 54/DSN-MUI/X/2006
"""

# ── Monthly Fee (Ujrah / Kafalah bil Ujrah) ───────────────────────────────────

# Rate applied to the approved card limit every month (Ijarah + Kafalah bil Ujrah akad).
# e.g. limit Rp 10,000,000 → monthly fee = Rp 175,000
MONTHLY_FEE_RATE: float = 1.75 / 100  # 1.75 %

# ── Cash Rebate Equivalent Rates ─────────────────────────────────────────────
# Cash rebate = (card_limit - outstanding) × eq_rate
# It reduces the monthly fee; the cardholder never pays more than MONTHLY_FEE_RATE × limit.
#
# Four scenarios depending on *when* payment is made and *how much* is paid:

# Paid before due date, full balance cleared
CASH_REBATE_BEFORE_DUE_FULL: float = 1.75 / 100  # 1.75 %

# Paid before due date, partial / minimum payment only
CASH_REBATE_BEFORE_DUE_PARTIAL: float = 1.40 / 100  # 1.40 %

# Paid after due date, full balance cleared
CASH_REBATE_AFTER_DUE_FULL: float = 1.40 / 100  # 1.40 %

# Paid after due date, partial / minimum payment only
CASH_REBATE_AFTER_DUE_PARTIAL: float = 1.35 / 100  # 1.35 %

# ── Minimum Payment ───────────────────────────────────────────────────────────

# Percentage of total bill used to calculate the minimum payment due
MIN_PAYMENT_PERCENT: float = 0.05  # 5 %

# Floor: minimum payment is never less than this amount (IDR)
MIN_PAYMENT_FLOOR: float = 50_000.0  # Rp 50,000

# ── Cash Advance (Tarik Tunai — Qard akad) ────────────────────────────────────

# Flat fee per ATM withdrawal, regardless of the amount withdrawn (IDR)
CASH_ADVANCE_FEE: float = 25_000.0  # Rp 25,000 / withdrawal

# Maximum cash advance as a fraction of the card limit
CASH_ADVANCE_MAX_PERCENT: float = 0.20  # 20 %

# ── Smart Spending (0 % Installment) ─────────────────────────────────────────

# Interest rate for Smart Spending — always zero per the product rules
SMART_SPENDING_RATE: float = 0.0  # 0 %

# Minimum transaction amount eligible for Smart Spending (IDR)
SMART_SPENDING_MIN_AMOUNT: float = 500_000.0  # Rp 500,000

# Maximum tenor (months) allowed for Smart Spending
SMART_SPENDING_MAX_TENOR: int = 12  # 12 months

# ── Billing Statement Delivery Fee ───────────────────────────────────────────

# Fee for receiving the billing statement by physical courier (IDR)
BILLING_FEE_PHYSICAL: float = 20_000.0  # Rp 20,000

# Fee for receiving the billing statement by email
BILLING_FEE_EMAIL: float = 0.0  # free

# ── Card Tier Metadata ────────────────────────────────────────────────────────
# Descriptive info per card tier used by get_card_fee_info().
# Add or remove keys here as the product evolves.

CARD_TIERS: dict = {
    "classic": {
        "card_type": "Classic",
        "akad": "Kafalah bil Ujrah, Qard, Ijarah",
        "features": [
            "Smart Spending",
            "Smart Bill",
            "Smart Sadaqah",
            "Cash Advance",
            "Perisai Plus",
        ],
    },
    "gold": {
        "card_type": "Gold",
        "akad": "Kafalah bil Ujrah, Qard, Ijarah",
        "welcome_bonus": "Rp 50,000 with Rp 1 transaction within first 3 months",
        "features": [
            "Smart Spending",
            "Smart Fund",
            "Smart Bill",
            "Smart Sadaqah",
            "Cash Advance",
            "Perisai Plus",
        ],
    },
    "platinum": {
        "card_type": "Platinum",
        "akad": "Kafalah bil Ujrah, Qard, Ijarah",
        "welcome_bonus": "Rp 150,000 with Rp 1 transaction within first 3 months",
        "executive_lounge": "Free executive lounge access (main and supplementary card)",
        "priority_benefit": "Free annual fee for life for Priority customers",
        "features": [
            "Smart Spending",
            "Smart Fund",
            "Smart Bill",
            "Smart Sadaqah",
            "Cash Advance",
            "Perisai Plus",
            "Executive Lounge",
        ],
    },
}

# ── Regulatory / Product Reference ───────────────────────────────────────────

SYARIAH_BASIS: str = "Fatwa DSN-MUI No. 54/DSN-MUI/X/2006"

PRODUCT_NOTE: str = (
    "BSI Hasanah Card is Indonesia's only Sharia-compliant credit card issued by a full "
    "Sharia bank. No interest (bunga) — fees are based on Ujrah (service fee). "
    "Cannot be used at non-halal merchants (discotheque, gambling, bar, dating/escort services)."
)
