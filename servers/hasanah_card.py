"""
BSI Hasanah Card Calculator MCP Server

All rates, fees, and limits are defined in config/hasanah_card.py.
Edit that file to update any value without touching the tool logic here.
"""

# from typing import Literal

from fastmcp import FastMCP

from config.hasanah_card import (
    BILLING_FEE_EMAIL,
    BILLING_FEE_PHYSICAL,
    CARD_TIERS,
    CASH_ADVANCE_FEE,
    CASH_ADVANCE_MAX_PERCENT,
    CASH_REBATE_AFTER_DUE_FULL,
    CASH_REBATE_AFTER_DUE_PARTIAL,
    CASH_REBATE_BEFORE_DUE_FULL,
    CASH_REBATE_BEFORE_DUE_PARTIAL,
    MIN_PAYMENT_FLOOR,
    MIN_PAYMENT_PERCENT,
    MONTHLY_FEE_RATE,
    PRODUCT_NOTE,
    SMART_SPENDING_MAX_TENOR,
    SMART_SPENDING_MIN_AMOUNT,
    SMART_SPENDING_RATE,
    SYARIAH_BASIS,
)

hasanah_card = FastMCP(name="bsi_hasanah_card")


@hasanah_card.tool()
def calculate_monthly_fee(card_limit: float) -> dict:
    """
    Calculate the gross monthly fee (ujrah) for BSI Hasanah Card.

    The monthly fee is charged every month based on the card limit,
    regardless of whether there are transactions or not. It is based
    on the Ijarah and Kafalah bil Ujrah akad at a rate of 1.75% of the limit.

    Args:
        card_limit: The approved card limit in IDR (e.g., 10000000 for Rp 10 juta).

    Returns:
        A dict with:
            - monthly_fee: Gross monthly fee in IDR
            - rate: Applied rate (1.75%)
            - card_limit: The card limit used
            - note: Explanation of the fee
    """
    monthly_fee = card_limit * MONTHLY_FEE_RATE
    rate_pct = round(MONTHLY_FEE_RATE * 100, 4)
    return {
        "monthly_fee": round(monthly_fee, 2),
        "rate_percent": rate_pct,
        "card_limit": card_limit,
        "note": (
            f"Monthly fee is charged at {rate_pct}% of card limit per month "
            f"(Rp {card_limit:,.0f} × {rate_pct}% = Rp {monthly_fee:,.0f}). "
            "This is the gross amount before cash rebate deduction."
        ),
    }


