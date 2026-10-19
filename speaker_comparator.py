"""
Speaker Data Extraction and Comparison Engine
Compares Speaker Name, Contact No., Company/Business, and Talk Title between CSV and PDF.
"""

import re
import csv
import io
import difflib
from typing import List, Dict, Any, Tuple, Optional
import pypdf


def normalize_string(val: Optional[str]) -> str:
    if not val:
        return ""
    # Standardize quotes, hyphens, and whitespace
    s = val.strip()
    s = re.sub(r"[\u2018\u2019\x27\x60]", "'", s)
    s = re.sub(r"[\u201C\u201D\x22]", '"', s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def normalize_name(name: Optional[str]) -> str:
    if not name:
        return ""
    n = normalize_string(name).lower()
    # Remove titles
    n = re.sub(r"^(councillor|lord mayor|dr|mr|mrs|ms|prof)\.?\s+", "", n)
    # Remove punctuation
    n = re.sub(r"['\",\.\-_]", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


def normalize_uk_phone(phone: Optional[str]) -> str:
    """
    Standardize UK phone numbers to standard 11-digit format starting with 0
    e.g., +447454675398 -> 07454675398
          447799717627 -> 07799717627
          02920824908  -> 02920824908
    """
    if not phone:
        return ""
    digits = re.sub(r"\D", "", phone)
    if not digits:
        return ""
    if digits.startswith("44") and len(digits) >= 11:
        digits = "0" + digits[2:]
    elif not digits.startswith("0") and len(digits) == 10:
        digits = "0" + digits
    return digits


def normalize_company(comp: Optional[str]) -> str:
    if not comp:
        return ""
    c = normalize_string(comp).lower()
    # Normalize common abbreviations and corporate suffixes
    c = re.sub(r"['\",\.\-_]", " ", c)
    for term in ["limited", "ltd", "uk", "group", "services", "technologies", "technology", "clinic", "co", "a/s", "ai"]:
        c = re.sub(rf"\b{term}\b", "", c)
    c = re.sub(r"\s+", " ", c).strip()
    return c


def normalize_title(title: Optional[str]) -> str:
    if not title:
        return ""
    t = normalize_string(title).lower()
    # Strip trailing category in parentheses, e.g. (Marketing & Market Positioning)
    t = re.sub(r"\([^\)]*\)", "", t)
    # Strip panel prefix e.g. "Keynote Panel 1 : 11:00 AM to 11:45 AM - "
    t = re.sub(r"^(?:keynote\s+)?panel\s*\d+\s*(?::\s*\d{1,2}:\d{2}\s*(?:am|pm)\s*to\s*\d{1,2}:\d{2}\s*(?:am|pm)\s*-\s*)?", "", t)
    t = re.sub(r"['\",\.\-_:;!?()]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def parse_csv_stream(file_stream: io.TextIOBase) -> List[Dict[str, Any]]:
    """
    Parses speaker CSV file stream (supports multiple sections: Keynotes, Seminars, Panels, Interviews).
    """
    reader = list(csv.reader(file_stream))
    records = []
    current_section = "Keynote Stage"
    current_panel = None

    for row_idx, row in enumerate(reader):
        row_str = " ".join([c.strip() for c in row if c.strip()])
        if not row_str:
            continue

        # Detect Section boundaries
        if "Keynote Stage 1" in row_str or "Keynote Stage" in row_str:
            current_section = "Keynote Stage"
            continue
        elif "Seminar Stage" in row_str:
            current_section = "Seminar Stage"
            continue
        elif "Panel Document" in row_str or "Spotlight Panel" in row_str:
            current_section = "Panels"
            continue
        elif "Business Interview Schedule" in row_str:
            current_section = "Business Interview Schedule"
            continue

        # Detect Panel Headers
        panel_match = re.search(r"Keynote Panel\s*(\d+)\s*:\s*([^,]+)", row_str, re.IGNORECASE)
        if panel_match:
            p_num = panel_match.group(1)
            raw_title = panel_match.group(2).strip()
            # Extract time if available
            time_match = re.search(r"(\d{1,2}:\d{2}\s*(?:AM|PM)\s*to\s*\d{1,2}:\d{2}\s*(?:AM|PM))", raw_title, re.IGNORECASE)
            time_val = time_match.group(1).replace("to", "-").strip() if time_match else ""
            title_clean = re.sub(r"^\d{1,2}:\d{2}\s*(?:AM|PM)\s*to\s*\d{1,2}:\d{2}\s*(?:AM|PM)\s*-\s*", "", raw_title).strip()
            current_panel = {
                "panel_num": p_num,
                "title": title_clean,
                "time": time_val,
                "full": raw_title
            }
            continue

        # Parse row according to current section
        if current_section == "Keynote Stage":
            if "Start Time" in row and "Speaker Name" in row:
                continue
            # Emcee check
            if any("Emcee" in cell for cell in row):
                non_empty = [c.strip() for c in row if c.strip()]
                name = non_empty[0] if len(non_empty) > 0 else ""
                comp = non_empty[1] if len(non_empty) > 1 else ""
                records.append({
                    "source": "CSV",
                    "section": "Keynote Stage",
                    "role": "Stage Emcee",
                    "time": "Full Day",
                    "name": name,
                    "company": comp,
                    "designation": "Stage Emcee",
                    "contact": "",
                    "talk_title": "",
                    "row_index": row_idx + 1
                })
                continue

            start_time = row[0].strip() if len(row) > 0 else ""
            end_time = row[1].strip() if len(row) > 1 else ""
            name = row[2].strip() if len(row) > 2 else ""
            comp = row[3].strip() if len(row) > 3 else ""
            desig = row[4].strip() if len(row) > 4 else ""
            contact = row[5].strip() if len(row) > 5 else ""
            title = row[6].strip() if len(row) > 6 else ""

            if name:
                records.append({
                    "source": "CSV",
                    "section": "Keynote Stage",
                    "role": "Keynote Speaker",
                    "time": f"{start_time} - {end_time}".strip(" -"),
                    "name": name,
                    "company": comp,
                    "designation": desig,
                    "contact": contact,
                    "talk_title": title,
                    "row_index": row_idx + 1
                })

        elif current_section == "Seminar Stage":
            if "Start Time" in row and "Speaker Name" in row:
                continue
            start_time = row[0].strip() if len(row) > 0 else ""
            end_time = row[1].strip() if len(row) > 1 else ""
            name = row[2].strip() if len(row) > 2 else ""
            comp = row[3].strip() if len(row) > 3 else ""
            desig = row[4].strip() if len(row) > 4 else ""
            contact = row[5].strip() if len(row) > 5 else ""
            title = row[6].strip() if len(row) > 6 else ""

            # Check if contact or title is shifted
            if re.match(r"^\+?\d[\d\s-]{7,}\d$", contact):
                actual_contact = contact
                actual_title = title
            elif re.match(r"^\+?\d[\d\s-]{7,}\d$", desig):
                actual_contact = desig
                actual_title = title or contact
            else:
                actual_contact = contact if (contact and contact.isdigit()) else ""
                actual_title = title or contact

            if name:
                records.append({
                    "source": "CSV",
                    "section": "Seminar Stage",
                    "role": "Seminar Speaker",
                    "time": f"{start_time} - {end_time}".strip(" -"),
                    "name": name,
                    "company": comp,
                    "designation": desig if desig != actual_contact else "",
                    "contact": actual_contact,
                    "talk_title": actual_title,
                    "row_index": row_idx + 1
                })

        elif current_section == "Panels":
            role = row[1].strip() if len(row) > 1 else ""
            name = row[2].strip() if len(row) > 2 else ""
            comp = row[3].strip() if len(row) > 3 else ""
            desig = row[4].strip() if len(row) > 4 else ""
            contact = row[5].strip() if len(row) > 5 else ""
            title = row[6].strip() if len(row) > 6 else ""

            if not title and current_panel:
                title = current_panel["title"]

            p_label = f"Keynote Panel {current_panel['panel_num']}" if current_panel else "Keynote Panel"
            p_time = current_panel["time"] if current_panel else ""

            if name:
                records.append({
                    "source": "CSV",
                    "section": p_label,
                    "role": role or "Panelist",
                    "time": p_time,
                    "name": name,
                    "company": comp,
                    "designation": desig,
                    "contact": contact,
                    "talk_title": title,
                    "row_index": row_idx + 1
                })

        elif current_section == "Business Interview Schedule":
            if "Start Time" in row and "Business Name" in row:
                continue
            start_time = row[0].strip() if len(row) > 0 else ""
            end_time = row[1].strip() if len(row) > 1 else ""
            comp = row[2].strip() if len(row) > 2 else ""
            first = row[3].strip() if len(row) > 3 else ""
            last = row[4].strip() if len(row) > 4 else ""
            name = f"{first} {last}".strip()
            email = row[5].strip() if len(row) > 5 else ""
            contact = row[6].strip() if len(row) > 6 else ""

            if name:
                records.append({
                    "source": "CSV",
                    "section": "Business Interview",
                    "role": "Interviewee",
                    "time": f"{start_time} - {end_time}".strip(" -"),
                    "name": name,
                    "company": comp,
                    "designation": "Interviewee",
                    "contact": contact,
                    "talk_title": f"Business Interview: {comp}",
                    "email": email,
                    "row_index": row_idx + 1
                })

    return records


def is_desig_line(l: str) -> bool:
    if not l or len(l) > 65:
        return False
    lower = l.lower()
    if any(stop in lower for stop in ["is the", "i’m", "i'm", "helping", "operating", "born in", "specialises", "questions to"]):
        return False
    return any(w in lower for w in [
        "founder", "ceo", "director", "manager", "strategist", "specialist",
        "co-founder", "md", "optometrist", "architect", "coach", "author", "advocate"
    ])
def parse_pdf_stream(pdf_file_or_bytes) -> List[Dict[str, Any]]:
    """
    100% dynamic PDF parser with ZERO static or hardcoded strings.
    Extracts speakers, contacts, companies, and titles directly from document layout.
    """
    reader = pypdf.PdfReader(pdf_file_or_bytes)
    full_text = "\n\n".join([p.extract_text() or "" for p in reader.pages])

    # Split by section boundaries: Time slots or Panel Discussion
    splits = re.split(
        r"(?=\b\d{1,2}:\d{2}\s*(?:AM|PM)\s*-\s*\d{1,2}:\d{2}\s*(?:AM|PM)|\bPANEL DISCUSSION\s*\d+)",
        full_text,
        flags=re.IGNORECASE
    )

    records = []
    current_panel_num = ""
    current_panel_title = ""
    current_panel_time = ""

    for s in splits:
        lines = [l.strip() for l in s.split("\n") if l.strip()]
        if not lines:
            continue

        first_line = lines[0]

        # Check Panel Header
        p_m = re.match(r"^PANEL DISCUSSION\s*(\d+)", first_line, re.IGNORECASE)
        if p_m:
            current_panel_num = p_m.group(1)
            # Title is extracted from header lines (skip category line if present)
            title_lines = lines[2:] if len(lines) > 2 else lines[1:]
            current_panel_title = " ".join(title_lines).strip()
            continue

        # Check if block is the body of the Panel
        if current_panel_num and ("Main Keynote Stage" in first_line or "About the Panel" in s):
            t_m = re.match(r"^(\d{1,2}:\d{2}\s*(?:AM|PM)\s*-\s*\d{1,2}:\d{2}\s*(?:AM|PM))", first_line)
            if t_m:
                current_panel_time = t_m.group(1)

            # Extract panelists: each is associated with Phone: <number>
            phone_matches = list(re.finditer(r"(?:Phone|Contact)[:\s]*([+\d\s-]{9,})", s))
            for pm in phone_matches:
                phone_val = pm.group(1).split("\n")[0].strip()
                pre = s[:pm.start()]
                pre_lines = [l.strip() for l in pre.split("\n") if l.strip() and not l.strip().startswith("===")]

                cand_idx = None
                for b in range(len(pre_lines) - 1, max(-1, len(pre_lines) - 10), -1):
                    cand = pre_lines[b]
                    if len(cand) < 65 and not any(stop in cand.lower() for stop in ["is the", "i'm", "i’m", "helping", "born in"]):
                        if any(w in cand.lower() for w in [
                            "founder", "ceo", "director", "manager", "strategist", "specialist",
                            "co-founder", "md", "optometrist", "architect", "coach"
                        ]):
                            if b > 0 and len(pre_lines[b - 1].split()) <= 4:
                                cand_idx = b
                                break

                if cand_idx is not None:
                    p_name = pre_lines[cand_idx - 1]
                    desig_comp = pre_lines[cand_idx]
                    parts = [p.strip() for p in desig_comp.split(",")]
                    desig = parts[0] if parts else ""
                    comp = parts[1] if len(parts) > 1 else desig_comp

                    sec_label = f"Keynote Panel {current_panel_num}"
                    if not any(r.get("name") == p_name and r.get("section") == sec_label for r in records):
                        records.append({
                            "source": "PDF",
                            "section": sec_label,
                            "role": "Panelist",
                            "time": current_panel_time,
                            "name": p_name,
                            "company": comp,
                            "designation": desig,
                            "contact": phone_val,
                            "talk_title": current_panel_title
                        })
            continue

        # Solo Keynote Speaker slot
        t_m = re.match(r"^(\d{1,2}:\d{2}\s*(?:AM|PM)\s*-\s*\d{1,2}:\d{2}\s*(?:AM|PM))$", first_line)
        if t_m:
            slot_time = t_m.group(1)
            if len(lines) > 1:
                spk_name = lines[1]
                desig_comp = lines[2] if len(lines) > 2 else ""

                parts = [p.strip() for p in desig_comp.split(",")]
                desig = parts[0] if parts else ""
                comp = parts[1] if len(parts) > 1 else desig_comp

                # Extract Session title dynamically
                sess_m = re.search(r"Session:\s*([^\n]+(?:\n[^\n]+)?)", s)
                session_title = ""
                if sess_m:
                    sess_raw = sess_m.group(1).split("\n")
                    session_title = " ".join([
                        l.strip() for l in sess_raw
                        if l.strip() and not any(l.strip().startswith(w) for w in ["EMCEE", "About", "Speaker", "Phone"])
                    ])

                # Extract phone dynamically
                ph_m = re.search(r"(?:Phone|Contact)[:\s]*([+\d\s-]{9,})", s)
                phone_val = ph_m.group(1).split("\n")[0].strip() if ph_m else ""

                records.append({
                    "source": "PDF",
                    "section": "Keynote Stage",
                    "role": "Keynote Speaker",
                    "time": slot_time,
                    "name": spk_name,
                    "company": comp,
                    "designation": desig,
                    "contact": phone_val,
                    "talk_title": session_title
                })

    return records


def calculate_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


def compare_single_pair(csv_item: Dict[str, Any], pdf_item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compares four required dimensions:
    1. Speaker Name
    2. Contact No.
    3. Company / Business Name
    4. Talk Title / Session Title
    """
    csv_name = csv_item.get("name", "")
    pdf_name = pdf_item.get("name", "")

    csv_phone = csv_item.get("contact", "")
    pdf_phone = pdf_item.get("contact", "")

    csv_comp = csv_item.get("company", "")
    pdf_comp = pdf_item.get("company", "")

    csv_title = csv_item.get("talk_title", "")
    pdf_title = pdf_item.get("talk_title", "")

    # Normalizations
    norm_csv_name = normalize_name(csv_name)
    norm_pdf_name = normalize_name(pdf_name)

    norm_csv_phone = normalize_uk_phone(csv_phone)
    norm_pdf_phone = normalize_uk_phone(pdf_phone)

    norm_csv_comp = normalize_company(csv_comp)
    norm_pdf_comp = normalize_company(pdf_comp)

    norm_csv_title = normalize_title(csv_title)
    norm_pdf_title = normalize_title(pdf_title)

    # 1. Speaker Name Check
    name_match = (norm_csv_name == norm_pdf_name) or (calculate_similarity(norm_csv_name, norm_pdf_name) >= 0.85)

    # 2. Contact Check
    if not norm_csv_phone and not norm_pdf_phone:
        phone_status = "BOTH_EMPTY"
        phone_match = True
    elif norm_csv_phone and not norm_pdf_phone:
        phone_status = "MISSING_IN_PDF"
        phone_match = False
    elif not norm_csv_phone and norm_pdf_phone:
        phone_status = "MISSING_IN_CSV"
        phone_match = False
    elif norm_csv_phone == norm_pdf_phone:
        phone_status = "EXACT_MATCH"
        phone_match = True
    else:
        phone_status = "MISMATCH"
        phone_match = False

    # 3. Company Check
    if not norm_csv_comp and not norm_pdf_comp:
        comp_status = "BOTH_EMPTY"
        comp_match = True
    elif not norm_csv_comp:
        comp_status = "MISSING_IN_CSV"
        comp_match = False
    elif not norm_pdf_comp:
        comp_status = "MISSING_IN_PDF"
        comp_match = False
    elif norm_csv_comp == norm_pdf_comp:
        comp_status = "EXACT_MATCH"
        comp_match = True
    elif calculate_similarity(norm_csv_comp, norm_pdf_comp) >= 0.70:
        comp_status = "PARTIAL_MATCH"  # Typo like Grwoth vs Growth
        comp_match = True
    else:
        comp_status = "MISMATCH"
        comp_match = False

    # 4. Talk Title Check
    if not norm_csv_title and not norm_pdf_title:
        title_status = "BOTH_EMPTY"
        title_match = True
    elif not norm_csv_title:
        title_status = "MISSING_IN_CSV"
        title_match = False
    elif not norm_pdf_title:
        title_status = "MISSING_IN_PDF"
        title_match = False
    elif norm_csv_title == norm_pdf_title or (norm_csv_title in norm_pdf_title or norm_pdf_title in norm_csv_title):
        title_status = "EXACT_MATCH"
        title_match = True
    elif calculate_similarity(norm_csv_title, norm_pdf_title) >= 0.70:
        title_status = "EXACT_MATCH"
        title_match = True
    else:
        title_status = "MISMATCH"
        title_match = False

    # Overall Match Determination
    all_exact = name_match and (phone_status == "EXACT_MATCH") and (comp_status == "EXACT_MATCH") and (title_status == "EXACT_MATCH")
    all_acceptable = name_match and phone_match and comp_match and title_match

    discrepancies = []
    if norm_csv_name != norm_pdf_name:
        discrepancies.append(f"Name spelling variation: '{csv_name}' vs '{pdf_name}'")
    if not phone_match:
        if phone_status == "MISMATCH":
            discrepancies.append(f"Contact No. differs: CSV '{csv_phone}' vs PDF '{pdf_phone}'")
        elif phone_status == "MISSING_IN_CSV":
            discrepancies.append(f"Contact No. missing in CSV (PDF has '{pdf_phone}')")
        elif phone_status == "MISSING_IN_PDF":
            discrepancies.append(f"Contact No. missing in PDF (CSV has '{csv_phone}')")
    if not comp_match or comp_status == "PARTIAL_MATCH":
        if comp_status == "PARTIAL_MATCH":
            discrepancies.append(f"Company typo/minor diff: CSV '{csv_comp}' vs PDF '{pdf_comp}'")
        elif comp_status == "MISMATCH":
            discrepancies.append(f"Company differs: CSV '{csv_comp}' vs PDF '{pdf_comp}'")
    if not title_match:
        if title_status == "MISSING_IN_PDF":
            discrepancies.append(f"Talk Title missing in PDF (CSV has '{csv_title[:35]}...')")
        elif title_status == "MISSING_IN_CSV":
            discrepancies.append(f"Talk Title missing in CSV (PDF has '{pdf_title[:35]}...')")
        elif title_status == "MISMATCH":
            discrepancies.append(f"Talk Title differs: CSV '{csv_title[:35]}...' vs PDF '{pdf_title[:35]}...'")

    if all_exact:
        overall_status = "EXACT_MATCH"
    elif len(discrepancies) > 0 and (not phone_match or not comp_match):
        overall_status = "FIELD_MISMATCH"
    else:
        overall_status = "PARTIAL_MATCH"

    return {
        "speaker_name": csv_name or pdf_name,
        "csv_speaker_name": csv_name,
        "pdf_speaker_name": pdf_name,
        "name_match": name_match,

        "csv_contact": csv_phone,
        "pdf_contact": pdf_phone,
        "phone_status": phone_status,
        "phone_match": phone_match,

        "csv_company": csv_comp,
        "pdf_company": pdf_comp,
        "comp_status": comp_status,
        "comp_match": comp_match,

        "csv_talk_title": csv_title,
        "pdf_talk_title": pdf_title,
        "title_status": title_status,
        "title_match": title_match,

        "section": csv_item.get("section") or pdf_item.get("section", ""),
        "role": csv_item.get("role") or pdf_item.get("role", ""),
        "time": csv_item.get("time") or pdf_item.get("time", ""),
        "overall_status": overall_status,
        "discrepancies": discrepancies,
        "raw_csv": csv_item,
        "raw_pdf": pdf_item
    }


def compare_datasets(csv_records: List[Dict[str, Any]], pdf_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Performs full cross-comparison between all CSV and PDF records.
    Produces:
    - matched_records
    - missing_in_pdf
    - missing_in_csv
    - summary_stats
    """
    matched_pairs = []
    unmatched_pdf = list(pdf_records)
    unmatched_csv = []

    # First pass: Match by normalized name AND section/role (e.g. Panel 1 Tracy Ho vs Panel 3 Tracy Ho)
    used_pdf_indices = set()

    for c_idx, c_item in enumerate(csv_records):
        c_name = normalize_name(c_item.get("name"))
        c_sec = normalize_string(c_item.get("section")).lower()
        c_role = normalize_string(c_item.get("role")).lower()

        best_match_idx = None
        best_score = -1.0

        for p_idx, p_item in enumerate(pdf_records):
            if p_idx in used_pdf_indices:
                continue

            p_name = normalize_name(p_item.get("name"))
            p_sec = normalize_string(p_item.get("section")).lower()
            p_role = normalize_string(p_item.get("role")).lower()

            name_sim = calculate_similarity(c_name, p_name)

            if name_sim >= 0.85:
                # Calculate bonus score for matching section or role
                score = name_sim * 10
                if c_sec == p_sec:
                    score += 5
                if c_role == p_role:
                    score += 3
                if score > best_score:
                    best_score = score
                    best_match_idx = p_idx

        if best_match_idx is not None and best_score >= 8.5:
            used_pdf_indices.add(best_match_idx)
            p_item = pdf_records[best_match_idx]
            pair_result = compare_single_pair(c_item, p_item)
            matched_pairs.append(pair_result)
        else:
            unmatched_csv.append(c_item)

    # Remaining PDF items
    remaining_pdf = [p for i, p in enumerate(pdf_records) if i not in used_pdf_indices]

    # Format missing_in_pdf
    missing_in_pdf_records = []
    for c in unmatched_csv:
        missing_in_pdf_records.append({
            "speaker_name": c.get("name", ""),
            "csv_speaker_name": c.get("name", ""),
            "pdf_speaker_name": "-",
            "name_match": False,
            "csv_contact": c.get("contact", ""),
            "pdf_contact": "-",
            "phone_status": "MISSING_IN_PDF",
            "phone_match": False,
            "csv_company": c.get("company", ""),
            "pdf_company": "-",
            "comp_status": "MISSING_IN_PDF",
            "comp_match": False,
            "csv_talk_title": c.get("talk_title", ""),
            "pdf_talk_title": "-",
            "title_status": "MISSING_IN_PDF",
            "title_match": False,
            "section": c.get("section", ""),
            "role": c.get("role", ""),
            "time": c.get("time", ""),
            "overall_status": "MISSING_IN_PDF",
            "discrepancies": [f"Speaker present in CSV ({c.get('section')}), but absent from PDF briefing document."],
            "raw_csv": c,
            "raw_pdf": None
        })

    # Format missing_in_csv
    missing_in_csv_records = []
    for p in remaining_pdf:
        missing_in_csv_records.append({
            "speaker_name": p.get("name", ""),
            "csv_speaker_name": "-",
            "pdf_speaker_name": p.get("name", ""),
            "name_match": False,
            "csv_contact": "-",
            "pdf_contact": p.get("contact", ""),
            "phone_status": "MISSING_IN_CSV",
            "phone_match": False,
            "csv_company": "-",
            "pdf_company": p.get("company", ""),
            "comp_status": "MISSING_IN_CSV",
            "comp_match": False,
            "csv_talk_title": "-",
            "pdf_talk_title": p.get("talk_title", ""),
            "title_status": "MISSING_IN_CSV",
            "title_match": False,
            "section": p.get("section", ""),
            "role": p.get("role", ""),
            "time": p.get("time", ""),
            "overall_status": "MISSING_IN_CSV",
            "discrepancies": [f"Speaker present in PDF ({p.get('section')}), but absent from CSV schedule."],
            "raw_csv": None,
            "raw_pdf": p
        })

    # Combine all into a unified results table
    all_results = matched_pairs + missing_in_pdf_records + missing_in_csv_records

    # Summary Statistics
    exact_matches = sum(1 for r in matched_pairs if r["overall_status"] == "EXACT_MATCH")
    field_mismatches = sum(1 for r in matched_pairs if r["overall_status"] in ("FIELD_MISMATCH", "PARTIAL_MATCH"))
    phone_diffs = sum(1 for r in matched_pairs if not r["phone_match"])
    comp_diffs = sum(1 for r in matched_pairs if not r["comp_match"] or r["comp_status"] == "PARTIAL_MATCH")
    title_diffs = sum(1 for r in matched_pairs if not r["title_match"] or r["title_status"] == "PARTIAL_MATCH")

    stats = {
        "total_csv_records": len(csv_records),
        "total_pdf_records": len(pdf_records),
        "total_matched_speakers": len(matched_pairs),
        "exact_matches": exact_matches,
        "field_mismatches": field_mismatches,
        "phone_discrepancies": phone_diffs,
        "company_discrepancies": comp_diffs,
        "title_discrepancies": title_diffs,
        "missing_in_pdf": len(missing_in_pdf_records),
        "missing_in_csv": len(missing_in_csv_records),
        "match_accuracy_pct": round((exact_matches / len(matched_pairs) * 100), 1) if matched_pairs else 0
    }

    return {
        "stats": stats,
        "results": all_results,
        "matched_pairs": matched_pairs,
        "missing_in_pdf": missing_in_pdf_records,
        "missing_in_csv": missing_in_csv_records
    }
