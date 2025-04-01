import os
from flask import Flask, request, jsonify, send_from_directory, render_template, url_for
from werkzeug.utils import secure_filename
import cv2
import numpy as np
import uuid
from flask_cors import CORS
import base64

# Initialize Flask app with CORS
app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)  # Enable CORS for all routes

# Configuration
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['RESULT_FOLDER'] = 'static/results'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'webp'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# Create folders if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULT_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def create_cartoon_effect(input_path, output_path):
    original_image = cv2.imread(input_path)
    if original_image is None:
        raise ValueError("Image not found")
    
    # Image processing steps...
    color_filtered = cv2.bilateralFilter(original_image, d=9, sigmaColor=75, sigmaSpace=75)
    gray = cv2.cvtColor(color_filtered, cv2.COLOR_BGR2GRAY)
    gray = cv2.medianBlur(gray, 7)
    edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, blockSize=9, C=2)
    color_cartoon = cv2.medianBlur(original_image, 7)
    edges_rgb = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    cartoon = cv2.bitwise_and(color_cartoon, edges_rgb)
    cv2.imwrite(output_path, cartoon)
    return cartoon

@app.route('/')
def index():
    # Permanent image configuration
    permanent_image = "profile2.jpg"
    image_path = os.path.join(app.config['RESULT_FOLDER'], permanent_image)
    
    # Verify image exists and get URL
    if os.path.exists(image_path):
        image_url = url_for('static', filename=f'results/{permanent_image}')
    else:
        image_url = None
        print(f"Warning: Permanent image not found at {image_path}")
    
    return render_template('index.html', 
                        permanent_image_url=image_url,
                        has_permanent_image=image_url is not None)


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part', 'status': 'error'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file', 'status': 'error'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed', 'status': 'error'}), 400
    
    try:
        # Save original file
        filename = f"{uuid.uuid4().hex[:10]}_{secure_filename(file.filename)}"
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(input_path)
        
        # Process image
        output_filename = f"cartoon_{filename}"
        output_path = os.path.join(app.config['RESULT_FOLDER'], output_filename)
        
        # Create cartoon effect
        cartoon = create_cartoon_effect(input_path, output_path)
        
        # Convert to base64 for immediate display
        _, buffer = cv2.imencode('.jpg', cartoon)
        cartoon_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return jsonify({
            'status': 'success',
            'original': f"/static/uploads/{filename}",
            'result': f"/static/results/{output_filename}",
            'preview': f"data:image/jpeg;base64,{cartoon_base64}"
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to process image: {str(e)}', 'status': 'error'}), 500

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    app.run(debug=True, port=5000)