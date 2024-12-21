from flask import Flask, request, jsonify, render_template, current_app
import tensorflow as tf
from PIL import Image
import numpy as np
import io
import logging

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max-limit

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Allowed extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_model():
    if not hasattr(current_app, 'model'):
        try:
            current_app.model = tf.keras.models.load_model("model/model.keras")
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Model loading error: {str(e)}")
            raise
    return current_app.model

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    try:
        # File validations
        if 'file' not in request.files:
            return jsonify({'error': 'Please select a file to upload'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'Please upload only JPG or PNG images'}), 400

        # Process image with error handling
        try:
            image_bytes = file.read()
            img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        except Exception as e:
            logger.error(f"Image processing error: {str(e)}")
            return jsonify({'error': 'Unable to process the image. Please try another image.'}), 400

        # Image preprocessing
        try:
            img = img.resize((128, 128))
            img_array = np.array(img) / 255.0
            input_array = np.expand_dims(img_array, axis=0)
        except Exception as e:
            logger.error(f"Preprocessing error: {str(e)}")
            return jsonify({'error': 'Error preparing image for analysis'}), 500

        # Make prediction with cached model
        model = load_model()
        prediction = model.predict(input_array)
        
        # Results with better confidence handling
        confidence = float(prediction[0][0])
        if confidence > 0.5:
            result = 'Healthy'
            confidence_percent = round(confidence * 100, 2)
        else:
            result = 'Diseased'
            confidence_percent = round((1 - confidence) * 100, 2)

        return jsonify({
            'prediction': result,
            'confidence': confidence_percent,
            'details': {
                'raw_confidence': confidence,            }
        })
        
    except Exception as e:
        logger.error(f"Prediction error: {str(e)}")
        return jsonify({
            'error': 'An error occurred during analysis',
            'details': str(e) if app.debug else None
        }), 500

if __name__ == '__main__': 
    app.run(debug=True)
