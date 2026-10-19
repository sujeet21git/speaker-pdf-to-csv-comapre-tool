# 🎙️ Speaker Compare & Verification Tool

An intelligent, full-stack Python application designed to cross-verify and compare event speaker information between **PDF Briefing Documents** and **CSV Contact Schedules**.

Built for event managers, marketing operations, and B2B conference organizers to catch phone discrepancies, company name typos, missing speakers, and session title mismatches in seconds.

---

## ✨ Features

- **Split-View Dual Upload Interface**:
  - **Left Card**: Drag-and-drop or select PDF Briefing document.
  - **Right Card**: Drag-and-drop or select CSV Contact Schedule.
- **Deep 4-Point Comparison Engine**:
  1. **Speaker Name**: Case-insensitive fuzzy matching, honorific stripping (`Dr`, `Mr`, `Lord Mayor`, etc.).
  2. **Contact Number**: Standardized UK phone normalization (`+44`, `07`, `029` formats), exact digit mismatch highlighting.
  3. **Company / Business Name**: Suffix normalization (`Ltd`, `Limited`, `UK`, `AI`) and typo detection (e.g., `Grwoth` vs `Growth`).
  4. **Talk / Session Title**: Keynote titles and panel discussion themes cross-matched.
- **Instant 1-Click Sample File Demo**:
  - Preloaded with **Cardiff Business Growth Expo 2026** dataset for instant testing.
- **Real-Time KPI Dashboard**:
  - Total Evaluated Records
  - 🟢 Exact Matches
  - 🟡 Field Mismatches
  - 📞 Phone Discrepancies
  - 🏢 Company Discrepancies
  - 🔴 Missing in PDF
  - 🔵 Missing in CSV
- **Interactive Filtering & Search**:
  - Live search across speaker name, company, talk title, and phone number.
  - Quick filter pills to isolate phone differences, company typos, or missing records.
  - Stage/Section dropdown filter (`Keynote Stage`, `Keynote Panels`, `Seminar Stage`, `Business Interviews`).
- **Comprehensive Data Export**:
  - 📗 Styled **Excel (.xlsx)** export with multi-tab categorized sheets.
  - 📥 Clean **CSV** export for CRM and pipeline imports.
  - 🖨️ Formatted Print view.
- **Inspector Modal**:
  - Click the 🔍 inspection icon on any row to view raw JSON records from both CSV and PDF side-by-side with discrepancy diagnostic notes.

---

## 🏗️ Architecture & Project Structure

```text
speaker compare tool/
├── app.py                                        # Flask REST API backend & web server
├── speaker_comparator.py                         # Parsing, normalization & comparison engine
├── templates/
│   └── index.html                                # Modern dark-mode glassmorphic Web GUI
├── requirements.txt                              # Python package dependencies
├── .gitignore                                    # Git exclusion rules
├── cardiff speaker contact no. - Sheet1.csv       # Sample Cardiff Expo 2026 CSV schedule
└── keynote-emcee-briefing-cardiff-business-growth-expo-2026.pdf # Sample Cardiff Expo 2026 PDF
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.10 or higher
- Linux / macOS / Windows

### 2. Activate Virtual Environment & Install Dependencies

If setting up for the first time:

```bash
# 1. Create a virtual environment
python3 -m venv .venv

# 2. Activate the virtual environment
# On Linux/macOS:
source .venv/bin/activate
# On Windows:
# .venv\Scripts\activate

# 3. Install required packages
pip install -r requirements.txt
```

### 3. Run the Web GUI Server

```bash
# Run using the virtual environment python
.venv/bin/python app.py
```

Output:
```text
[INFO] Starting Speaker Comparison Server on http://127.0.0.1:5055
 * Running on http://127.0.0.1:5055
```

### 4. Access the Application

Open your browser and navigate to:

👉 **[http://127.0.0.1:5055](http://127.0.0.1:5055)**

---

## 📊 Sample Findings (Cardiff Business Growth Expo 2026)

When comparing `cardiff speaker contact no. - Sheet1.csv` against `keynote-emcee-briefing-cardiff-business-growth-expo-2026.pdf`:

| Category | Example Discrepancy Found |
| :--- | :--- |
| **📞 Phone Number Mismatch** | • **Estelle Cartlidge**: CSV `447709642469` vs PDF `07709642425` (last digits 469 vs 425)<br>• **Gweirydd Davies**: CSV `447791937887` vs PDF `07791937843`<br>• **Lucy Stagg**: CSV `442920824908` vs PDF `02920824864`<br>• **Elena Apalkova**: CSV `447493885686` vs PDF `07493885642`<br>• **Julie Wong**: CSV `447876761708` vs PDF `07876761664`<br>• **Aled Nelmes**: CSV `447711052211` vs PDF `07711052167`<br>• **Anna Lloyd Owen**: CSV `447531304929` vs PDF `07531304885`<br>• **Stefania Arca**: CSV `447518808468` vs PDF `07518808424`<br>• **Wendy Parker**: Contact missing in CSV panel row, PDF has `07984859031` |
| **🏢 Company Typos** | • **Santosh Kumar**: CSV listed `B2B Grwoth Hub` vs PDF `B2B Growth Hub`<br>• **Keila Costa**: CSV listed `Brainbridg` vs PDF `BrainBridg_`<br>• **Des O Connor**: CSV listed `Des O connor` vs PDF `DesOConnor.ai` |
| **🔴 Missing in PDF** | • **David Kershaw** (Listed in CSV Keynote Panel 4, but absent from PDF briefing)<br>• **Seminar Stage Speakers**: `Ashish Domah`, `Priyanka Sinha`, `Xohan Duran`, `Eloise Balmer`, `Maxine Jones`, `Radu Mamaliga` |
| **🔵 Missing in CSV** | • **Councillor Michael Michael** (Lord Mayor of Cardiff, Keynote Stage Opening Dignitary in PDF; CSV row 4 was blank) |

---

## 🔌 REST API Reference

| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/` | `GET` | Serves the interactive Web GUI application |
| `/api/health` | `GET` | Health check endpoint returning engine status & version |
| `/api/default-compare` | `GET` | Compares preloaded workspace sample files automatically |
| `/api/compare` | `POST` | Multipart form upload (`pdf_file` and `csv_file`) for custom comparison |
| `/api/export-excel` | `POST` | Generates and downloads multi-sheet styled `.xlsx` workbook |
| `/api/export-csv` | `POST` | Generates and downloads comparison results as `.csv` |

---

## 🛠️ Tech Stack

- **Backend**: Python 3.14 / Flask
- **Document Processing**: `pypdf`, `pdfplumber`, `csv`
- **Data Analysis**: `pandas`, `openpyxl`
- **Frontend**: Vanilla HTML5, Modern CSS (Glassmorphism, CSS Grid/Flexbox), Vanilla JavaScript (Zero external frontend frameworks)
- **Design Tokens**: Plus Jakarta Sans, JetBrains Mono, Dark slate palette with Neon Cyan & Purple accents

---

## 📄 License
Internal B2B Automation Tools. All rights reserved.
