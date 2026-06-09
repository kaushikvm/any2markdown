import os
import uuid
import traceback
import pytesseract
from PIL import Image
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
from werkzeug.utils import secure_filename
from markitdown import MarkItDown

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallback-dev-key-change-in-production")
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB upload limit

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
OUTPUT_FOLDER = os.path.join(os.path.dirname(__file__), 'outputs')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.txt', '.json', '.xml', '.md'}

# Initialize MarkItDown in standard mode for PDFs and Docs
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

        # File extension allowlist check
        if raw_ext not in ALLOWED_EXTENSIONS:
            flash(f'Unsupported file type: {raw_ext}. Please upload a PDF, Word document, image, or text file.')
            return render_template('index.html')

        # SPREADSHEET ISOLATION GATEWAY
        if raw_ext in ['.xlsx', '.xls', '.csv']:
            flash('Excel/Spreadsheet conversion is temporarily disabled. Please upload a PDF, Word document, or image.')
            return render_template('index.html')

        task_id = str(uuid.uuid4())
        temp_input_name = f"input_{task_id}{raw_ext}"
        temp_input_path = os.path.join(UPLOAD_FOLDER, temp_input_name)

        try:
            # Save incoming uploaded file physically to disk
            file.save(temp_input_path)

            # Fetch file size details
            size_bytes = os.path.getsize(temp_input_path)
            size_kb = round(size_bytes / 1024, 1)
            input_size_str = f"{size_kb} KB" if size_kb > 0 else f"{size_bytes} B"

            markdown_content = ""

            # 1. LIGHTWEIGHT OCR ENGINE FOR IMAGES (PNG, JPG, JPEG, TIFF, BMP)
            if raw_ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
                try:
                    img = Image.open(temp_input_path)
                    extracted_text = pytesseract.image_to_string(img)

                    if extracted_text.strip():
                        markdown_content = f"# OCR Extracted Text from {filename}\n\n" + extracted_text
                except Exception as img_err:
                    print(f"System Tesseract OCR failed: {str(img_err)}")

            # 2. CORE PIPELINE FOR DOCUMENTS (Word Docs & PDFs)
            if not markdown_content.strip():
                result = md.convert(temp_input_path)
                markdown_content = getattr(result, 'text_content', None) or ""

            # 3. TEXT-BASED FORMAT FALLBACK
            if not markdown_content.strip() and raw_ext in ['.txt', '.json', '.xml', '.md']:
                with open(temp_input_path, 'r', encoding='utf-8', errors='ignore') as f:
                    markdown_content = f.read()

            # 4. BLANK PROTECTION GATE
            if not markdown_content.strip():
                markdown_content = f"# {filename}\n\nNo readable textual elements could be extracted from this file."

            # Save processed Markdown to file system
            output_filename = f"{task_id}.md"
            output_filepath = os.path.join(OUTPUT_FOLDER, output_filename)
            md_display_name = os.path.splitext(filename)[0] + '.md'

            with open(output_filepath, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            if os.path.exists(temp_input_path):
                os.remove(temp_input_path)

            return redirect(url_for('success',
                                    uid=task_id,
                                    out_name=md_display_name,
                                    orig_name=filename,
                                    orig_size=input_size_str))

        except Exception as e:
            print("Conversion Error:")
            traceback.print_exc()
            flash(f"An error occurred during conversion: {str(e)}")
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

        info_payload = {
            'original_name': original_name,
            'input_size': input_size_str,
            'output_size': output_size_str,
            'md_filename': md_filename,
            'uid': output_id
        }
        return render_template('success.html', info=info_payload)
    except Exception as e:
        return f"Template initialization failure: {str(e)}", 500

@app.route('/download-file/<uid>/<filename>')
def download_file(uid, filename):
    return send_from_directory(OUTPUT_FOLDER, f"{uid}.md", as_attachment=True, download_name=filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)