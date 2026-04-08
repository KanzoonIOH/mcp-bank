"""
KPR (Kredit Pemilikan Rumah) Conventional Mortgage Calculator MCP Server

Supports a hybrid fixed-then-floating rate structure common in Indonesian
conventional bank mortgages. Uses the annuity (reducing-balance) method:
each month's payment covers accrued interest first, with the remainder
reducing the outstanding principal.

Tool:
    calculate_kpr — full mortgage simulation with year-by-year schedule.
"""

from fastmcp import FastMCP

kpr = FastMCP(name="mcp_kpr")


def _annuity_payment(principal: float, annual_rate_pct: float, n_months: int) -> float:
    """
    Return the fixed monthly payment for an annuity loan.

    Formula:  P × r / (1 − (1 + r)^−n)
    where r = monthly rate = annual_rate / 12.

    Falls back to simple division when rate is 0%.
    """
    if principal <= 0 or n_months <= 0:
        return 0.0
    r = annual_rate_pct / 100 / 12
    if r == 0:
        return principal / n_months
    return principal * r / (1 - (1 + r) ** -n_months)


def _amortize_phase(
    principal: float,
    annual_rate_pct: float,
    n_months: int,
) -> tuple[float, float, float, list[dict]]:
    """
    Simulate month-by-month amortization for one rate phase.

    Returns:
        (total_principal_paid, total_interest_paid, ending_balance, monthly_rows)

    Each row in monthly_rows:
        month, principal_paid, interest_paid, remaining_balance
    """
    payment = _annuity_payment(principal, annual_rate_pct, n_months)
    r = annual_rate_pct / 100 / 12
    balance = principal
    rows: list[dict] = []
    total_principal = 0.0
    total_interest = 0.0

    for m in range(1, n_months + 1):
        interest = balance * r
        principal_paid = payment - interest
        # Guard against floating-point overshoot on final payment
        if principal_paid > balance:
            principal_paid = balance
            payment = principal_paid + interest
        balance -= principal_paid
        if balance < 0:
            balance = 0.0
        total_principal += principal_paid
        total_interest += interest
        rows.append(
            {
                "month": m,
                "principal_paid": round(principal_paid, 2),
                "interest_paid": round(interest, 2),
                "remaining_balance": round(balance, 2),
            }
        )

    return round(total_principal, 2), round(total_interest, 2), round(balance, 2), rows


