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

# Initialize MarkItDown in standard mode
md = MarkItDown()

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
        
        task_id = str(uuid.uuid4())
        temp_input_name = f"input_{task_id}{raw_ext}"
        temp_input_path = os.path.join(UPLOAD_FOLDER, temp_input_name)
        
        try:
            # Save incoming uploaded file physically to disk so parsers can access it
            file.save(temp_input_path)
            
            # Fetch human-readable original file size metric
            size_bytes = os.path.getsize(temp_input_path)
            size_kb = round(size_bytes / 1024, 1)
            input_size_str = f"{size_kb} KB" if size_kb > 0 else f"{size_bytes} B"
            
            markdown_content = ""
            
            # 1. OPTIMIZED OCR ENGINE FALLBACK FOR IMAGES
            if raw_ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
                try:
                    import easyocr
                    reader = easyocr.Reader(['en'], gpu=False)
                    bounds = reader.readtext(temp_input_path, detail=0)
                    if bounds:
                        markdown_content = f"# OCR Extracted Text from {filename}\n\n" + "\n\n".join(bounds)
                except Exception as img_err:
                    print(f"EasyOCR parsing processing trace log exception: {str(img_err)}")
            
            # 2. CORE MARKITDOWN PIPELINE (For Word Docs, PDFs, and standard file objects)
            if not markdown_content.strip():
                result = md.convert(temp_input_path)
                markdown_content = result.text_content or ""
                
            # 3. TEXT-BASED FORMAT FALLBACK GATEWAY (Plain text parsing fallback layouts)
            if not markdown_content.strip() and raw_ext in ['.txt', '.csv', '.json', '.xml', '.md']:
                with open(temp_input_path, 'r', encoding='utf-8', errors='ignore') as f:
                    markdown_content = f.read()
                    
            # 4. SAFETY FALLBACK GATE: If output string remains fundamentally blank
            if not markdown_content.strip():
                markdown_content = f"# {filename}\n\nThis structural format contains unreadable textual nodes or requires deeper system OCR configurations to interpret cleanly."
            
            # Save the processed markdown content cleanly to disk layout
            output_filename = f"{task_id}.md"
            output_filepath = os.path.join(OUTPUT_FOLDER, output_filename)
            md_display_name = os.path.splitext(filename)[0] + '.md'
            
            with open(output_filepath, "w", encoding="utf-8") as f:
                f.write(markdown_content)
                
            # Clean up the temporary input upload file to conserve host space
            if os.path.exists(temp_input_path):
                os.remove(temp_input_path)
                
            # REDIRECT FIXED: Route directly to the success visualization view page mapping
            return redirect(url_for('success', 
                                    uid=task_id, 
                                    out_name=md_display_name, 
                                    orig_name=filename, 
                                    orig_size=input_size_str))
            
        except Exception as e:
            print("Conversion Error Tracer Logging:")
            traceback.print_exc()
            flash(f"An error occurred during conversion processing layout: {str(e)}")
            if os.path.exists(temp_input_path):
                os.remove(temp_input_path)
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

        # Populates the explicit 'info' payload variable mapping structure required by success.html
        info_payload = {
            'original_name': original_name,
            'input_size': input_size_str,
            'output_size': output_size_str,
            'md_filename': md_filename,
            'uid': output_id 
        }
        
        return render_template('success.html', info=info_payload)
        
    except Exception as e:
        return f"Template processing initialization layout failure layout: {str(e)}", 500

@app.route('/download-file/<uid>/<filename>')
def download_file(uid, filename):
    return send_from_directory(
        OUTPUT_FOLDER, 
        f"{uid}.md", 
        as_attachment=True, 
        download_name=filename
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
