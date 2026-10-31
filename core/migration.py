"""
core/migration.py
==================
One-off migration of project data from the tool's earlier, non-standard
cost structure (codes like "03.01.01", with "10 Income" and "11 Unplanned
costs (contingency)" as Principal Activities) to the official ISDC 2012
structure (codes like "04.0303").

- A backup copy of the database file is made before anything changes.
- Old codes are mapped to the closest ISDC 2012 code. Where several old
  codes map to the same new code, amounts are added and notes are kept.
- Entries of the old "Unplanned costs (contingency)" activity are moved
  into the Contingency cost category (ISDC treats contingency as a cost
  category, not an activity).
- Entries of the old "Income" activity are moved to 11.04 Asset recovery
  and flagged in the notes so the user can check the sign.
- Applicability overrides are carried over to the mapped codes.
"""

import re
import shutil

OLD_FORMAT = re.compile(r"^\d{2}\.\d{2}(\.\d{2})?$")   # "03.01" or "03.01.01"

# Old Level-3 code -> ISDC 2012 Typical Activity
OLD_L3 = {
    "01.01.01": "01.0102", "01.01.02": "01.0102", "01.01.03": "01.0101",
    "01.02.01": "01.0201", "01.02.02": "01.0201", "01.02.03": "01.0202",
    "01.03.01": "01.0501", "01.03.02": "01.0501", "01.03.03": "01.0501",
    "02.01.01": "02.0102", "02.01.02": "02.0201", "02.01.03": "02.0401",
    "02.02.01": "02.0101", "02.02.02": "02.0502", "02.02.03": "02.0101",
    "02.03.01": "04.0201", "02.03.02": "04.0202", "02.03.03": "01.0601",
    "03.01.01": "04.0303", "03.01.02": "04.0304", "03.01.03": "04.0703",
    "03.02.01": "04.0503", "03.02.02": "04.0601", "03.02.03": "04.0602",
    "03.03.01": "04.0506", "03.03.02": "04.0702", "03.03.03": "07.0301",
    "03.04.01": "04.0901", "03.04.02": "07.0501", "03.04.03": "04.0902",
    "04.01.01": "05.0901", "04.01.02": "05.0902", "04.01.03": "05.0903",
    "04.02.01": "05.0904", "04.02.02": "05.0104",
    "04.03.01": "05.0905", "04.03.02": "05.0906", "04.03.03": "05.1202",
    "05.01.01": "06.0301", "05.01.02": "06.0302", "05.01.03": "06.0304",
    "05.02.01": "06.0201", "05.02.02": "06.0201",
    "05.03.01": "06.0102", "05.03.02": "06.0307", "05.03.03": "06.0201",
    "06.01.01": "08.0201", "06.01.02": "08.0203", "06.01.03": "08.0205",
    "06.02.01": "08.0301", "06.02.02": "08.0306",
    "06.03.01": "06.0104", "06.03.02": "08.0402", "06.03.03": "08.0401", "06.03.04": "08.0305",
    "07.01.01": "09.0103", "07.01.02": "09.0105", "07.02.01": "09.0201",
    "08.01.01": "02.0104", "08.01.02": "10.0101", "08.01.03": "10.0202",
    "08.02.01": "02.0104", "08.02.02": "10.0101", "08.03.01": "02.0104",
    "09.01.01": "11.0205", "09.01.02": "11.0301", "09.02.01": "11.0104", "09.02.02": "11.0104",
    "10.01.01": "11.0402", "10.01.02": "11.0402", "10.02.01": "11.0405",
    "11.01.01": "11.0104", "11.02.01": "11.0104",
}

# Old Level-2 code -> ISDC 2012 Activity Group
OLD_L2 = {
    "01.01": "01.0100", "01.02": "01.0200", "01.03": "01.0500",
    "02.01": "02.0100", "02.02": "02.0100", "02.03": "04.0200",
    "03.01": "04.0300", "03.02": "04.0500", "03.03": "04.0700", "03.04": "04.0900",
    "04.01": "05.0900", "04.02": "05.0900", "04.03": "05.0900",
    "05.01": "06.0300", "05.02": "06.0200", "05.03": "06.0100",
    "06.01": "08.0200", "06.02": "08.0300", "06.03": "08.0300",
    "07.01": "09.0100", "07.02": "09.0200",
    "08.01": "10.0100", "08.02": "10.0100", "08.03": "10.0100",
    "09.01": "11.0200", "09.02": "11.0100",
    "10.01": "11.0400", "10.02": "11.0400",
    "11.01": "11.0100", "11.02": "11.0100",
}

# Old Principal Activity -> ISDC 2012 Principal Activity (old 11 has no equivalent)
OLD_PA = {"01": "01", "02": "02", "03": "04", "04": "05", "05": "06", "06": "08",
          "07": "09", "08": "10", "09": "11", "10": "11"}

COST_KEYS = ("labour_eur", "investment_eur", "expenses_eur", "contingency_eur")


