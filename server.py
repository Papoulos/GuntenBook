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

    # --- 1. Suppression fiable du HEADER Gutenberg ---
    start_marker_text = r'\*\*\*\s*START OF (THE|THIS)?\s*PROJECT GUTENBERG EBOOK'
    start_marker = soup.find(string=lambda t: t and re.search(start_marker_text, t, re.IGNORECASE | re.DOTALL))

    if start_marker:
        element_to_delete = start_marker.parent
        while element_to_delete.parent != soup.body and element_to_delete.parent is not None:
            element_to_delete = element_to_delete.parent
        for sibling in list(element_to_delete.find_previous_siblings()):
            sibling.decompose()
        element_to_delete.decompose()

    # --- 2. Suppression fiable du FOOTER Gutenberg ---
    end_marker_text = r'\*\*\*\s*END OF (THE|THIS)?\s*PROJECT GUTENBERG EBOOK.*'
    end_marker = soup.find(string=lambda t: t and re.search(end_marker_text, t, re.IGNORECASE | re.DOTALL))

    if end_marker:
        element_to_delete = end_marker.parent
        while element_to_delete.parent != soup.body and element_to_delete.parent is not None:
            element_to_delete = element_to_delete.parent
        for sibling in list(element_to_delete.find_next_siblings()):
            sibling.decompose()
        element_to_delete.decompose()

    # --- 3. Si le body est vide maintenant, on crée un body minimal ---
    if not soup.body or not soup.body.contents:
        soup.body = soup.new_tag('body')

    # --- 4. Détection des chapitres pour les sauts de page (amélioré avec plus de variantes) ---
    chapter_pattern = re.compile(
        r'^\s*'
        r'(?:Chapitre|Livre|Partie|Lettre|Préface|Introduction|Conclusion|Chapitre premier|Chapitre dernier|Prologue|Épilogue)'
        r'(?:\s+[IVXLCDM\d]+)?[\s\.:-]*$'
        r'|'
        r'^\s*M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})[\s\.:-]*$',
        re.IGNORECASE
    )

    # --- Nouvelle étape : Suppression de tout avant le premier chapitre ou préface ---
    first_content_element = None
    for header in soup.body.find_all(['h1', 'h2', 'h3']):
        text = header.get_text(strip=True)
        if chapter_pattern.match(text):
            first_content_element = header
            break

    if first_content_element:
        element_to_keep = first_content_element
        while element_to_keep.parent != soup.body and element_to_keep.parent is not None:
            element_to_keep = element_to_keep.parent
        for sibling in list(element_to_keep.find_previous_siblings()):
            sibling.decompose()

    # --- 5. Création du nouveau body propre ---
    new_body = soup.new_tag('body')

    # --- 6. Page de titre ---
    if title:
        title_page = soup.new_tag('div', **{'class': 'title-page'})
        h1 = soup.new_tag('h1')
        h1.string = title
        title_page.append(h1)
        if author:
            p_author = soup.new_tag('p', **{'class': 'author'})
            p_author.string = author
            title_page.append(p_author)
        new_body.append(title_page)
        new_body.append(soup.new_tag('div', **{'class': 'blank-page'}))

    # --- 7. Ajout du contenu nettoyé + marquage des chapitres ---
    is_first_chapter = True
    for element in list(soup.body.children):  # list() pour éviter modifications pendant itération
        if isinstance(element, Tag) and element.name in ['h1', 'h2', 'h3']:
            text = element.get_text(strip=True)
            if chapter_pattern.match(text):
                if not is_first_chapter:
                    element['class'] = element.get('class', []) + ['section-break']
                else:
                    is_first_chapter = False
        if isinstance(element, Tag):
            new_body.append(element)
        elif isinstance(element, NavigableString) and element.strip():
            new_body.append(element)

    # --- 8. Remplacement du body ---
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

        css_string = css_string = """
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
        height: 170mm; /* A5 height 210mm minus 2cm top + 2cm bottom margins */
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
