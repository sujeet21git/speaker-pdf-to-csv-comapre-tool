#!/usr/bin/env python3
"""
Flask Web GUI Application for Speaker Comparison Tool
Upload PDF on one side, CSV on the other side.
Compares Speaker Name, Contact No., Company, and Talk Title.
"""

import os
import io
import re
import csv
import json
import logging
from typing import Dict, Any, List
from flask import Flask, request, jsonify, render_template, send_file, Response
import pandas as pd

from speaker_comparator import (
    parse_csv_stream,
    parse_pdf_stream,
    compare_datasets,
    normalize_name,
    normalize_uk_phone,
    normalize_company,
    normalize_title
)

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SpeakerComparator")

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32MB max upload

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CSV_PATH = os.path.join(BASE_DIR, "cardiff speaker contact no. - Sheet1.csv")
DEFAULT_PDF_PATH = os.path.join(BASE_DIR, "keynote-emcee-briefing-cardiff-business-growth-expo-2026.pdf")


@app.route("/")
def index():
    has_default_csv = os.path.exists(DEFAULT_CSV_PATH)
    has_default_pdf = os.path.exists(DEFAULT_PDF_PATH)
    return render_template(
        "index.html",
        has_default_csv=has_default_csv,
        has_default_pdf=has_default_pdf,
        default_csv_name=os.path.basename(DEFAULT_CSV_PATH) if has_default_csv else "",
        default_pdf_name=os.path.basename(DEFAULT_PDF_PATH) if has_default_pdf else ""
    )


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "service": "Speaker Comparison Engine", "version": "1.0.0"})


@app.route("/api/default-compare", methods=["GET"])
def default_compare():
    """Runs comparison using default workspace CSV and PDF files."""
    try:
        if not os.path.exists(DEFAULT_CSV_PATH) or not os.path.exists(DEFAULT_PDF_PATH):
            return jsonify({"error": "Default project files not found in workspace"}), 404

        with open(DEFAULT_CSV_PATH, "r", encoding="utf-8", errors="replace") as f:
            csv_records = parse_csv_stream(f)

        with open(DEFAULT_PDF_PATH, "rb") as f:
            pdf_records = parse_pdf_stream(f)

        comparison_output = compare_datasets(csv_records, pdf_records)
        comparison_output["files"] = {
            "csv_name": os.path.basename(DEFAULT_CSV_PATH),
            "pdf_name": os.path.basename(DEFAULT_PDF_PATH),
            "is_default": True
        }
        return jsonify(comparison_output)
    except Exception as e:
        logger.exception("Error running default comparison")
        return jsonify({"error": str(e)}), 500


