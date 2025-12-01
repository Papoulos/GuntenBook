from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import io
import os
import re
from weasyprint import HTML, CSS
from bs4 import BeautifulSoup, NavigableString, Tag

app = Flask(__name__)

# Configure CORS
frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
CORS(app, resources={r"/api/*": {"origins": frontend_url}})

def clean_gutenberg_html(html_content, title=None, author=None):
    soup = BeautifulSoup(html_content, 'html.parser')

    chapter_pattern = re.compile(
        r'^\s*'
        r'(?:Chapitre|Livre|Partie|Lettre|Préface|Introduction|Conclusion)'
        r'(?:\s+[IVXLCDM\d]+)?\s*\.?\s*$'
        r'|'
        r'^\s*M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})\.?\s*$',
        re.IGNORECASE
    )

    if soup.body:
        # 1. Remove Gutenberg Footer
        end_marker_text = '*** END OF THE PROJECT GUTENBERG EBOOK'
        end_marker = soup.find(string=lambda text: text and end_marker_text in text)

        if end_marker:
            element_to_delete = end_marker.find_parent()
            if element_to_delete:
                for element in list(element_to_delete.find_all_next()):
                    element.decompose()
                element_to_delete.decompose()

        # 2. Remove Gutenberg Header
        first_content_element = None
        for header in soup.body.find_all(['h1', 'h2', 'h3']):
            if chapter_pattern.match(header.get_text(strip=True)):
                first_content_element = header
                break

        if first_content_element:
            for element in list(first_content_element.find_previous_siblings()):
                element.extract()

    # 3. Create New Body for PDF structure
    new_body = soup.new_tag('body')

    # 4. Add Title Page (if a title was provided)
    if title:
        title_page = soup.new_tag('div', **{'class': 'title-page'})
        title_tag = soup.new_tag('h1')
        title_tag.string = title
        title_page.append(title_tag)

        if author:
            author_tag = soup.new_tag('p', **{'class': 'author'})
            author_tag.string = author
            title_page.append(author_tag)

        new_body.append(title_page)
        new_body.append(soup.new_tag('div', **{'class': 'blank-page'}))

    # 5. Process content and identify chapters
    if soup.body:
        headers = soup.body.find_all(['h1', 'h2', 'h3'])
        is_first_chapter = True
        for header in headers:
            if chapter_pattern.match(header.get_text(strip=True)):
                if is_first_chapter:
                    is_first_chapter = False  # Skip adding class to the first chapter
                else:
                    header['class'] = header.get('class', []) + ['section-break']
        
        new_body.extend(list(soup.body.contents))

    # 6. Replace Old Body
    if soup.body:
        soup.body.replace_with(new_body)
    else:
        soup.append(new_body)

    return str(soup)


@app.route('/api/convert', methods=['POST'])
def convert_to_pdf():
    # Limit the size of the incoming request
    if request.content_length > 10 * 1024 * 1024:  # 10 MB limit
        return jsonify({"error": "Request payload is too large."}), 413

    if not request.is_json:
        return jsonify({"error": "Unsupported Media Type. Must be application/json."}), 415

    try:
        data = request.get_json()
        html_content = data.get('html_content')
        title = data.get('title')
        author = data.get('author')

        if not html_content:
            return jsonify({"error": "html_content is required."}), 400

        cleaned_html = clean_gutenberg_html(html_content, title, author)

        css_string = """
            @page {
                size: A5;
                margin: 2cm;
                @bottom-center {
                    content: counter(page);
                }
            }
            /* No page number on the first page (Title Page) */
            @page :first {
                @bottom-center {
                    content: none;
                }
            }
            
            body {
                font-size: 10pt;
                font-family: serif;
                line-height: 1.5;
            }

            /* Title Page Styling */
            .title-page {
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                height: 100vh;
                text-align: center;
                page-break-after: always;
            }
            
            .title-page h1 {
                margin-bottom: 1em;
                font-size: 2em;
            }
            
            .title-page .author {
                font-size: 1.5em;
                font-style: italic;
            }

            /* Blank Page Styling */
            .blank-page {
                page-break-after: always;
                content: "";
                display: block;
                height: 1px; /* Minimal height to ensure it renders */
            }

            /* Section Breaks */
            .section-break {
                page-break-before: always;
            }
            
            /* Ensure h1 always breaks page (except on title page, handled by structure) */
            h1 {
                page-break-before: always;
            }
            
            /* Override for title page h1 to avoid double break if logic fails */
            .title-page h1 {
                page-break-before: avoid;
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
