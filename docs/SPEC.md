# SPEC.md — EasyCash&Tax Web Reimplementation

## 1. Feature Inventory

Derived from the EasyCash source tree (<https://github.com/Thomas-Mielke-Software/EasyCash>) and homepage/docs (<https://www.easyct.de>).

| Area | Source Files / Folders | Description |
| ------ | ------------------------ | ------------- |
| **Client / Business Management** | `MandantName.cpp/h`, `IconAuswahl*.cpp/h`, `UnternehmensartDlg.cpp/h`, `IconAuswahlMandant/Betrieb/Bestandskonto.cpp/h` | Client (Mandant) name, business type (Freiberufler/Gewerbe), icons for clients/businesses/asset accounts. |
| **Opening Balances** | `AnfangssaldoDlg.cpp/h` | Opening balances for accounts at year start. |
| **VAT Prepayments & Periods** | `UstVorauszahlungenDlg.cpp/h`, `VoranmeldungszeitraumDroplist.cpp/h`, `voranmeldezeitraumdlg.cpp/h` | VAT prepayments, period selection (monthly/quarterly/annual). |
| **Tax Forms (EÜR, USt, UVA)** | `EUeR/`, `UST/`, `UVA/` folders with `.ecf` XML form definitions per year; `NeuesFormular.cpp/h`, `Formularabschnitt.cpp/h`, `Formularfeld.cpp/h`, `EasyCashFormularDuplizierer/` | Form definitions (XML), sections, fields, duplication tool. EÜR = German income surplus (§4(3) EStG). USt = VAT declaration. UVA = Austrian variant. |
| **Fast Entry / Booking Grid** | `Navigation.cpp/h`, `QuickList.cpp/h`, `QuickEdit.cpp/h`, `MyListView.cpp/h` | Tree navigation, tabular booking grid with inline editing, keyboard nav, frozen headers. |
| **Calculator in Fields** | `VCalcParser.cpp/h`, `VCalcParserException.cpp/h`, `VCalcParserTypes.h`, `RechnDlg.cpp/h` | Expression parser for amounts (e.g., "100+20*1.19"). |
| **Reports / Output** | `OutputWnd.cpp/h`, `druckauswahldlg.cpp/h` | Report generation, print preview. |
| **Plugin System** | `PluginManager.cpp/h`, `ECTIFace/`, `ECTReg/`, `ECTUpdater/` | DLL-based plugin interface (Elster export, CSV import, etc.). |
| **Settings / Backup** | `Datensicherungsoptionen.cpp/h`, `Startoptionen.cpp/h`, `einstellungen*.cpp/h` | Backup intervals, startup options, multi-tab settings dialogs. |
| **Year Change** | `buchungsjahrwaehlen.cpp/h`, `ECTIFace/buchungsjahrwaehlen.cpp/h`, `ECTIFace/konvertierung.cpp/h` | Year-end rollover, create new year file, convert old formats. |
| **VAT Reconciliation** | `UStAbgleich.cpp/h`, `UStAbgleichDlg.cpp/h` | Map VAT pre-registration fields to annual VAT declaration fields (`uvafeld` attribute). |
| **Depreciation (AfA)** | `AfAGenauigkeit.cpp/h`, `ECTIFace/easycashdoc.h` (defines modes) | AfA modes: 0=annual, 1=half-year, 2=month-precise, 3=per settings. Linear & degressive. |
| **Currency** | `ECTIFace/ectiface.h`, `ECTIFace/easycashdoc.cpp` | Hardcoded rates (DEM, ATS, etc.), conversion to EUR. |

**UVA (Austrian) Scope Decision**: UVA folder contains Austrian forms (AT-2005..AT-2026). The original supports Austria; v1 **excludes UVA** to focus on German EÜR + USt. Mark as OPEN QUESTION whether to add later.

---

## 2. Daily Workflow

1. **Start / Client Selection**
   - User opens app → sees client list (Mandanten). Select or create a client.
   - Each client has one or more "Betriebe" (businesses). Switch via toolbar/dropdown.

2. **Year Selection**
   - File → Open Year → dialog lists `*.eca` files in data dir for that client/year.
   - Or create new year (Jahreswechsel) → copies opening balances, increments year.

3. **Main Window Layout**
   - **Left**: Navigation tree (Income/Expense accounts, VAT, Reports, Forms).
   - **Center**: Booking grid (Tabulator-like) showing bookings for selected account/period.
   - **Right/Bottom**: Calculator, quick-entry form, status.

4. **Enter Bookings (Fast Entry)**
   - Select account in navigation → grid shows bookings.
   - Press `Ins` / click "Neu" → inline row appears.
   - Fields: Date, Description, Account (auto from navigation), Gross amount, VAT rate (dropdown), Receipt number, AfA fields if asset.
   - Amount field accepts expressions (VCalcParser): `100+50*1.19`.
   - `Enter` saves row, moves to next.

5. **Edit / Find**
   - Double-click cell → inline edit (QuickEdit).
   - Filter by month, account, text search.
   - Recurring bookings (Dauerbuchungen): define once, auto-generate per interval.

6. **VAT Prepayments (USt-Voranmeldung)**
   - Navigation → "Umsatzsteuer-Voranmeldung".
   - Select period (month/quarter) via dropdown.
   - Review calculated fields, adjust prepayments (`UstVorauszahlungenDlg`).
   - Export via Elster plugin (out of scope v1; form fill only).

7. **Reports & Tax Forms**
   - Navigation → "Formulare" → EÜR, USt-Erklärung.
   - Form fills from account→field mappings (Einstellungen → EÜR-Konten).
   - Preview, print, or export XML for Elster.

8. **Year-End / RollOver**
   - File → Jahreswechsel → creates new `.eca` for next year, carries forward balances, resets counters.

---

## 3. Business Rules

| Rule | Source | Detail |
| ------ | -------- | -------- |
| **Money representation** | `ECTIFace/easycashdoc.h:52` (`CBetrag::Betrag` in cents) | Integer cents internally. API/JSON: decimal string with 2 places (e.g., `"119.00"`). |
| **VAT rate storage** | `CBetrag::MWSt` in **promille × 1000** (19% → 19000) | Stored per booking. Configurable per account & period. |
| **Standard VAT rates (DE)** | Web (BMF), `todo.txt` v1.10 "MWSt-Sätze frei konfigurierbar" | 19% (Regel), 7% (ermäßigt). **Validity**: 19% since 2007-01-01; 7% unchanged. **OPEN QUESTION**: historical rates before 2007 (16%). |
| **VAT rate validity dates** | Not in code; per German law | Rates change by law. Must be date-bound in new format. **OPEN QUESTION**: exact change dates for 16%→19%, any others. |
| **Kleinunternehmer (§19 UStG)** | `todo.txt` v2.30 "MWSt-Feld optional per Checkbox"; BMF 2026 | Threshold: prev year ≤ 25,000 € net, current year ≤ 100,000 €. No VAT charged, no input tax deduction. No USt-Voranmeldung required (from 2024). **Marked per client/business in settings**. |
| **EÜR Line Mapping (Anlage EÜR)** | `EUeR/2024/EUeR-d-2024.ecf` XML fields; BMF 2026 PDF | Lines 12–23 (Einnahmen), 24–70 (Ausgaben), 71– (AfA, Zinsen, etc.). Kleinunternehmer use lines 12+13 (brutto). Normal: lines 15–17 (split by VAT rate). **Full mapping table in FORMAT.md**. |
| **AfA (Depreciation) Modes** | `ECTIFace/easycashdoc.h:88-92` `#define GANZJAHRES_AFA 0` etc. | 0=annual (full year), 1=half-year (Halbjahresregel), 2=month-precise, 3=per settings. Linear & degressive (`AbschreibungDegressiv`, `AbschreibungSatz`). |
| **AfA Calculation** | `CBuchung::GetBuchungsjahrNetto()` | Net amount for current year depends on `AbschreibungGenauigkeit`. Half-year: 50% in first year regardless of month. Month-precise: pro-rata. |
| **VAT Prepayments Reconciliation** | `UStAbgleich.h` `uvafeld` attribute | Annual VAT declaration fields reference pre-registration field IDs. Multiple declaration fields can map to one pre-reg field. |
| **Booking Number Sequences** | `CEasyCashDoc` counters: `nLaufendeBuchungsnummerFuerEinnahmen/Ausgaben/Bank/Kasse` | Separate sequences per type. User-visible. |
| **Form Field Mapping** | `CEasyCashDoc::m_csEinnahmenFeldzuweisungen` etc. | Account name → form field ID per form (EÜR, USt). Stored in INI/Extension "ECT". |

**OPEN QUESTIONS** (marked 🔴):

- Exact VAT rate history: use 19% as default. Allow global setting and setting per entry.
- Austrian UVA out of scope
- Elster XML export format (Elster plugin is separate GPL repo) - prepare adapter
- AfA: GWG (Geringwertige Wirtschaftsgüter) threshold rules: set €800? as default and allow config of different value
- `Anfangssaldo` (opening balances) are stored — per lump sum
- Multi-currency handling beyond hardcoded Euro conversion rates - out of scope
- Plugin API surface needed for v1 (or defer entirely) - yes prepare for it, implement later

---

## 4. Original Data File Organization

| Aspect | Finding |
| -------- | --------- |
| **File per** | **One `.eca` file per client (Mandant) per year per business (Betrieb)**. Filename pattern: `<Mandant>_<Betrieb>_<Jahr>.eca` (verified via `CBuchungsjahrWaehlen::OnInitDialog` listing `*.eca` in data dir). |
| **Format** | MFC `CArchive` binary serialization of `CEasyCashDoc` (VERSION 13). Not human-readable. |
| **Form Definitions** | `.ecf` XML files in `EUeR/YYYY/`, `UST/AT-YYYY/`, `UST/D-YYYY/`, `UVA/...` — loaded at runtime, not stored in `.eca`. |
| **Settings** | `easyct.ini` in program dir (Windows), per-mandant sections. Plugin data in `CEasyCashDoc::Erweiterung` string. |
| **Backup** | Automatic backup copies (`.bak`) + recovery file on crash. |

**New Format Decision (per idea.md)**: **One JSON file per client (Mandant), containing all years & businesses**. This differs from original (per-year files) but matches "single file per client" requirement. Years & businesses are nested objects.

---

## 5. Proposed v1 Scope vs. Later

| Feature | v1 | Later |
| --------- | ----- | ------- |
| Client / Business / Account CRUD | ✅ | |
| Booking entry (income/expense) with inline grid | ✅ | |
| VAT rate per booking, configurable rates with validity dates | ✅ | |
| Kleinunternehmer mode (checkbox, hides VAT fields) | ✅ | |
| EÜR form fill (Anlage EÜR 2024/2025/2026) | ✅ | |
| USt-Voranmeldung form fill (monthly/quarterly) | ✅ | |
| VAT prepayments (UstVorauszahlungen) | ✅ | |
| AfA: linear, degressive, 4 accuracy modes | ✅ | |
| Year rollover (Jahreswechsel) | ✅ | |
| Opening balances (Anfangssaldo) | ✅ | |
| Recurring bookings (Dauerbuchungen) | ✅ | |
| Calculator in amount fields (VCalcParser) | ✅ | |
| Reports: EÜR, GuV, SuSa, Journal | ✅ | |
| JSON import/export (download/upload) | ✅ | |
| Schema endpoint `/api/v1/schema` | ✅ | |
| Multi-user / Auth | ❌ | v2 |
| Elster XML export / submission | ❌ | v2 (separate plugin) |
| Plugin system (DLL/JS) | ❌ | v2 |
| Austrian UVA forms | ❌ | v2 |
| Multi-currency (live rates) | ❌ | v2 |
| Attachments / receipts scan | ❌ | v2 |
| Mobile-responsive UI | ❌ | v2 |

---

## Open Questions for Review

see anserws above

1. **Form versioning**: EÜR 2024/2025/2026 differ slightly. Load all `.ecf` from `EUeR/` at runtime? - yes
2. **Testing**: Any existing test data (`.eca` samples) to validate parser? - will be provided later
3. **UI language**: German only v1, i18n structure ready? - yes
4. **Docker base image**: `ghcr.io/astral-sh/uv:python3.15`?
