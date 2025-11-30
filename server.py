from flask import Flask, request, send_file, jsonify, send_from_directory
import os
import requests
from xhtml2pdf import pisa
import io

app = Flask(__name__, static_folder='dist')

@app.route('/api/convert', methods=['POST'])
def convert_to_pdf():
    try:
        data = request.get_json()
        html_url = data.get('url')

        if not html_url:
            return jsonify({"error": "URL is required."}), 400

        # Télécharger le contenu HTML
        response = requests.get(html_url)
        response.raise_for_status()  # Lève une exception pour les codes d'erreur HTTP
        html_content = response.content

        # Convertir en PDF
        pdf_file = io.BytesIO()
        pisa_status = pisa.CreatePDF(io.BytesIO(html_content), dest=pdf_file)

        if pisa_status.err:
            raise Exception(f"PDF creation error: {pisa_status.err}")

        pdf_file.seek(0)

        return send_file(
            pdf_file,
            as_attachment=True,
            download_name='document.pdf',
            mimetype='application/pdf'
        )

    except requests.exceptions.RequestException as e:
        app.logger.error(f"Failed to download HTML: {e}")
        return jsonify({"error": "Failed to download the HTML content from the provided URL."}), 500
    except Exception as e:
        app.logger.error(f"PDF conversion failed: {e}")
        return jsonify({"error": "An error occurred during PDF conversion."}), 500

# Serve React App
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug_mode, port=5001)