@hasanah_card.tool()
def calculate_cash_rebate(
    outstanding: float,
    card_limit: float,
    # payment_timing: Literal["before_due_date", "after_due_date"],
    payment_timing: str,
    # payment_type: Literal["full", "partial"],
    payment_type: str,
    num_days: int = 0,
    transaction_amount: float = 0.0,
) -> dict:
    """
    Calculate the cash rebate for BSI Hasanah Card.

    Cash rebate is an appreciation from the bank that reduces the monthly fee.
    It is calculated as: (Outstanding - Limit) × eq_rate
    or alternatively: transaction_amount × num_days × (rate × 12/365)

    The equivalent rate depends on payment timing and type:
    - Before due date + full payment:    1.75%
    - Before due date + partial payment: 1.40%
    - After due date  + full payment:    1.40%
    - After due date  + partial payment: 1.35%

    Balance-based formula: (Limit - Outstanding) × eq_rate
    - When outstanding = 0 (no transactions): rebate = limit × 1.75% = monthly fee → net fee = 0
    - When outstanding = limit (fully used): rebate = 0 → net fee = monthly fee
    - Cash rebate is capped at monthly fee (cannot exceed it)

    Args:
        outstanding: Total outstanding balance in IDR.
        card_limit: The card limit in IDR.
        payment_timing: "before_due_date" or "after_due_date".
        payment_type: "full" (full payment) or "partial" (partial/minimum payment).
        num_days: Number of days used in the transaction-based formula (optional).
        transaction_amount: Transaction nominal for the day-based formula (optional).

    Returns:
        A dict with:
            - cash_rebate: Calculated cash rebate amount in IDR
            - eq_rate_percent: The equivalent rate used
            - method: Which formula was used
    """
    # Determine eq. rate
    if payment_timing == "before_due_date":
        eq_rate = (
            CASH_REBATE_BEFORE_DUE_FULL
            if payment_type == "full"
            else CASH_REBATE_BEFORE_DUE_PARTIAL
        )
    else:
        eq_rate = (
            CASH_REBATE_AFTER_DUE_FULL
            if payment_type == "full"
            else CASH_REBATE_AFTER_DUE_PARTIAL
        )

    # Primary formula: (Limit - Outstanding) × eq_rate
    # Cash rebate is higher when outstanding is lower (less card usage = more rebate).
    # When outstanding = 0 (no transactions), rebate = limit × eq_rate = monthly_fee → net = 0.
    # When outstanding = limit (full utilization), rebate = 0.
    # Capped at 0 (no negative rebate) if outstanding exceeds limit.
    if card_limit > 0:
        rebate_balance = max(card_limit - outstanding, 0.0) * eq_rate
    else:
        rebate_balance = 0.0

    # Alternative formula: transaction × days × (rate × 12/365)
    rebate_transaction = 0.0
    if transaction_amount > 0 and num_days > 0:
        rebate_transaction = transaction_amount * num_days * (eq_rate * 12 / 365)

    # Use the transaction-based formula if inputs are provided, otherwise balance-based
    if transaction_amount > 0 and num_days > 0:
        cash_rebate = rebate_transaction
        method = "transaction_based: nominal × days × (rate × 12/365)"
    else:
        cash_rebate = rebate_balance
        method = "balance_based: (limit - outstanding) × eq_rate"

    eq_rate_pct = round(eq_rate * 100, 4)
    return {
        "cash_rebate": round(cash_rebate, 2),
        "eq_rate_percent": eq_rate_pct,
        "payment_timing": payment_timing,
        "payment_type": payment_type,
        "method": method,
        "note": (
            f"Cash rebate uses eq. rate {eq_rate_pct}% "
            f"({'before' if payment_timing == 'before_due_date' else 'after'} due date, "
            f"{'full' if payment_type == 'full' else 'partial'} payment). "
            "Cash rebate reduces the monthly fee but cannot exceed the monthly fee."
        ),
    }


@hasanah_card.tool()
def calculate_net_monthly_fee(
    card_limit: float,
    outstanding: float,
    # payment_timing: Literal["before_due_date", "after_due_date"],
    payment_timing: str,
    # payment_type: Literal["full", "partial"],
    payment_type: str,
    num_days: int = 0,
    transaction_amount: float = 0.0,
) -> dict:
    """
    Calculate the net monthly fee (ujrah bersih) for BSI Hasanah Card.

    Formula: Net Monthly Fee = Monthly Fee - Cash Rebate
    The net monthly fee is what the cardholder actually pays as ujrah.
    If there are no transactions, cash rebate equals monthly fee → net = 0.

    Args:
        card_limit: The card limit in IDR.
        outstanding: Total outstanding balance in IDR.
        payment_timing: "before_due_date" or "after_due_date".
        payment_type: "full" (full payment) or "partial" (partial/minimum payment).
        num_days: Number of days for transaction-based rebate formula (optional).
        transaction_amount: Transaction nominal for day-based rebate formula (optional).

    Returns:
        A dict with:
            - monthly_fee: Gross monthly fee
            - cash_rebate: Cash rebate amount
            - net_monthly_fee: Amount actually paid (Monthly Fee - Cash Rebate)
            - savings: How much was saved via cash rebate
    """
    # Monthly fee
    monthly_fee = card_limit * MONTHLY_FEE_RATE

    # Cash rebate
    rebate_result = calculate_cash_rebate(
        outstanding=outstanding,
        card_limit=card_limit,
        payment_timing=payment_timing,
        payment_type=payment_type,
        num_days=num_days,
        transaction_amount=transaction_amount,
    )
    cash_rebate = rebate_result["cash_rebate"]

    # Cash rebate cannot exceed monthly fee
    cash_rebate = min(cash_rebate, monthly_fee)

    net_monthly_fee = monthly_fee - cash_rebate
    net_monthly_fee = max(net_monthly_fee, 0.0)  # cannot be negative

    return {
        "monthly_fee": round(monthly_fee, 2),
        "cash_rebate": round(cash_rebate, 2),
        "net_monthly_fee": round(net_monthly_fee, 2),
        "savings_from_rebate": round(cash_rebate, 2),
        "eq_rate_percent": rebate_result["eq_rate_percent"],
        "note": (
            f"Net Monthly Fee = Monthly Fee (Rp {round(monthly_fee):,}) "
            f"- Cash Rebate (Rp {round(cash_rebate):,}) "
            f"= Rp {round(net_monthly_fee):,}. "
            "No interest is charged. Cash rebate cannot exceed monthly fee."
        ),
    }


