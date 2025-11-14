# Medical Billing Domain Knowledge

## CPT Code 80307 - Presumptive Drug Screening

**Definition:** Drug test(s), presumptive, any number of drug classes, any number of devices or procedures

**Key Characteristics:**
- **Type:** Presumptive (not confirmatory)
- **Billing Unit:** 1 per patient per date of service
- **Applies to:** Urine drug testing with multiple analytes
- **Coverage:** All drug classes tested on that date (not per drug)

**Important:**
- One 80307 per patient per service date
- Regardless of number of drugs tested
- Presumptive uses immunoassay (screening)
- Confirmatory uses chromatography/mass spec (different codes: 80320-80377)

## Date Format Standards

### US Medical Billing Date Format
**Standard:** MM/DD/YYYY
- Month: 2 digits with leading zero (01-12)
- Day: 2 digits with leading zero (01-31)
- Year: 4 digits (YYYY)

**Examples:**
- January 5, 2025 → 01/05/2025
- December 31, 2024 → 12/31/2024

**Why This Format:**
- US medical billing industry standard
- Required by most medical billing software
- Different from ISO format (YYYY-MM-DD)
- Different from European format (DD/MM/YYYY)

### Critical Date Fields
1. **Date of Birth:** Patient demographic identifier
2. **Date of Service (DOS):** When specimen was collected (billable date)
3. **Test Completed Date:** When lab analysis finished (tracking only)

## Billing File Requirements

### Critical Fields
1. **Patient Demographics:**
   - Last Name (required)
   - First Name (required)
   - Medical Record Number / MRN (required)
   - Date of Birth (required)

2. **Service Information:**
   - Date of Service / DOS (required) - Collection date
   - CPT Code (required) - 80307
   - Units (required) - Always "1"

3. **Provider Information:**
   - Ordering Provider (often required)
   - May use initials (e.g., "TP", "JC")

## Medical Biller's Needs

- **Clean Data:** No "nan", "null", or invalid values
- **Standard Formatting:** Consistent date formats
- **Complete Records:** All required fields present
- **Easy Import:** CSV format compatible with billing software
- **Empty Fields:** Represented as empty strings, not null indicators

## Field Naming Conventions

**Professional Medical Billing Style:**
- `Patient_Last_Name` (not `lastname`)
- `Patient_MRN` (not `mr_number`)
- `Date_of_Service` (not `dos`)
- `CPT_Code` (not `code`)
- `Ordering_Provider` (not `provider`)

## Common Issues to Avoid

1. **"nan" or "NaN" strings** - Shows as text
2. **Inconsistent date formats** - Mix of formats
3. **Missing MRN** - Cannot bill without identifier
4. **Invalid dates** - 13/01/2025 or 02/30/2025
5. **Multiple units for 80307** - Should always be 1
6. **Service date vs completed date** - Bill on collection date
