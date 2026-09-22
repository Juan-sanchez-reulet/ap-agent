"""Week-1 spike: can we create a PO-linked DRAFT vendor bill in Odoo 19 Community?

Two transports:
  * json2  (default when ODOO_API_KEY is set) — the target for OdooErp in week 3
  * xmlrpc (fallback, deprecated by Odoo but alive until v22) — needs admin/admin

Usage: uv run python -m scripts.odoo_spike [--transport json2|xmlrpc]
"""

import argparse
import os
import xmlrpc.client
from typing import Any, Protocol

BASE_URL = os.environ.get("ODOO_URL", "http://localhost:8069")
DATABASE = os.environ.get("ODOO_DB", "apagent")


class Transport(Protocol):
    def call(self, model: str, method: str, **params: Any) -> Any: ...


class Json2Transport:
    """POST /json/2/<model>/<method> with a bearer API key (Odoo 19+)."""

    def __init__(self, api_key: str) -> None:
        import httpx

        self.client = httpx.Client(
            base_url=BASE_URL,
            headers={
                "Authorization": f"bearer {api_key}",
                "X-Odoo-Database": DATABASE,
                "User-Agent": "ap-agent-spike",
            },
            timeout=60,
        )

    def call(self, model: str, method: str, **params: Any) -> Any:
        response = self.client.post(f"/json/2/{model}/{method}", json=params)
        if response.status_code >= 400:
            raise RuntimeError(f"{model}.{method} -> {response.status_code}: {response.text[:300]}")
        return response.json()


class XmlRpcTransport:
    def __init__(self, user: str = "admin", password: str = "admin") -> None:
        common = xmlrpc.client.ServerProxy(f"{BASE_URL}/xmlrpc/2/common")
        self.uid = common.authenticate(DATABASE, user, password, {})
        self.password = password
        self.models = xmlrpc.client.ServerProxy(f"{BASE_URL}/xmlrpc/2/object")

    def call(self, model: str, method: str, **params: Any) -> Any:
        positional: list[Any] = []
        for key in ("ids", "vals_list", "domain"):
            if key in params:
                positional.append(params.pop(key))
        return self.models.execute_kw(
            DATABASE, self.uid, self.password, model, method, positional, params
        )


def run(t: Transport) -> None:
    spain = t.call("res.country", "search_read", domain=[["code", "=", "ES"]], fields=["id"])[0]
    [partner_id] = t.call(
        "res.partner",
        "create",
        vals_list=[
            {
                "name": "TecnoHardware Ibérica S.L.",
                "vat": "ESB46234563",
                "is_company": True,
                "country_id": spain["id"],
            }
        ],
    )
    print(f"1. vendor {partner_id}")

    [product_id] = t.call(
        "product.product",
        "create",
        vals_list=[
            {
                "name": "Monitor 27 pulgadas QHD",
                "purchase_ok": True,
                "type": "consu",
                "is_storable": True,
                "list_price": 189.0,
            }
        ],
    )
    print(f"2. product {product_id}")

    [po_id] = t.call(
        "purchase.order",
        "create",
        vals_list=[
            {
                "partner_id": partner_id,
                "order_line": [
                    [0, 0, {"product_id": product_id, "product_qty": 2, "price_unit": 189.0}]
                ],
            }
        ],
    )
    t.call("purchase.order", "button_confirm", ids=[po_id])
    print(f"3. purchase order {po_id} confirmed")

    pickings = t.call(
        "stock.picking", "search_read", domain=[["purchase_id", "=", po_id]], fields=["id", "state"]
    )
    print(f"4. receipts {pickings}")
    if pickings:
        moves = t.call(
            "stock.move",
            "search_read",
            domain=[["picking_id", "=", pickings[0]["id"]]],
            fields=["id", "product_uom_qty"],
        )
        for move in moves:
            t.call(
                "stock.move",
                "write",
                ids=[move["id"]],
                vals={"quantity": move["product_uom_qty"], "picked": True},
            )
        outcome = t.call("stock.picking", "button_validate", ids=[pickings[0]["id"]])
        state = t.call("stock.picking", "read", ids=[pickings[0]["id"]], fields=["state"])
        print(f"   validate -> {outcome} state={state}")

    tax = t.call(
        "account.tax",
        "search_read",
        domain=[["type_tax_use", "=", "purchase"], ["amount", "=", 21], ["name", "like", "21% G"]],
        fields=["id", "name"],
        limit=1,
    )[0]
    account = t.call(
        "account.account",
        "search_read",
        domain=[["code", "=like", "629%"]],
        fields=["id", "code", "name"],
        limit=1,
    )[0]
    po_line = t.call(
        "purchase.order.line", "search_read", domain=[["order_id", "=", po_id]], fields=["id"]
    )[0]
    print(f"5. tax={tax['name']} account={account['code']} po_line={po_line['id']}")

    [bill_id] = t.call(
        "account.move",
        "create",
        vals_list=[
            {
                "move_type": "in_invoice",
                "partner_id": partner_id,
                "ref": "TH-2026-5521",
                "invoice_date": "2026-09-12",
                "invoice_line_ids": [
                    [
                        0,
                        0,
                        {
                            "product_id": product_id,
                            "quantity": 2,
                            "price_unit": 189.0,
                            "account_id": account["id"],
                            "tax_ids": [[6, 0, [tax["id"]]]],
                            "purchase_line_id": po_line["id"],
                        },
                    ]
                ],
            }
        ],
    )
    bill = t.call(
        "account.move",
        "read",
        ids=[bill_id],
        fields=["state", "ref", "amount_untaxed", "amount_tax", "amount_total"],
    )
    print(f"6. draft bill {bill}")

    again = t.call(
        "account.move",
        "search_read",
        domain=[
            ["move_type", "=", "in_invoice"],
            ["partner_id", "=", partner_id],
            ["ref", "=", "TH-2026-5521"],
        ],
        fields=["id"],
    )
    print(f"7. idempotency lookup by vendor + ref -> {again}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", choices=["json2", "xmlrpc"], default=None)
    args = parser.parse_args()
    api_key = os.environ.get("ODOO_API_KEY")
    transport = args.transport or ("json2" if api_key else "xmlrpc")
    print(f"transport: {transport}")
    run(Json2Transport(api_key) if transport == "json2" else XmlRpcTransport())


if __name__ == "__main__":
    main()
