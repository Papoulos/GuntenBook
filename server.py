from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import io
import os
from itertools import takewhile
from weasyprint import HTML, CSS
from bs4 import BeautifulSoup

app = Flask(__name__)

# Configure CORS
frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
CORS(app, resources={r"/api/*": {"origins": frontend_url}})

def clean_gutenberg_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')

    start_marker = soup.find(string=lambda t: "*** START OF THE PROJECT GUTENBERG EBOOK" in t)
    end_marker = soup.find(string=lambda t: "*** END OF THE PROJECT GUTENBERG EBOOK" in t)

    # Fallback for when markers are not found
    if not start_marker or not end_marker:
        for tag in soup(['script', 'style']):
            tag.decompose()
        title_tag = soup.find('h1')
        if title_tag:
            title_tag.wrap(soup.new_tag('div', **{'class': 'title-page'}))
        return str(soup)

    # More robustly extract content between markers
    content_iterator = start_marker.find_all_next()
    book_content_tags = takewhile(lambda t: t != end_marker, content_iterator)

    # Create a new document with only the book content
    new_soup = BeautifulSoup('<!DOCTYPE html><html><body></body></html>', 'html.parser')
    body = new_soup.body
    for tag in book_content_tags:
        # The iterator yields NavigableStrings and Tags, so handle both
        body.append(tag.extract())

    # Perform final cleanup on the new document
    for tag in body(['script', 'style']):
        tag.decompose()

    title_tag = body.find('h1')
    if title_tag:
        title_tag.wrap(new_soup.new_tag('div', **{'class': 'title-page'}))

    return str(new_soup)


@app.route('/api/convert', methods=['POST'])
def convert_to_pdf():
    # Limit the size of the incoming request
    if request.content_length > 10 * 1024 * 1024:  # 10 MB limit
        return jsonify({"error": "Request payload is too large."}), 413

    try:
        html_content = request.data.decode('utf-8')

        cleaned_html = clean_gutenberg_html(html_content)

        css_string = """
            @page {
                size: A5;
                margin: 2cm;
                @bottom-center {
                    content: counter(page);
                }
            }
            h1 {
                page-break-before: always;
            }
            .title-page h1 {
                page-break-before: avoid;
            }
            .title-page {
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                height: 100vh;
                text-align: center;
            }
            body {
                font-size: 12pt;
            }
        """

        pdf_file = io.BytesIO()
        HTML(string=cleaned_html).write_pdf(pdf_file, stylesheets=[CSS(string=css_string)])
        pdf_file.seek(0)

        return send_file(
            pdf_file,
            as_attachment=True,
            attachment_filename='document.pdf',
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