@kpr.tool()
def calculate_kpr(
    property_price: float,
    down_payment: float,
    loan_term_years: int,
    fixed_rate_percent: float,
    fixed_rate_years: int,
    floating_rate_percent: float,
) -> dict:
    """
    Calculate a comprehensive conventional KPR (mortgage) simulation with a
    fixed-then-floating rate structure, using the annuity (reducing-balance) method.

    Down payment interpretation:
        - If down_payment < 1  → treated as a fraction of property_price
          (e.g. 0.20 means 20% down payment)
        - If down_payment >= 1 → treated as a nominal IDR amount

    The fixed rate applies for the first `fixed_rate_years` years.
    After that, the floating rate applies for the remainder of the loan term.
    Setting fixed_rate_years = 0 means the entire loan uses the floating rate.
    Setting fixed_rate_years >= loan_term_years means the entire loan uses
    the fixed rate.

    All amounts are in IDR (Indonesian Rupiah).

    Args:
        property_price:       Total property price in IDR.
        down_payment:         Down payment as a fraction (e.g. 0.20) or IDR amount.
        loan_term_years:      Total loan tenure in years.
        fixed_rate_percent:   Annual interest rate (%) for the fixed period.
        fixed_rate_years:     Number of years the fixed rate applies.
        floating_rate_percent: Annual interest rate (%) after the fixed period.

    Returns:
        A comprehensive dict containing:
            - loan_summary:      Principal, down payment, term, rates.
            - fixed_phase:       Monthly installment, months, interest paid (fixed period).
            - floating_phase:    Monthly installment, months, interest paid (floating period).
            - totals:            Grand total payment, interest, and principal over full term.
            - schedule:          Year-by-year breakdown of payments and balances.
            - note:              Human-readable narrative of the full mortgage plan.
    """
    # ── 1. Resolve down payment ──────────────────────────────────────────────
    if down_payment < 1:
        dp_amount = property_price * down_payment
        dp_percent = down_payment * 100
    else:
        dp_amount = down_payment
        dp_percent = (
            (down_payment / property_price) * 100 if property_price > 0 else 0.0
        )

    loan_principal = property_price - dp_amount

    # ── 2. Resolve phase durations ───────────────────────────────────────────
    total_months = loan_term_years * 12
    fixed_months = min(fixed_rate_years, loan_term_years) * 12
    floating_months = total_months - fixed_months

    # ── 3. Fixed phase amortization ──────────────────────────────────────────
    fixed_principal_paid = 0.0
    fixed_interest_paid = 0.0
    fixed_monthly_rows: list[dict] = []
    fixed_monthly_payment = 0.0
    balance_after_fixed = loan_principal

    if fixed_months > 0:
        fixed_monthly_payment = _annuity_payment(
            loan_principal, fixed_rate_percent, total_months
        )
        (
            fixed_principal_paid,
            fixed_interest_paid,
            balance_after_fixed,
            fixed_monthly_rows,
        ) = _amortize_phase(
            principal=loan_principal,
            annual_rate_pct=fixed_rate_percent,
            n_months=fixed_months,
        )
        # Re-derive balance after fixed phase from full-term payment schedule
        # so the balance is consistent with the actual fixed payment used.
        # We already used full-term n for the payment, now re-simulate.
        # Override: simulate fixed phase with full-term payment (not fixed-only payment)
        # so balance transition is accurate.
        # Actually: recalculate using the payment from full term at fixed rate,
        # applied only for fixed_months, to get the true remaining balance.
        r_fixed = fixed_rate_percent / 100 / 12
        balance = loan_principal
        fp_paid = 0.0
        fi_paid = 0.0
        fixed_monthly_rows = []
        for m in range(1, fixed_months + 1):
            interest = balance * r_fixed
            principal_paid = fixed_monthly_payment - interest
            if principal_paid > balance:
                principal_paid = balance
            balance -= principal_paid
            if balance < 0:
                balance = 0.0
            fp_paid += principal_paid
            fi_paid += interest
            fixed_monthly_rows.append(
                {
                    "month": m,
                    "principal_paid": round(principal_paid, 2),
                    "interest_paid": round(interest, 2),
                    "remaining_balance": round(balance, 2),
                }
            )
        fixed_principal_paid = round(fp_paid, 2)
        fixed_interest_paid = round(fi_paid, 2)
        balance_after_fixed = round(balance, 2)

    # ── 4. Floating phase amortization ───────────────────────────────────────
    floating_principal_paid = 0.0
    floating_interest_paid = 0.0
    floating_monthly_rows: list[dict] = []
    floating_monthly_payment = 0.0

    if floating_months > 0 and balance_after_fixed > 0:
        floating_monthly_payment = _annuity_payment(
            balance_after_fixed, floating_rate_percent, floating_months
        )
        floating_principal_paid, floating_interest_paid, _, floating_monthly_rows = (
            _amortize_phase(
                principal=balance_after_fixed,
                annual_rate_pct=floating_rate_percent,
                n_months=floating_months,
            )
        )

    # ── 5. Build year-by-year schedule ───────────────────────────────────────
    # Combine all monthly rows with their phase label
    all_monthly: list[dict] = []
    for row in fixed_monthly_rows:
        all_monthly.append(
            {**row, "phase": "fixed", "rate_percent": fixed_rate_percent}
        )
    for i, row in enumerate(floating_monthly_rows):
        all_monthly.append(
            {
                **row,
                "month": fixed_months + i + 1,  # absolute month number
                "phase": "floating",
                "rate_percent": floating_rate_percent,
            }
        )

    yearly_schedule: list[dict] = []
    for year in range(1, loan_term_years + 1):
        start = (year - 1) * 12
        end = year * 12
        year_rows = all_monthly[start:end]
        if not year_rows:
            break
        phase = year_rows[0]["phase"]
        rate = year_rows[0]["rate_percent"]
        monthly_installment = (
            fixed_monthly_payment if phase == "fixed" else floating_monthly_payment
        )
        yr_principal = sum(r["principal_paid"] for r in year_rows)
        yr_interest = sum(r["interest_paid"] for r in year_rows)
        yr_total = yr_principal + yr_interest
        remaining = year_rows[-1]["remaining_balance"]

        yearly_schedule.append(
            {
                "year": year,
                "phase": phase,
                "annual_rate_percent": rate,
                "monthly_installment": round(monthly_installment, 2),
                "total_paid_this_year": round(yr_total, 2),
                "principal_paid_this_year": round(yr_principal, 2),
                "interest_paid_this_year": round(yr_interest, 2),
                "remaining_balance_end_of_year": round(remaining, 2),
            }
        )

    # ── 6. Grand totals ──────────────────────────────────────────────────────
    total_principal_paid = round(fixed_principal_paid + floating_principal_paid, 2)
    total_interest_paid = round(fixed_interest_paid + floating_interest_paid, 2)
    total_payment = round(total_principal_paid + total_interest_paid, 2)

    # ── 7. Build narrative note ──────────────────────────────────────────────
    note_parts = [
        f"KPR Conventional — Property price: Rp {property_price:,.0f}.",
        f"Down payment: Rp {dp_amount:,.0f} ({dp_percent:.1f}%), "
        f"Loan principal: Rp {loan_principal:,.0f}.",
        f"Loan term: {loan_term_years} years ({total_months} months).",
    ]

    if fixed_months > 0 and floating_months > 0:
        note_parts.append(
            f"FIXED phase ({fixed_rate_years} year(s), {fixed_months} months) "
            f"at {fixed_rate_percent}% p.a.: "
            f"monthly installment Rp {fixed_monthly_payment:,.0f}. "
            f"Principal paid: Rp {fixed_principal_paid:,.0f}, "
            f"Interest paid: Rp {fixed_interest_paid:,.0f}. "
            f"Remaining balance after fixed period: Rp {balance_after_fixed:,.0f}."
        )
        note_parts.append(
            f"FLOATING phase ({loan_term_years - fixed_rate_years} year(s), {floating_months} months) "
            f"at {floating_rate_percent}% p.a.: "
            f"monthly installment Rp {floating_monthly_payment:,.0f}. "
            f"Principal paid: Rp {floating_principal_paid:,.0f}, "
            f"Interest paid: Rp {floating_interest_paid:,.0f}."
        )
    elif fixed_months > 0:
        note_parts.append(
            f"Entire loan at FIXED rate {fixed_rate_percent}% p.a.: "
            f"monthly installment Rp {fixed_monthly_payment:,.0f}."
        )
    else:
        note_parts.append(
            f"Entire loan at FLOATING rate {floating_rate_percent}% p.a.: "
            f"monthly installment Rp {floating_monthly_payment:,.0f}."
        )

    note_parts.append(
        f"TOTAL over {loan_term_years} years: "
        f"payment Rp {total_payment:,.0f} "
        f"(principal Rp {total_principal_paid:,.0f} + "
        f"interest Rp {total_interest_paid:,.0f})."
    )

    # ── 8. Assemble response ─────────────────────────────────────────────────
    return {
        "loan_summary": {
            "property_price": round(property_price, 2),
            "down_payment_amount": round(dp_amount, 2),
            "down_payment_percent": round(dp_percent, 2),
            "loan_principal": round(loan_principal, 2),
            "loan_term_years": loan_term_years,
            "total_months": total_months,
            "fixed_rate_percent": fixed_rate_percent,
            "fixed_rate_years": fixed_rate_years,
            "fixed_months": fixed_months,
            "floating_rate_percent": floating_rate_percent,
            "floating_months": floating_months,
        },
        "fixed_phase": {
            "monthly_installment": round(fixed_monthly_payment, 2),
            "total_months": fixed_months,
            "total_principal_paid": fixed_principal_paid,
            "total_interest_paid": fixed_interest_paid,
            "total_paid": round(fixed_principal_paid + fixed_interest_paid, 2),
            "balance_at_end": balance_after_fixed,
        },
        "floating_phase": {
            "monthly_installment": round(floating_monthly_payment, 2),
            "total_months": floating_months,
            "total_principal_paid": floating_principal_paid,
            "total_interest_paid": floating_interest_paid,
            "total_paid": round(floating_principal_paid + floating_interest_paid, 2),
        },
        "totals": {
            "total_payment": total_payment,
            "total_principal_paid": total_principal_paid,
            "total_interest_paid": total_interest_paid,
            "total_interest_to_principal_ratio": (
                round(total_interest_paid / loan_principal, 4)
                if loan_principal > 0
                else 0.0
            ),
        },
        "schedule": yearly_schedule,
        "note": " ".join(note_parts),
    }
