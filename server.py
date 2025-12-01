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

    # 1. Create New Body
    new_body = soup.new_tag('body')
    
    # 3. Add Title Page (if a title was provided)
    if title:
        title_page = soup.new_tag('div', **{'class': 'title-page'})

        # Create and add the title tag
        title_tag = soup.new_tag('h1')
        title_tag.string = title
        title_page.append(title_tag)

        # Create and add the author tag if an author is provided
        if author:
            author_tag = soup.new_tag('p', **{'class': 'author'})
            author_tag.string = author
            title_page.append(author_tag)

        new_body.append(title_page)

        # 4. Add a blank page after the title page
        blank_page = soup.new_tag('div', **{'class': 'blank-page'})
        new_body.append(blank_page)

    # 5. Extract Preface and Chapters
    # We scan the original body for headers matching our criteria
    # and append them + their content to the new body.
    
    # Find all potential section headers and process them hierarchically
    headers = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    processed_elements = set()

    for header in headers:
        if header in processed_elements:
            continue

        # This header starts a new section
        try:
            current_level = int(header.name[1])
        except (ValueError, IndexError):
            current_level = 6  # Fallback

        header['class'] = header.get('class', []) + ['section-break']
        
        # Append the header itself
        new_body.append(header)
        processed_elements.add(header)

        # Append all subsequent siblings until the next section header
        for sibling in header.find_next_siblings():
            if sibling in processed_elements:
                continue

            # Check if we've hit a new section of equal or higher importance
            if isinstance(sibling, Tag) and sibling.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                try:
                    sibling_level = int(sibling.name[1])
                    if sibling_level <= current_level:
                        break  # End of the current section
                except (ValueError, IndexError):
                    pass

            new_body.append(sibling)
            processed_elements.add(sibling)

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
