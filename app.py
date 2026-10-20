from flask import Flask, render_template, request, jsonify
from flask import send_from_directory, abort
from pathlib import Path
from werkzeug.utils import secure_filename
import uuid
import threading
import traceback
import validator

app = Flask(__name__)
RESULTS_DIR = Path("results").resolve()

app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@app.route("/")
def home():
    return render_template("index.html")

jobs = {}
jobs_lock = threading.Lock()

def process_text_file(job_id, input_file):
    try:
        with jobs_lock:
            jobs[job_id] = {"status": "Running", "message": "Checker is processing your file..."}

        # Create a results folder for this specific job id
        job_results_dir = RESULTS_DIR / job_id
        job_results_dir.mkdir(parents=True, exist_ok=True)
        output_file = job_results_dir / "results.txt"

        # --- INTEGRATE CHECKER HERE ---
        # Option A: If checker.py has a function like run_checker(input_path, output_path)
        # checker.run_checker(str(input_file), str(output_file))
        
        # Option B: If checker.py reads "input.txt" and writes "results.txt" directly in its directory,
        # you can adapt it or call its core function here. 
        # For example, if it returns text data:
        # checked_data = checker.process_data(input_file.read_text(encoding="utf-8", errors="replace"))
        # output_file.write_text(checked_data, encoding="utf-8")
        
        # Placeholder fallback if checker.py uses standard file paths:
        # (Replace this line with your actual checker function call)
        validator.run(str(input_file), str(output_file)) 
        # ------------------------------

        # Read results to count lines or give stats back to website
        if output_file.is_file():
            output_text = output_file.read_text(encoding="utf-8", errors="replace")
            line_count = len(output_text.splitlines())
        else:
            line_count = 0

        with jobs_lock:
            jobs[job_id] = {
                "status": "Completed",
                "message": "Processing completed successfully",
                "line_count": line_count,
                "download_url": f"/results/{job_id}/results.txt"
            }

    except Exception as e:
        traceback.print_exc()
        with jobs_lock:
            jobs[job_id] = {
                "status": "Error",
                "message": f"Processing failed: {str(e)}"
            }


@app.route("/start/<job_id>", methods=["POST"])
def start_job(job_id):
    job_dir = (UPLOAD_DIR / job_id).resolve()
    input_file = job_dir / "input.txt"

    if job_dir.parent != UPLOAD_DIR.resolve() or not input_file.is_file():  
        return jsonify({"error": "Uploaded file not found"}), 404  

    with jobs_lock:  
        if job_id in jobs and jobs[job_id]["status"] == "Running":  
            return jsonify({"error": "Job is already running"}), 409  

        jobs[job_id] = {"status": "Queued", "message": "Job queued"}  

    thread = threading.Thread(  
        target=process_text_file,  
        args=(job_id, input_file),  
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

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("file")

    if not file or not file.filename:  
        return jsonify({"error": "Please select a file"}), 400  

    if Path(file.filename).suffix.lower() != ".txt":  
        return jsonify({"error": "Only TXT files are allowed"}), 400  

    job_id = uuid.uuid4().hex  
    job_dir = UPLOAD_DIR / job_id  
    job_dir.mkdir(parents=True, exist_ok=True)  

    saved_file = job_dir / "input.txt"  
    file.save(saved_file)  

    return jsonify({  
        "status": "uploaded",  
        "message": "File uploaded successfully",  
        "job_id": job_id  
    })

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

@app.route("/results")
def list_results():
    folders = []

    if RESULTS_DIR.exists():  
        for folder in sorted(RESULTS_DIR.iterdir()):  
            if not folder.is_dir():  
                continue  

            files = []  

            for item in sorted(folder.iterdir()):  
                if item.is_file() and item.suffix.lower() == ".txt":  
                    files.append({  
                        "name": item.name,  
                        "size": item.stat().st_size  
                    })  

            folders.append({  
                "name": folder.name,  
                "files": files  
            })  

    return jsonify({"folders": folders})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
