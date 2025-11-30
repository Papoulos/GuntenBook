from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import io
import os
from xhtml2pdf import pisa

app = Flask(__name__)

# Configure CORS
frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3001')
CORS(app, resources={r"/api/*": {"origins": frontend_url}})


@app.route('/api/convert', methods=['POST'])
def convert_to_pdf():
    # Limit the size of the incoming request
    if request.content_length > 10 * 1024 * 1024:  # 10 MB limit
        return jsonify({"error": "Request payload is too large."}), 413

    try:
        html_content = request.data

        pdf_file = io.BytesIO()
        pisa_status = pisa.CreatePDF(io.BytesIO(html_content), dest=pdf_file)

        if pisa_status.err:
            raise Exception("PDF creation error")

        pdf_file.seek(0)

        return send_file(
            pdf_file,
            as_attachment=True,
            download_name='document.pdf',
            mimetype='application/pdf'
        )

    except Exception as e:
        # Log the exception for debugging purposes
        app.logger.error(f"PDF conversion failed: {e}")
        # Return a generic error message to the user
        return jsonify({"error": "An error occurred during PDF conversion."}), 500

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug_mode, port=5001)
