import os
import uuid
import io
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
from werkzeug.utils import secure_filename
from markitdown import MarkItDown

app = Flask(__name__)
# Keep secret key for essential flash message signaling
app.secret_key = "super_secret_conversion_key_12345"

# Setup local storage paths securely on PythonAnywhere disk space
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
OUTPUT_FOLDER = os.path.join(os.path.dirname(__file__), 'outputs')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected.')
            return render_template('index.html')
            
        file = request.files['file']
        if file.filename == '':
            flash('No file selected.')
            return render_template('index.html')
            
        filename = secure_filename(file.filename)
        ext = os.path.splitext(filename)[1].lower()
        
        try:
            # Read file data directly into an in-memory byte buffer stream
            file_bytes = file.read()
            file_stream = io.BytesIO(file_bytes)
            
            # Formulate original size display metric string
            size_kb = round(len(file_bytes) / 1024, 1)
            input_size_str = f"{size_kb} KB" if size_kb > 0 else f"{len(file_bytes)} B"
            
            # Initialize MarkItDown and convert directly from memory stream buffer
            md = MarkItDown()
            result = md.convert_stream(file_stream, file_extension=ext)
            md_content = result.text_content or ''
            
            # Fallback block: if markitdown returns an empty string for plain text structures, read raw bytes
            if not md_content.strip() and ext in ['.txt', '.csv', '.json', '.xml', '.md']:
                md_content = file_bytes.decode('utf-8', errors='ignore')
                
            md_filename = os.path.splitext(filename)[0] + '.md'
            
            # Generate unique server tracking file identifier
            output_id = str(uuid.uuid4())
            output_path = os.path.join(OUTPUT_FOLDER, f"{output_id}.md")
            
            # Write markdown asset securely to local disk storage
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
                
            # VETERAN FIX: Pass metrics safely via URL parameters instead of breaking the session cookie limit
            return redirect(url_for('success', 
                                    uid=output_id, 
                                    out_name=md_filename, 
                                    orig_name=filename, 
                                    orig_size=input_size_str))
            
        except Exception as e:
            flash(f"Conversion failed: {str(e)}")
            return render_template('index.html')
            
    return render_template('index.html')

@app.route('/success')
def success():
    # Gather parameters out of the secure URL query string mapping
    output_id = request.args.get('uid')
    md_filename = request.args.get('out_name', 'converted.md')
    original_name = request.args.get('orig_name', 'Document')
    input_size_str = request.args.get('orig_size', 'Processed')
    
    if not output_id:
        return redirect(url_for('index'))
        
    try:
        output_path = os.path.join(OUTPUT_FOLDER, f"{output_id}.md")
        
        if os.path.exists(output_path):
            size_bytes = os.path.getsize(output_path)
            if size_bytes < 1024:
                output_size_str = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                output_size_str = f"{round(size_bytes / 1024, 1)} KB"
            else:
                output_size_str = f"{round(size_bytes / (1024 * 1024), 1)} MB"
        else:
            output_size_str = "0 B"

        # Populates the explicit 'info' structure variable expected by success.html
        info_payload = {
            'original_name': original_name,
            'input_size': input_size_str,
            'output_size': output_size_str,
            'md_filename': md_filename,
            'uid': output_id  # Passed forward for the JavaScript automatic download trigger
        }
        
        return render_template('success.html', info=info_payload)
        
    except Exception as e:
        return f"Template initialization failed: {str(e)}", 500

@app.route('/download-file/<uid>/<filename>')
def download_file(uid, filename):
    # Verify file existence directly inside output directory layout securely via route parameters
    return send_from_directory(
        OUTPUT_FOLDER, 
        f"{uid}.md", 
        as_attachment=True, 
        download_name=filename
    )