@app.route("/api/compare", methods=["POST"])
def compare():
    """
    Accepts uploaded files via multipart form data:
    - Mode: 'pdf_vs_csv' or 'csv_vs_csv' (or auto-detected from file extensions)
    - File inputs:
        - file1 & file2, OR
        - pdf_file & csv_file
    """
    try:
        mode = request.form.get("mode", "").lower()
        file1 = request.files.get("file1")
        file2 = request.files.get("file2")

        # Fallback to pdf_file / csv_file field names for backward compatibility
        pdf_file = request.files.get("pdf_file") or (file1 if file1 and file1.filename.lower().endswith(".pdf") else None) or (file2 if file2 and file2.filename.lower().endswith(".pdf") else None)
        csv_file = request.files.get("csv_file") or (file2 if file2 and file2.filename.lower().endswith(".csv") else None) or (file1 if file1 and file1.filename.lower().endswith(".csv") else None)

        # Detect CSV-to-CSV mode:
        # 1. Explicit mode == 'csv_vs_csv', OR
        # 2. Both file1 and file2 are provided and end with .csv, OR
        # 3. Two CSV files uploaded
        is_csv_vs_csv = False
        if mode == "csv_vs_csv":
            is_csv_vs_csv = True
        elif file1 and file2 and file1.filename.lower().endswith(".csv") and file2.filename.lower().endswith(".csv"):
            is_csv_vs_csv = True

        if is_csv_vs_csv:
            csv1 = file1 or request.files.get("csv_file1") or csv_file
            csv2 = file2 or request.files.get("csv_file2") or request.files.get("csv_file")

            if not csv1 or not csv2:
                return jsonify({"error": "Two CSV files are required for CSV-to-CSV comparison."}), 400

            csv1_raw = csv1.read().decode("utf-8", errors="replace")
            csv2_raw = csv2.read().decode("utf-8", errors="replace")

            records1 = parse_csv_stream(io.StringIO(csv1_raw))
            records2 = parse_csv_stream(io.StringIO(csv2_raw))

            label1 = "CSV 1"
            label2 = "CSV 2"
            result = compare_datasets(records1, records2, label1=label1, label2=label2)
            result["files"] = {
                "mode": "csv_vs_csv",
                "source1_name": csv1.filename,
                "source2_name": csv2.filename,
                "source1_label": label1,
                "source2_label": label2,
                "csv_name": csv1.filename,
                "pdf_name": csv2.filename,
                "is_default": False
            }
            return jsonify(result)

        # PDF vs CSV comparison mode
        if not pdf_file and os.path.exists(DEFAULT_PDF_PATH):
            with open(DEFAULT_PDF_PATH, "rb") as f:
                pdf_bytes = io.BytesIO(f.read())
            pdf_name = os.path.basename(DEFAULT_PDF_PATH)
        elif pdf_file:
            pdf_bytes = io.BytesIO(pdf_file.read())
            pdf_name = pdf_file.filename
        else:
            return jsonify({"error": "PDF file is required for PDF-to-CSV comparison."}), 400

        if not csv_file and os.path.exists(DEFAULT_CSV_PATH):
            with open(DEFAULT_CSV_PATH, "r", encoding="utf-8", errors="replace") as f:
                csv_text = io.StringIO(f.read())
            csv_name = os.path.basename(DEFAULT_CSV_PATH)
        elif csv_file:
            csv_raw = csv_file.read().decode("utf-8", errors="replace")
            csv_text = io.StringIO(csv_raw)
            csv_name = csv_file.filename
        else:
            return jsonify({"error": "CSV file is required for PDF-to-CSV comparison."}), 400

        # Parse CSV & PDF
        csv_records = parse_csv_stream(csv_text)
        pdf_records = parse_pdf_stream(pdf_bytes)

        # Compare
        result = compare_datasets(csv_records, pdf_records, label1="CSV", label2="PDF")
        result["files"] = {
            "mode": "pdf_vs_csv",
            "source1_name": pdf_name,
            "source2_name": csv_name,
            "source1_label": "PDF",
            "source2_label": "CSV",
            "csv_name": csv_name,
            "pdf_name": pdf_name,
            "is_default": False
        }

        return jsonify(result)
    except Exception as e:
        logger.exception("Error processing uploaded files")
        return jsonify({"error": str(e)}), 500