@hasanah_card.tool()
def calculate_minimum_payment(total_bill: float, overlimit_amount: float = 0.0) -> dict:
    """
    Calculate the minimum payment for BSI Hasanah Card.

    Minimum payment = max(5% of total bill, Rp 50,000).
    If the cardholder is over the limit, the overlimit amount is added to minimum payment.

    No late payment penalty (ta'widh) or over-limit penalty is charged (unlike conventional cards).

    Args:
        total_bill: Total outstanding bill amount in IDR.
        overlimit_amount: Amount exceeding the card limit (if any), in IDR. Default 0.

    Returns:
        A dict with:
            - minimum_payment: Minimum payment due
            - five_percent_of_bill: 5% of total bill
            - overlimit_amount: Extra amount added if over limit
            - total_minimum_due: Final minimum payment including overlimit
    """
    five_pct = total_bill * MIN_PAYMENT_PERCENT
    base_minimum = max(five_pct, MIN_PAYMENT_FLOOR)
    total_minimum = base_minimum + overlimit_amount

    return {
        "minimum_payment_base": round(base_minimum, 2),
        "five_percent_of_bill": round(five_pct, 2),
        "floor_amount": MIN_PAYMENT_FLOOR,
        "overlimit_amount": round(overlimit_amount, 2),
        "total_minimum_due": round(total_minimum, 2),
        "note": (
            f"Minimum payment = max(5% × Rp {total_bill:,.0f}, Rp {MIN_PAYMENT_FLOOR:,.0f}) "
            f"= Rp {base_minimum:,.0f}. "
            + (
                f"Plus overlimit amount Rp {overlimit_amount:,.0f} = Rp {total_minimum:,.0f}. "
                if overlimit_amount > 0
                else ""
            )
            + "BSI Hasanah Card does NOT charge late payment penalties or over-limit fees."
        ),
    }


@hasanah_card.tool()
def calculate_smart_spending_installment(
    transaction_amount: float,
    tenor_months: int,
) -> dict:
    """
    Calculate the monthly installment for BSI Hasanah Card Smart Spending feature.

    Smart Spending converts any retail transaction into 0% installments
    for up to 12 months. Minimum transaction amount is Rp 500,000.

    Args:
        transaction_amount: Original transaction amount in IDR (minimum Rp 500,000).
        tenor_months: Installment period in months (1 to 12).

    Returns:
        A dict with:
            - monthly_installment: Amount to pay each month
            - total_payment: Total amount paid over the tenor
            - interest_rate_percent: Always 0% (no interest)
            - tenor_months: Number of installment months
            - is_eligible: Whether the transaction meets minimum requirements
    """
    errors = []
    if transaction_amount < SMART_SPENDING_MIN_AMOUNT:
        errors.append(
            f"Transaction amount Rp {transaction_amount:,.0f} is below minimum "
            f"Rp {SMART_SPENDING_MIN_AMOUNT:,.0f} required for Smart Spending."
        )
    if tenor_months < 1 or tenor_months > SMART_SPENDING_MAX_TENOR:
        errors.append(
            f"Tenor {tenor_months} months is invalid. Must be between 1 and {SMART_SPENDING_MAX_TENOR} months."
        )

    is_eligible = len(errors) == 0
    monthly_installment = transaction_amount / tenor_months if is_eligible else 0.0
    total_payment = transaction_amount  # 0% interest, total equals original amount

    return {
        "is_eligible": is_eligible,
        "monthly_installment": round(monthly_installment, 2),
        "total_payment": round(total_payment, 2),
        "interest_rate_percent": SMART_SPENDING_RATE * 100,
        "tenor_months": tenor_months,
        "transaction_amount": transaction_amount,
        "errors": errors,
        "note": (
            f"Smart Spending: Rp {transaction_amount:,.0f} ÷ {tenor_months} months "
            f"= Rp {monthly_installment:,.0f}/month at 0% interest. "
            "Available at any merchant, minimum transaction Rp 500,000, max 12 months."
        )
        if is_eligible
        else "; ".join(errors),
    }


