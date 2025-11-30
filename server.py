from flask import Flask, request, send_file, jsonify, send_from_directory
import os
from xhtml2pdf import pisa
import io

app = Flask(__name__, static_folder='dist')

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

# Serve React App
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug_mode, port=5001)
