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
            # Save incoming uploaded file
            file.save(temp_input_path)
            
            # Convert the document using MarkItDown
            result = md.convert(temp_input_path)
            markdown_content = result.text_content
            
            # Save the converted file to output
            output_filename = f"converted_{task_id}.md"
            output_filepath = os.path.join(OUTPUT_FOLDER, output_filename)
            
            with open(output_filepath, "w", encoding="utf-8") as f:
                f.write(markdown_content)
                
            # Clean up the original uploaded file to save memory/space
            if os.path.exists(temp_input_path):
                os.remove(temp_input_path)
                
            return redirect(url_for('success', filename=output_filename))
            
        except Exception as e:
            print("Conversion Error Error:")
            traceback.print_exc()
            flash(f"An error occurred during conversion: {str(e)}")
            if os.path.exists(temp_input_path):
                os.remove(temp_input_path)
            return render_template('index.html')
            
    return render_template('index.html')

@app.route('/success/<filename>')
def success(filename):
    return render_template('success.html', filename=filename)

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
