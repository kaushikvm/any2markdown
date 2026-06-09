import os
import uuid
import traceback
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
from werkzeug.utils import secure_filename
from markitdown import MarkItDown

app = Flask(__name__)
app.secret_key = "super_secret_conversion_key_12345"

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
        raw_ext = os.path.splitext(filename)[1].lower()
        ext_without_dot = raw_ext.lstrip('.')
        
        task_id = str(uuid.uuid4())
        temp_input_name = f"input_{task_id}{raw_ext}"
        temp_input_path = os.path.join(UPLOAD_FOLDER, temp_input_name)
        
        try:
            file.save(temp_input_path)
            
            size_bytes = os.path.getsize(temp_input_path)
            size_kb = round(size_bytes / 1024, 1)
            input_size_str = f"{size_kb} KB" if size_kb > 0 else f"{size_bytes} B"
            
            md_content = ""
            
            # OPTIMIZED IMAGE HANDLING FALLBACK
            if raw_ext in ['.png', '.jpg', '.jpeg']:
                try:
                    import easyocr
                    # Initialize the reader (English text processing)
                    reader = easyocr.Reader(['en'], gpu=False)
                    bounds = reader.readtext(temp_input_path, detail=0)
                    
                    if bounds:
                        md_content = f"# Extracted Text from {filename}\n\n" + "\n\n".join(bounds)
                except Exception as img_err:
                    print(f"EasyOCR fallback failed: {str(img_err)}")
            
            # DEFAULT CORE PIPELINE (If not handled by image engine or if it returns blank)
            if not md_content.strip():
                md = MarkItDown()
                result = md.convert(temp_input_path)
                md_content = result.text_content or ''
            
            # TEXT SUB-FORMATS FALLBACK
            if not md_content.strip() and raw_ext in ['.txt', '.csv', '.json', '.xml', '.md']:
                with open(temp_input_path, 'r', encoding='utf-8', errors='ignore') as f:
                    md_content = f.read()
            
            # FINAL ACCIDENT SAFEGUARD: If it's still completely blank, make a note of it
            if not md_content.strip():
                md_content = f"# {filename}\n\nNo readable textual elements could be extracted from this asset format structure."
                
            md_filename = os.path.splitext(filename)[0] + '.md'
            output_path = os.path.join(OUTPUT_FOLDER, f"{task_id}.md")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
                
            if os.path.exists(temp_input_path):
                os.remove(temp_input_path)
                
            return redirect(url_for('success', 
                                    uid=task_id, 
                                    out_name=md_filename, 
                                    orig_name=filename, 
                                    orig_size=input_size_str))
            
        except Exception as e:
            print("--- MARKITDOWN CONVERSION CRASH TRACEBACK ---")
            traceback.print_exc()
            print("---------------------------------------------")
            
            if os.path.exists(temp_input_path):
                os.remove(temp_input_path)
                
            flash(f"Conversion failed: {str(e)}")
            return render_template('index.html')
            
    return render_template('index.html')

@app.route('/success')
def success():
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

        info_payload = {
            'original_name': original_name,
            'input_size': input_size_str,
            'output_size': output_size_str,
            'md_filename': md_filename,
            'uid': output_id 
        }
        
        return render_template('success.html', info=info_payload)
        
    except Exception as e:
        return f"Template initialization failed: {str(e)}", 500

@app.route('/download-file/<uid>/<filename>')
def download_file(uid, filename):
    return send_from_directory(
        OUTPUT_FOLDER, 
        f"{uid}.md", 
        as_attachment=True, 
        download_name=filename
    )
