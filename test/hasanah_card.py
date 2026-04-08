import asyncio

from fastmcp import Client

client = Client("http://localhost:8000/mcp")

# ── n8n metadata injected by the AI Agent node on every call ─────────────────
N8N_META = {
    "sessionId": "38d516d11aff472d8590654b072a1c99",
    "action": "sendMessage",
    "chatInput": "calculate hasanah card fees",
    "toolCallId": "chatcmpl-tool-3a962d8ff2b542c798b0d5c677d1455d",
}


def n8n_args(**kwargs) -> dict:
    """Merge real tool args with the extra n8n metadata fields."""
    return {**N8N_META, "tool": kwargs.get("_tool", ""), **kwargs}


# ── helpers ───────────────────────────────────────────────────────────────────


def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


def show(label: str, result) -> None:
    print(f"\n[{label}]")
    if isinstance(result, list):
        for item in result:
            print(" ", item)
    else:
        print(" ", result)


# ── test cases ────────────────────────────────────────────────────────────────


async def test():
    """
    Simulate what n8n's AI Agent node sends for every BSI Hasanah Card tool.
    Each call includes the real tool arguments PLUS the extra metadata fields
    that n8n injects (sessionId, action, chatInput, toolCallId).
    The StripExtraFieldsMiddleware silently drops the metadata before FastMCP
    validates the arguments, so every call should succeed cleanly.
    """
    async with client:
        # ── 1. calculate_monthly_fee ──────────────────────────────────────────
        section("1. calculate_monthly_fee — Gold card, Rp 10 juta limit")
        result = await client.call_tool(
            "calculate_monthly_fee",
            n8n_args(
                _tool="calculate_monthly_fee",
                card_limit=10_000_000,
            ),
        )
        show("limit=10_000_000 → monthly_fee should be Rp 175,000", result)

        # ── 2. calculate_cash_rebate (balance-based) ──────────────────────────
        section("2. calculate_cash_rebate — balance-based, before due, full payment")
        result = await client.call_tool(
            "calculate_cash_rebate",
            n8n_args(
                _tool="calculate_cash_rebate",
                outstanding=8_000_000,
                card_limit=10_000_000,
                payment_timing="before_due_date",
                payment_type="full",
            ),
        )
        show("outstanding=8M, limit=10M → rebate=(10M-8M)×1.75%=Rp 35,000", result)

        # # ── 3. calculate_cash_rebate (transaction-based) ──────────────────────
        # section("3. calculate_cash_rebate — transaction-based formula")
        # result = await client.call_tool(
        #     "calculate_cash_rebate",
        #     n8n_args(
        #         _tool="calculate_cash_rebate",
        #         outstanding=5_000_000,
        #         card_limit=10_000_000,
        #         payment_timing="before_due_date",
        #         payment_type="partial",
        #         transaction_amount=5_000_000,
        #         num_days=30,
        #     ),
        # )
        # show("transaction-based: 5M × 30 days × (1.40%×12/365)", result)

        # # ── 4. calculate_cash_rebate — after due date, partial ────────────────
        # section(
        #     "4. calculate_cash_rebate — after due date, partial payment (lowest rate)"
        # )
        # result = await client.call_tool(
        #     "calculate_cash_rebate",
        #     n8n_args(
        #         _tool="calculate_cash_rebate",
        #         outstanding=5_000_000,
        #         card_limit=10_000_000,
        #         payment_timing="after_due_date",
        #         payment_type="partial",
        #     ),
        # )
        # show("after due+partial → eq_rate should be 1.35%, rebate=Rp 67,500", result)

        # # ── 5. calculate_net_monthly_fee — no transactions ────────────────────
        # section("5. calculate_net_monthly_fee — no transactions (FAQ: Pak Adi example)")
        # result = await client.call_tool(
        #     "calculate_net_monthly_fee",
        #     n8n_args(
        #         _tool="calculate_net_monthly_fee",
        #         card_limit=10_000_000,
        #         outstanding=0,
        #         payment_timing="before_due_date",
        #         payment_type="full",
        #     ),
        # )
        # show(
        #     "outstanding=0 → rebate=monthly_fee → net_monthly_fee should be Rp 0",
        #     result,
        # )

        # # ── 6. calculate_net_monthly_fee — partial usage ──────────────────────
        # section("6. calculate_net_monthly_fee — partial card usage, partial payment")
        # result = await client.call_tool(
        #     "calculate_net_monthly_fee",
        #     n8n_args(
        #         _tool="calculate_net_monthly_fee",
        #         card_limit=10_000_000,
        #         outstanding=8_000_000,
        #         payment_timing="before_due_date",
        #         payment_type="partial",
        #     ),
        # )
        # show(
        #     "8M outstanding, partial before due → rebate=(10M-8M)×1.40%=Rp 28,000",
        #     result,
        # )

        # # ── 7. calculate_minimum_payment — 5% applies ─────────────────────────
        # section("7. calculate_minimum_payment — 5% of Rp 2,000,000")
        # result = await client.call_tool(
        #     "calculate_minimum_payment",
        #     n8n_args(
        #         _tool="calculate_minimum_payment",
        #         total_bill=2_000_000,
        #     ),
        # )
        # show("5% × Rp 2,000,000 = Rp 100,000 (above floor)", result)

        # # ── 8. calculate_minimum_payment — floor applies ──────────────────────
        # section("8. calculate_minimum_payment — floor Rp 50,000 applies")
        # result = await client.call_tool(
        #     "calculate_minimum_payment",
        #     n8n_args(
        #         _tool="calculate_minimum_payment",
        #         total_bill=500_000,
        #     ),
        # )
        # show("5% × Rp 500,000 = Rp 25,000 → floor Rp 50,000 applies", result)

        # # ── 9. calculate_minimum_payment — with overlimit ─────────────────────
        # section("9. calculate_minimum_payment — overlimit amount added")
        # result = await client.call_tool(
        #     "calculate_minimum_payment",
        #     n8n_args(
        #         _tool="calculate_minimum_payment",
        #         total_bill=3_000_000,
        #         overlimit_amount=500_000,
        #     ),
        # )
        # show("5%×3M=150,000 + overlimit 500,000 = total min Rp 650,000", result)

        # # ── 10. calculate_smart_spending_installment — eligible ───────────────
        # section("10. calculate_smart_spending_installment — Rp 3,000,000 / 12 months")
        # result = await client.call_tool(
        #     "calculate_smart_spending_installment",
        #     n8n_args(
        #         _tool="calculate_smart_spending_installment",
        #         transaction_amount=3_000_000,
        #         tenor_months=12,
        #     ),
        # )
        # show("3M ÷ 12 = Rp 250,000/month at 0%", result)

        # # ── 11. calculate_smart_spending_installment — short tenor ────────────
        # section("11. calculate_smart_spending_installment — Rp 1,500,000 / 3 months")
        # result = await client.call_tool(
        #     "calculate_smart_spending_installment",
        #     n8n_args(
        #         _tool="calculate_smart_spending_installment",
        #         transaction_amount=1_500_000,
        #         tenor_months=3,
        #     ),
        # )
        # show("1.5M ÷ 3 = Rp 500,000/month at 0%", result)

        # # ── 12. calculate_smart_spending_installment — below minimum ──────────
        # section("12. calculate_smart_spending_installment — below Rp 500,000 minimum")
        # result = await client.call_tool(
        #     "calculate_smart_spending_installment",
        #     n8n_args(
        #         _tool="calculate_smart_spending_installment",
        #         transaction_amount=300_000,
        #         tenor_months=6,
        #     ),
        # )
        # show("Rp 300,000 < minimum → is_eligible=False", result)

        # # ── 13. calculate_cash_advance — within limit ─────────────────────────
        # section("13. calculate_cash_advance — Rp 500,000 from Rp 5,000,000 limit")
        # result = await client.call_tool(
        #     "calculate_cash_advance",
        #     n8n_args(
        #         _tool="calculate_cash_advance",
        #         withdrawal_amount=500_000,
        #         card_limit=5_000_000,
        #     ),
        # )
        # show("max=20%×5M=Rp 1M, fee=Rp 25,000 flat, within_limit=True", result)

        # # ── 14. calculate_cash_advance — multiple withdrawals ─────────────────
        # section("14. calculate_cash_advance — 2 withdrawals")
        # result = await client.call_tool(
        #     "calculate_cash_advance",
        #     n8n_args(
        #         _tool="calculate_cash_advance",
        #         withdrawal_amount=800_000,
        #         card_limit=5_000_000,
        #         num_withdrawals=2,
        #     ),
        # )
        # show("2 withdrawals × Rp 25,000 fee = Rp 50,000 total fee", result)

        # # ── 15. calculate_cash_advance — exceeds limit ────────────────────────
        # section("15. calculate_cash_advance — amount exceeds 20% limit")
        # result = await client.call_tool(
        #     "calculate_cash_advance",
        #     n8n_args(
        #         _tool="calculate_cash_advance",
        #         withdrawal_amount=2_000_000,
        #         card_limit=5_000_000,
        #     ),
        # )
        # show("2M > max 1M → is_within_limit=False", result)

        # # ── 16. calculate_billing_statement_fee — email ───────────────────────
        # section("16. calculate_billing_statement_fee — email (free)")
        # result = await client.call_tool(
        #     "calculate_billing_statement_fee",
        #     n8n_args(
        #         _tool="calculate_billing_statement_fee",
        #         delivery_method="email",
        #     ),
        # )
        # show("email delivery → Rp 0", result)

        # # ── 17. calculate_billing_statement_fee — physical ────────────────────
        # section("17. calculate_billing_statement_fee — physical courier")
        # result = await client.call_tool(
        #     "calculate_billing_statement_fee",
        #     n8n_args(
        #         _tool="calculate_billing_statement_fee",
        #         delivery_method="physical",
        #     ),
        # )
        # show("physical delivery → Rp 20,000", result)

        # # ── 18. get_card_fee_info — classic ───────────────────────────────────
        # section("18. get_card_fee_info — Classic")
        # result = await client.call_tool(
        #     "get_card_fee_info",
        #     n8n_args(
        #         _tool="get_card_fee_info",
        #         card_type="classic",
        #     ),
        # )
        # show("Classic tier fee structure", result)

        # # ── 19. get_card_fee_info — gold ──────────────────────────────────────
        # section("19. get_card_fee_info — Gold")
        # result = await client.call_tool(
        #     "get_card_fee_info",
        #     n8n_args(
        #         _tool="get_card_fee_info",
        #         card_type="gold",
        #     ),
        # )
        # show("Gold tier fee structure", result)

        # # ── 20. get_card_fee_info — platinum ──────────────────────────────────
        # section("20. get_card_fee_info — Platinum")
        # result = await client.call_tool(
        #     "get_card_fee_info",
        #     n8n_args(
        #         _tool="get_card_fee_info",
        #         card_type="platinum",
        #     ),
        # )
        # show("Platinum tier fee structure + lounge benefit", result)

        # # ── 21. calculate_full_billing_summary — before due, full ─────────────
        # section("21. calculate_full_billing_summary — before due date, full payment")
        # result = await client.call_tool(
        #     "calculate_full_billing_summary",
        #     n8n_args(
        #         _tool="calculate_full_billing_summary",
        #         card_limit=10_000_000,
        #         outstanding=8_000_000,
        #         payment_timing="before_due_date",
        #         payment_type="full",
        #     ),
        # )
        # show("All-in-one: gross=175K, rebate=35K, net=140K, min_payment=407K", result)

        # # ── 22. calculate_full_billing_summary — after due, partial ───────────
        # section("22. calculate_full_billing_summary — after due date, partial payment")
        # result = await client.call_tool(
        #     "calculate_full_billing_summary",
        #     n8n_args(
        #         _tool="calculate_full_billing_summary",
        #         card_limit=10_000_000,
        #         outstanding=8_000_000,
        #         payment_timing="after_due_date",
        #         payment_type="partial",
        #     ),
        # )
        # show("After due+partial → eq_rate=1.35%, no late penalty", result)

        # # ── 23. calculate_full_billing_summary — no transactions ──────────────
        # section("23. calculate_full_billing_summary — no transactions this month")
        # result = await client.call_tool(
        #     "calculate_full_billing_summary",
        #     n8n_args(
        #         _tool="calculate_full_billing_summary",
        #         card_limit=10_000_000,
        #         outstanding=0,
        #         payment_timing="before_due_date",
        #         payment_type="full",
        #     ),
        # )
        # show("outstanding=0 → net_monthly_fee=0, total_bill=0", result)


asyncio.run(test())
