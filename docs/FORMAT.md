# FORMAT.md — EasyCash&Tax JSON format

## Top-level structure
- `format` (str): "easycash-web"
- `format_version` (int): 1 for v1
- `revision` (int): incremented on every save
- `meta` (dict): client name, business type, timestamps
- `settings` (dict): user-configurable settings
- `accounts` (list[Account]): account definitions
- `tax_rates` (list[TaxRate]): VAT rates with validity dates
- `bookings` (list[Booking]): all booking lines
- `recurring` (list[RecurringBooking]): recurring booking templates
- `clients` (list[Client]): client hierarchy

## Account model
- `id` (str): uuid7
- `name` (str): account name
- `type` (AccountType): INCOME or EXPENSE
- `currency` (str): "EUR"
- `client_id` (str): owning client id
- `business_id` (str): owning business id

## Booking model
- `id` (str): uuid7
- `booking_number` (str): user-visible
- `receipt_number` (str): user-visible
- `date` (date): Buchungsdatum
- `description` (str): max 256 chars
- `account_id` (str): owning account
- `type` (BookingType): INCOME or EXPENSE
- `gross_cents` (int): integer cents
- `vat_rate_percent` (int): 19, 7, 0
- `af_a_mode` (AfAMode): annual / half_year / month_precise / per_settings
- `af_a_method` (DepreciationMethod): linear / degressive
- `af_a_jahre` (int): depreciation years
- `af_a_satz_promille` (int): rate percent*1000
- `af_a_restwert_cents` (int): residual value in cents

## TaxRate model
- `id` (str): uuid7
- `code` (str): country code
- `name` (str): human label
- `promille` (int): percent*1000
- `valid_from` (date): validity start
- `valid_to` (date|None): validity end

## JSON file layout (per client)
- One JSON file per client in DATA_DIR
- Filename: `<client_name>.json`
- UTF-8, indent=2, deterministic key order
- Revision incremented on every save
- Migration chain from older format_version