@hasanah_card.tool()
def calculate_cash_advance(
    withdrawal_amount: float,
    card_limit: float,
    num_withdrawals: int = 1,
) -> dict:
    """
    Calculate cash advance (tarik tunai) fees for BSI Hasanah Card.

    Cash advance is available via ATM based on Qard akad (interest-free loan).
    Fee: flat Rp 25,000 per withdrawal, regardless of amount.
    Maximum: 20% of card limit.

    Note: The cash is a Qard (loan) — no interest is charged, only the flat fee.

    Args:
        withdrawal_amount: Amount to withdraw in IDR.
        card_limit: The card limit in IDR.
        num_withdrawals: Number of separate ATM withdrawals. Default 1.

    Returns:
        A dict with:
            - cash_advance_fee: Total fee for all withdrawals
            - fee_per_withdrawal: Fee per single withdrawal (Rp 25,000)
            - max_withdrawal_limit: Maximum allowed cash advance (20% of limit)
            - is_within_limit: Whether withdrawal amount is within the allowed limit
            - total_charge: Total amount charged (withdrawal + fee)
    """
    max_limit = card_limit * CASH_ADVANCE_MAX_PERCENT
    is_within_limit = withdrawal_amount <= max_limit

    total_fee = CASH_ADVANCE_FEE * num_withdrawals
    total_charge = withdrawal_amount + total_fee

    return {
        "withdrawal_amount": withdrawal_amount,
        "fee_per_withdrawal": CASH_ADVANCE_FEE,
        "num_withdrawals": num_withdrawals,
        "cash_advance_fee_total": total_fee,
        "max_withdrawal_limit": max_limit,
        "max_withdrawal_percent": CASH_ADVANCE_MAX_PERCENT * 100,
        "is_within_limit": is_within_limit,
        "total_charge": round(total_charge, 2),
        "note": (
            f"Cash advance fee: Rp {CASH_ADVANCE_FEE:,.0f} flat × {num_withdrawals} withdrawal(s) "
            f"= Rp {total_fee:,.0f}. "
            f"Max allowed: Rp {max_limit:,.0f} ({CASH_ADVANCE_MAX_PERCENT * 100:.0f}% of Rp {card_limit:,.0f} limit). "
            + (
                "Within limit."
                if is_within_limit
                else f"EXCEEDS LIMIT by Rp {withdrawal_amount - max_limit:,.0f}!"
            )
            + " This is a Qard (loan) — no interest, only flat fee applies."
        ),
    }


@hasanah_card.tool()
def calculate_billing_statement_fee(
    # delivery_method: Literal["email", "physical"],
    delivery_method: str,
) -> dict:
    """
    Calculate the billing statement delivery fee for BSI Hasanah Card.

    - Email delivery: Free (Rp 0)
    - Physical/courier delivery: Rp 20,000

    Args:
        delivery_method: "email" (free) or "physical" (Rp 20,000).

    Returns:
        A dict with the billing fee details.
    """
    fee = BILLING_FEE_EMAIL if delivery_method == "email" else BILLING_FEE_PHYSICAL

    return {
        "delivery_method": delivery_method,
        "billing_fee": fee,
        "note": (
            "Email billing is free. Physical billing to home/office address costs Rp 20,000."
            f" Selected method '{delivery_method}': Rp {fee:,.0f}."
        ),
    }


