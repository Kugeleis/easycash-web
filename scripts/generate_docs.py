#!/usr/bin/env python3
"""Generate docs/format.schema.json and docs/FORMAT.md from Pydantic models."""

import json

from easycash_web.models import (
    BookFile,
)


def main():
    # Generate schema
    schema = BookFile.model_json_schema()
    with open("docs/format.schema.json", "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
    print("Generated docs/format.schema.json")

    # Generate FORMAT.md summary
    lines = []
    lines.append("# FORMAT.md — EasyCash&Tax JSON format")
    lines.append("")
    lines.append("## Top-level structure")
    lines.append('- `format` (str): "easycash-web"')
    lines.append("- `format_version` (int): 1 for v1")
    lines.append("- `revision` (int): incremented on every save")
    lines.append("- `meta` (dict): client name, business type, timestamps")
    lines.append("- `settings` (dict): user-configurable settings")
    lines.append("- `accounts` (list[Account]): account definitions")
    lines.append("- `tax_rates` (list[TaxRate]): VAT rates with validity dates")
    lines.append("- `bookings` (list[Booking]): all booking lines")
    lines.append("- `recurring` (list[RecurringBooking]): recurring booking templates")
    lines.append("- `clients` (list[Client]): client hierarchy")
    lines.append("")
    lines.append("## Account model")
    lines.append("- `id` (str): uuid7")
    lines.append("- `name` (str): account name")
    lines.append("- `type` (AccountType): INCOME or EXPENSE")
    lines.append('- `currency` (str): "EUR"')
    lines.append("- `client_id` (str): owning client id")
    lines.append("- `business_id` (str): owning business id")
    lines.append("")
    lines.append("## Booking model")
    lines.append("- `id` (str): uuid7")
    lines.append("- `booking_number` (str): user-visible")
    lines.append("- `receipt_number` (str): user-visible")
    lines.append("- `date` (date): Buchungsdatum")
    lines.append("- `description` (str): max 256 chars")
    lines.append("- `account_id` (str): owning account")
    lines.append("- `type` (BookingType): INCOME or EXPENSE")
    lines.append("- `gross_cents` (int): integer cents")
    lines.append("- `vat_rate_percent` (int): 19, 7, 0")
    lines.append("- `af_a_mode` (AfAMode): annual / half_year / month_precise / per_settings")
    lines.append("- `af_a_method` (DepreciationMethod): linear / degressive")
    lines.append("- `af_a_jahre` (int): depreciation years")
    lines.append("- `af_a_satz_promille` (int): rate percent*1000")
    lines.append("- `af_a_restwert_cents` (int): residual value in cents")
    lines.append("")
    lines.append("## TaxRate model")
    lines.append("- `id` (str): uuid7")
    lines.append("- `code` (str): country code")
    lines.append("- `name` (str): human label")
    lines.append("- `promille` (int): percent*1000")
    lines.append("- `valid_from` (date): validity start")
    lines.append("- `valid_to` (date|None): validity end")
    lines.append("")
    lines.append("## JSON file layout (per client)")
    lines.append("- One JSON file per client in DATA_DIR")
    lines.append("- Filename: `<client_name>.json`")
    lines.append("- UTF-8, indent=2, deterministic key order")
    lines.append("- Revision incremented on every save")
    lines.append("- Migration chain from older format_version")
    lines.append("")
    with open("docs/FORMAT.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("Generated docs/FORMAT.md")


if __name__ == "__main__":
    main()
