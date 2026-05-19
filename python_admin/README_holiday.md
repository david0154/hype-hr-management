# Hype HR — Holiday Manager (Python Admin)

## Setup

```bash
pip install firebase-admin rich
```

Place your `serviceAccountKey.json` in the `python_admin/` folder.

## Run

```bash
cd python_admin
python holiday_manager.py
```

## Menu Options

| Option | Description |
|--------|-------------|
| 1 | Add / Update a holiday (date, occasion, type, paid) |
| 2 | List all holidays |
| 3 | Delete a holiday |
| 4 | Check which employees are eligible for a holiday |
| 5 | Exit |

## Holiday Types
- **Festival** — Diwali, Eid, Christmas etc.
- **National** — Independence Day, Republic Day
- **Optional** — Employee can choose
- **Restricted** — Company specific

## Firestore Structure

```
holidays/
  {YYYYMMDD}/
    date      : "2025-10-20"
    occasion  : "Diwali"
    type      : "Festival"
    paid      : true
```

## Eligibility Rule

An employee is **eligible** for a paid holiday if they have at least 1 attendance record  
(type = IN or COMPLETE) in the **±2 day window** around the holiday date.

Example: Holiday on **20 Oct** → eligible if present on any of **18, 19, 20, 21, 22 Oct**.