@hasanah_card.tool()
def get_card_fee_info(
    # card_type: Literal["classic", "gold", "platinum"],
    card_type: str,
) -> dict:
    """
    Get fee structure information for each BSI Hasanah Card type.

    BSI Hasanah Card has 3 tiers: Classic, Gold, and Platinum.
    Monthly fee = 1.75% of card limit (same rate for all tiers).
    Annual fee varies by tier (based on Ijarah akad).

    Note: Specific annual fee amounts and limit ranges may be updated by the bank.
    The monthly fee rate of 1.75% is applied to whatever limit is given.

    Args:
        card_type: "classic", "gold", or "platinum"

    Returns:
        A dict with fee information and key rules for the selected card type.
    """
    tier = CARD_TIERS[card_type]

    return {
        **tier,
        "monthly_fee_rate_percent": round(MONTHLY_FEE_RATE * 100, 4),
        "monthly_fee_basis": f"{round(MONTHLY_FEE_RATE * 100, 4)}% of approved card limit",
        "cash_advance_fee": f"Rp {CASH_ADVANCE_FEE:,.0f} flat per withdrawal",
        "cash_advance_limit_percent": round(CASH_ADVANCE_MAX_PERCENT * 100),
        "min_payment_percent": round(MIN_PAYMENT_PERCENT * 100),
        "min_payment_floor": f"Rp {MIN_PAYMENT_FLOOR:,.0f}",
        "late_penalty": "None (no ta'widh/denda keterlambatan)",
        "overlimit_penalty": "None (no denda overlimit)",
        "smart_spending": (
            f"{round(SMART_SPENDING_RATE * 100)}% installment up to {SMART_SPENDING_MAX_TENOR} months "
            f"(min Rp {SMART_SPENDING_MIN_AMOUNT:,.0f})"
        ),
        "cash_rebate_rates": {
            "before_due_date_full_payment": f"{round(CASH_REBATE_BEFORE_DUE_FULL * 100, 4)}%",
            "before_due_date_partial_payment": f"{round(CASH_REBATE_BEFORE_DUE_PARTIAL * 100, 4)}%",
            "after_due_date_full_payment": f"{round(CASH_REBATE_AFTER_DUE_FULL * 100, 4)}%",
            "after_due_date_partial_payment": f"{round(CASH_REBATE_AFTER_DUE_PARTIAL * 100, 4)}%",
        },
        "syariah_basis": SYARIAH_BASIS,
        "note": PRODUCT_NOTE,
    }


@hasanah_card.tool()
def calculate_full_billing_summary(
    card_limit: float,
    outstanding: float,
    # payment_timing: Literal["before_due_date", "after_due_date"],
    payment_timing: str,
    # payment_type: Literal["full", "partial"],
    payment_type: str,
    num_days: int = 0,
    transaction_amount: float = 0.0,
) -> dict:
    """
    Calculate a complete billing summary for BSI Hasanah Card.

    This combines all calculations into one comprehensive summary:
    - Gross monthly fee
    - Cash rebate
    - Net monthly fee (what you actually pay)
    - Minimum payment required

    Args:
        card_limit: The card limit in IDR.
        outstanding: Total outstanding balance in IDR (can include monthly fee).
        payment_timing: "before_due_date" or "after_due_date".
        payment_type: "full" (full payment) or "partial" (partial/minimum payment).
        num_days: Number of days for transaction-based rebate calculation (optional).
        transaction_amount: Transaction amount for day-based rebate formula (optional).

    Returns:
        A comprehensive billing summary dict.
    """
    # Monthly fee
    monthly_fee = card_limit * MONTHLY_FEE_RATE

    # Cash rebate
    rebate_result = calculate_cash_rebate(
        outstanding=outstanding,
        card_limit=card_limit,
        payment_timing=payment_timing,
        payment_type=payment_type,
        num_days=num_days,
        transaction_amount=transaction_amount,
    )
    cash_rebate = min(rebate_result["cash_rebate"], monthly_fee)

    # Net monthly fee
    net_monthly_fee = max(monthly_fee - cash_rebate, 0.0)

    # Total bill = outstanding + net monthly fee (if not already included)
    total_bill = outstanding + net_monthly_fee

    # Minimum payment
    min_payment_result = calculate_minimum_payment(total_bill=total_bill)

    # Overlimit check
    overlimit_amount = max(outstanding - card_limit, 0.0)

    return {
        "card_limit": card_limit,
        "outstanding_balance": outstanding,
        "overlimit_amount": round(overlimit_amount, 2),
        "gross_monthly_fee": round(monthly_fee, 2),
        "cash_rebate": round(cash_rebate, 2),
        "net_monthly_fee": round(net_monthly_fee, 2),
        "total_bill": round(total_bill, 2),
        "minimum_payment_due": min_payment_result["total_minimum_due"],
        "full_payment_amount": round(total_bill, 2),
        "payment_timing": payment_timing,
        "payment_type": payment_type,
        "eq_rate_percent": rebate_result["eq_rate_percent"],
        "late_penalty": 0.0,
        "overlimit_penalty": 0.0,
        "note": (
            "BSI Hasanah Card charges NO late payment penalty and NO over-limit penalty. "
            f"Net Monthly Fee = Gross Monthly Fee (Rp {monthly_fee:,.0f}) "
            f"- Cash Rebate (Rp {cash_rebate:,.0f}) = Rp {net_monthly_fee:,.0f}. "
            f"Minimum payment due: Rp {min_payment_result['total_minimum_due']:,.0f}."
        ),
    }