def map_old_code(code: str):
    """New code for an old-format code (any level), or None if it has no equivalent."""
    if code in OLD_L3:
        return OLD_L3[code]
    if code in OLD_L2:
        return OLD_L2[code]
    return None


def needs_migration(conn) -> bool:
    c = conn.cursor()
    c.execute("SELECT isdc_code FROM cost_entries")
    if any(OLD_FORMAT.match(r[0]) for r in c.fetchall()):
        return True
    c.execute("SELECT code FROM applicability_overrides")
    if any(OLD_FORMAT.match(r[0]) for r in c.fetchall()):
        return True
    c.execute("SELECT code FROM isdc_level2 LIMIT 1")
    row = c.fetchone()
    return bool(row and re.match(r"^\d{2}\.\d{2}$", row[0]))


def backup_database(db_path: str) -> str:
    backup = re.sub(r"(\.db)?$", ".backup-before-ISDC2012.db", db_path, count=1)
    shutil.copy2(db_path, backup)
    return backup


def migrate(conn, db_path: str = None) -> dict:
    """Migrate cost entries and overrides to ISDC 2012 codes. Returns a summary."""
    summary = {"backup": None, "entries": 0, "merged": 0, "overrides": 0, "dropped": []}
    if db_path:
        conn.commit()
        summary["backup"] = backup_database(db_path)
    c = conn.cursor()

    # --- cost entries -------------------------------------------------
    c.execute("SELECT * FROM cost_entries")
    rows = [dict(r) for r in c.fetchall()]
    old_rows = [r for r in rows if OLD_FORMAT.match(r["isdc_code"])]
    new_rows = {}
    for r in old_rows:
        old = r["isdc_code"]
        new = map_old_code(old)
        if not new:
            summary["dropped"].append(old)
            continue
        vals = {k: r.get(k) or 0.0 for k in COST_KEYS}
        note = r.get("notes") or ""
        if old.startswith("11."):            # old "Unplanned costs (contingency)" activity
            vals = {"labour_eur": 0.0, "investment_eur": 0.0, "expenses_eur": 0.0,
                    "contingency_eur": sum(vals.values())}
            note = (note + " " if note else "") + f"[migrated from old contingency item {old}]"
        elif old.startswith("10."):          # old "Income" activity
            note = (note + " " if note else "") + (f"[migrated from old Income item {old}; "
                                                   "enter income as a negative value]")
        else:
            note = (note + " " if note else "") + f"[from old code {old}]"
        key = (r["project_id"], new)
        level = 2 if new.endswith("00") else 3
        if key in new_rows:
            agg = new_rows[key]
            for k in COST_KEYS:
                agg[k] += vals[k]
            agg["notes"] = (agg["notes"] + " " + note).strip()
            agg["phase_id"] = agg["phase_id"] or r.get("phase_id")
            summary["merged"] += 1
        else:
            new_rows[key] = dict(project_id=r["project_id"], isdc_code=new, level=level,
                                 phase_id=r.get("phase_id"), notes=note.strip(), **vals)
    for r in old_rows:
        c.execute("DELETE FROM cost_entries WHERE id=?", (r["id"],))
    for e in new_rows.values():
        c.execute("SELECT * FROM cost_entries WHERE project_id=? AND isdc_code=?",
                  (e["project_id"], e["isdc_code"]))
        existing = c.fetchone()
        if existing:   # already a new-format entry on that code: add to it
            existing = dict(existing)
            for k in COST_KEYS:
                e[k] += existing.get(k) or 0.0
            e["notes"] = ((existing.get("notes") or "") + " " + e["notes"]).strip()
            c.execute("DELETE FROM cost_entries WHERE project_id=? AND isdc_code=?",
                      (e["project_id"], e["isdc_code"]))
        c.execute(
            "INSERT INTO cost_entries (project_id, isdc_code, level, labour_eur, investment_eur, "
            "expenses_eur, contingency_eur, phase_id, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (e["project_id"], e["isdc_code"], e["level"], e["labour_eur"], e["investment_eur"],
             e["expenses_eur"], e["contingency_eur"], e["phase_id"], e["notes"]))
        summary["entries"] += 1

    # --- applicability overrides ---------------------------------------
    c.execute("SELECT project_id, code, rating, justification FROM applicability_overrides")
    overrides = [dict(r) for r in c.fetchall()]
    for o in overrides:
        old = o["code"]
        if not (OLD_FORMAT.match(old) or re.match(r"^\d{2}$", old)):
            continue
        c.execute("DELETE FROM applicability_overrides WHERE project_id=? AND code=?",
                  (o["project_id"], old))
        new = OLD_PA.get(old) if len(old) == 2 else map_old_code(old)
        if not new:
            continue
        c.execute("INSERT OR IGNORE INTO applicability_overrides (project_id, code, rating, justification) "
                  "VALUES (?, ?, ?, ?)",
                  (o["project_id"], new, o["rating"],
                   ((o["justification"] or "") + f" [migrated from {old}]").strip()))
        summary["overrides"] += 1
    conn.commit()
    return summary