@app.route("/api/export-excel", methods=["POST"])
def export_excel():
    """Generates a styled multi-tab Excel report of comparison results."""
    try:
        data = request.json or {}
        results = data.get("results", [])
        stats = data.get("stats", {})

        if not results:
            return jsonify({"error": "No data to export"}), 400

        l1 = stats.get("source1_label") or (results[0].get("source1_label") if results else "Source 1")
        l2 = stats.get("source2_label") or (results[0].get("source2_label") if results else "Source 2")

        # Convert to DataFrame
        export_rows = []
        for r in results:
            export_rows.append({
                "Status": r.get("overall_status", ""),
                f"Speaker Name ({l1})": r.get("source1_speaker_name") or r.get("csv_speaker_name", ""),
                f"Speaker Name ({l2})": r.get("source2_speaker_name") or r.get("pdf_speaker_name", ""),
                f"Contact No. ({l1})": r.get("source1_contact") or r.get("csv_contact", ""),
                f"Contact No. ({l2})": r.get("source2_contact") or r.get("pdf_contact", ""),
                "Contact Status": r.get("phone_status", ""),
                f"Company ({l1})": r.get("source1_company") or r.get("csv_company", ""),
                f"Company ({l2})": r.get("source2_company") or r.get("pdf_company", ""),
                "Company Status": r.get("comp_status", ""),
                f"Talk Title ({l1})": r.get("source1_talk_title") or r.get("csv_talk_title", ""),
                f"Talk Title ({l2})": r.get("source2_talk_title") or r.get("pdf_talk_title", ""),
                "Title Status": r.get("title_status", ""),
                "Stage/Section": r.get("section", ""),
                "Role": r.get("role", ""),
                "Time": r.get("time", ""),
                "Discrepancies": " | ".join(r.get("discrepancies", []))
            })

        df_all = pd.DataFrame(export_rows)

        # Filter subsets
        df_exact = df_all[df_all["Status"] == "EXACT_MATCH"]
        df_mismatches = df_all[df_all["Status"].isin(["FIELD_MISMATCH", "PARTIAL_MATCH"])]
        df_phone_diffs = df_all[df_all["Contact Status"].isin(["MISMATCH", "MISSING_IN_CSV", "MISSING_IN_PDF"])]
        df_missing_s2 = df_all[df_all["Status"] == "MISSING_IN_PDF"]
        df_missing_s1 = df_all[df_all["Status"] == "MISSING_IN_CSV"]

        # Stats DataFrame
        stats_df = pd.DataFrame(list(stats.items()), columns=["Metric", "Value"])

        # Write to in-memory Excel buffer
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            stats_df.to_excel(writer, sheet_name="Summary Overview", index=False)
            df_all.to_excel(writer, sheet_name="All Comparisons", index=False)
            if not df_mismatches.empty:
                df_mismatches.to_excel(writer, sheet_name="Field Mismatches", index=False)
            if not df_phone_diffs.empty:
                df_phone_diffs.to_excel(writer, sheet_name="Phone Discrepancies", index=False)
            if not df_missing_s2.empty:
                df_missing_s2.to_excel(writer, sheet_name=f"Missing in {l2}"[:31], index=False)
            if not df_missing_s1.empty:
                df_missing_s1.to_excel(writer, sheet_name=f"Missing in {l1}"[:31], index=False)

        excel_buffer.seek(0)
        return send_file(
            excel_buffer,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="speaker_comparison_report.xlsx"
        )
    except Exception as e:
        logger.exception("Error exporting to Excel")
        return jsonify({"error": str(e)}), 500


@app.route("/api/export-csv", methods=["POST"])
def export_csv():
    """Generates a downloadable CSV report of comparison results."""
    try:
        data = request.json or {}
        results = data.get("results", [])
        stats = data.get("stats", {})

        if not results:
            return jsonify({"error": "No data to export"}), 400

        l1 = stats.get("source1_label") or (results[0].get("source1_label") if results else "Source 1")
        l2 = stats.get("source2_label") or (results[0].get("source2_label") if results else "Source 2")

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Overall Status",
            f"Speaker Name ({l1})",
            f"Speaker Name ({l2})",
            f"Contact No. ({l1})",
            f"Contact No. ({l2})",
            "Contact Status",
            f"Company ({l1})",
            f"Company ({l2})",
            "Company Status",
            f"Talk Title ({l1})",
            f"Talk Title ({l2})",
            "Title Status",
            "Stage/Section",
            "Role",
            "Time",
            "Discrepancies"
        ])

        for r in results:
            writer.writerow([
                r.get("overall_status", ""),
                r.get("source1_speaker_name") or r.get("csv_speaker_name", ""),
                r.get("source2_speaker_name") or r.get("pdf_speaker_name", ""),
                r.get("source1_contact") or r.get("csv_contact", ""),
                r.get("source2_contact") or r.get("pdf_contact", ""),
                r.get("phone_status", ""),
                r.get("source1_company") or r.get("csv_company", ""),
                r.get("source2_company") or r.get("pdf_company", ""),
                r.get("comp_status", ""),
                r.get("source1_talk_title") or r.get("csv_talk_title", ""),
                r.get("source2_talk_title") or r.get("pdf_talk_title", ""),
                r.get("title_status", ""),
                r.get("section", ""),
                r.get("role", ""),
                r.get("time", ""),
                " | ".join(r.get("discrepancies", []))
            ])

        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=speaker_comparison_report.csv"}
        )
    except Exception as e:
        logger.exception("Error exporting to CSV")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5055))
    logger.info(f"Starting Speaker Comparison Server on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
