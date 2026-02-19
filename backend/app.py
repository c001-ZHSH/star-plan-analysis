from flask import Flask, jsonify, request, send_file, render_template, send_from_directory
import threading
import uuid
import os
import time
import sys
import webbrowser
from star_scraper import StarPlanScraper

# Handle PyInstaller static path
if getattr(sys, 'frozen', False):
    template_folder = os.path.join(sys._MEIPASS, 'frontend')
    static_folder = os.path.join(sys._MEIPASS, 'frontend')
    app = Flask(__name__, static_folder=static_folder, static_url_path="")
else:
    app = Flask(__name__, static_folder="../frontend", static_url_path="")

# Route rewrite for PyInstaller
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

# Global state to store scraper status
# key: job_id, value: dict
jobs = {}

class ScraperThread(threading.Thread):
    def __init__(self, job_id, url, targets=None):
        super().__init__()
        self.job_id = job_id
        self.url = url
        self.targets = targets
        self.scraper = None

    def run(self):
        jobs[self.job_id] = {
            'status': 'starting',
            'progress': 0,
            'message': '初始化中...',
            'current': 0,
            'total': 0,
            'filename': None,
            'error': None
        }
        
        def progress_callback(current, total, message, phase="scanning"):
            # Update job status
            progress = 0
            if phase == "scanning":
                # Phase 1: Scanning universities (roughly 10% of work)
                progress = int((current / max(total, 1)) * 10)
            elif phase == "details":
                # Phase 2: Details (90% of work)
                progress = 10 + int((current / max(total, 1)) * 90)
            elif phase == "done":
                progress = 100
                
            jobs[self.job_id].update({
                'status': 'running',
                'progress': progress,
                'message': message,
                'current': current,
                'total': total
            })

        try:
            self.scraper = StarPlanScraper(self.url, progress_callback)
            self.scraper.run(target_universities=self.targets)
            
            # Save file
            filename = f"star_plan_analysis_{self.job_id}.xlsx"
            filepath = os.path.join(os.getcwd(), filename)
            self.scraper.save_to_excel(filepath)
            
            # Save preview data (first 10 rows)
            preview_data = self.scraper.results[:10] if self.scraper.results else []
            
            jobs[self.job_id].update({
                'status': 'completed',
                'progress': 100,
                'message': '分析完成！',
                'filename': filename,
                'preview_data': preview_data
            })
            
        except Exception as e:
            jobs[self.job_id].update({
                'status': 'error',
                'message': f'發生錯誤: {str(e)}',
                'error': str(e)
            })



@app.route('/api/fetch_universities', methods=['POST'])
def fetch_universities():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({'error': '請提供網址'}), 400
        
    try:
        # Use scraper just to get list
        scraper = StarPlanScraper(url)
        unis = scraper.get_universities()
        return jsonify({'universities': unis})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/start', methods=['POST'])
def start_scraper():
    data = request.json
    url = data.get('url')
    targets = data.get('targets') # List of names or None
    if not url:
        return jsonify({'error': '請提供網址'}), 400
        
    job_id = str(uuid.uuid4())
    thread = ScraperThread(job_id, url, targets)
    thread.start()
    
    return jsonify({'job_id': job_id})

@app.route('/api/status/<job_id>')
def get_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(job)

@app.route('/api/preview/<job_id>')
def get_preview(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    # Check if we can access the scraper instance
    # Ideally we should store results in the job dict or access the scraper
    # For simplicity, let's access the scraper if the thread is alive or finished
    # But thread might be gone.
    # Let's modify the ScraperThread to store results in the job dict upon completion
    # or expose the scraper results.
    
    # Actually, the scraper saves to file. We can read the file.
    # Or, we can modify the scraper to store the first N rows in the job dict.
    
    rows = job.get('preview_data', [])
    return jsonify({'preview': rows})

@app.route('/api/download/<job_id>')
def download_file(job_id):
    job = jobs.get(job_id)
    if not job or job['status'] != 'completed':
        return jsonify({'error': 'File not ready'}), 404
        
    path = os.path.join(os.getcwd(), job['filename'])
    return send_file(path, as_attachment=True, download_name='大學繁星校系分則分析.xlsx')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5002))
    
    def open_browser():
        time.sleep(1.5) # Wait for server to start
        webbrowser.open_new(f'http://localhost:{port}')

    print(f"Starting server on http://localhost:{port}")
    
    # Disable reloader if frozen to avoid PyInstaller issues
    use_reloader = not getattr(sys, 'frozen', False)
    
    # Only open browser if running as frozen executable (user convenience)
    # or if we want it in dev mode too. Let's do it for frozen mainly, 
    # but user asked for "local version", which implies the executable.
    # Determine if we are frozen
    is_frozen = getattr(sys, 'frozen', False)
    
    # Only open browser if running as frozen executable (user convenience)
    if is_frozen:
        threading.Thread(target=open_browser).start()
        
    # In frozen mode, debug must be False to avoid reloader/debugger issues
    # that cause restarts or weird behavior like auto-refreshing browser.
    app.run(host='0.0.0.0', port=port, debug=not is_frozen, use_reloader=not is_frozen)
