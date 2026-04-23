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

def clean_gutenberg_html(html_content, title=None, author=None, illustration_mode='none', illustration_count=0):
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

    # --- 2.5 Langue française pour les césures ---
    if soup.html:
        soup.html['lang'] = 'fr'

    # --- 3. Si le body est vide maintenant, on s'assure qu'il existe et contient le contenu ---
    if not soup.body:
        new_body = soup.new_tag('body')
        if soup.html:
            for child in list(soup.html.contents):
                new_body.append(child.extract())
            soup.html.append(new_body)
        else:
            for child in list(soup.contents):
                new_body.append(child.extract())
            soup.append(new_body)

    # --- 4. Détection des chapitres pour les sauts de page (amélioré avec plus de variantes) ---
    # Matches various section starts for page breaks.
    section_pattern = re.compile(
        r'^\s*'
        r'(?:Chapitre|Livre|Partie|Lettre|Préface|Introduction|Conclusion|Chapitre premier|Chapitre dernier|Prologue|Épilogue)'
        r'\b'
        r'|'
        r'^\s*(?=[MDCLXVI])M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})\b',
        re.IGNORECASE
    )
    # Matches only "Chapitre..." for illustrations.
    illustration_pattern = re.compile(r'^\s*Chapitre\b', re.IGNORECASE)

    # --- Nouvelle étape : Suppression de tout avant le premier chapitre ou préface ---
    first_content_element = None
    for header in soup.body.find_all(['h1', 'h2', 'h3']):
        text = header.get_text(strip=True)
        if section_pattern.match(text):
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
        # On ne met plus de blank-page ici car la gestion gauche/droite va s'en charger

    # --- 7. Ajout du contenu nettoyé + marquage des chapitres ---
    content_elements = []
    for element in list(soup.body.children):
        if isinstance(element, Tag):
            content_elements.append(element)
        elif isinstance(element, NavigableString) and element.strip():
            content_elements.append(element)

    # Gestion des illustrations en mode fixe
    illustration_positions = []
    if illustration_mode == 'fixed' and illustration_count > 0:
        def get_text_len(e):
            if isinstance(e, Tag):
                return len(e.get_text())
            return len(str(e))

        # Estimation : 10 pages ~= 25000 caractères
        limit = 25000

        start_idx = 0
        current_chars = 0
        for i, e in enumerate(content_elements):
            current_chars += get_text_len(e)
            if current_chars > limit:
                start_idx = i
                break

        end_idx = len(content_elements)
        current_chars = 0
        for i, e in enumerate(reversed(content_elements)):
            current_chars += get_text_len(e)
            if current_chars > limit:
                end_idx = len(content_elements) - i
                break

        if end_idx > start_idx and illustration_count > 0:
            step = (end_idx - start_idx) // (illustration_count + 1)
            if step > 0:
                for i in range(1, illustration_count + 1):
                    illustration_positions.append(start_idx + i * step)

    is_first_chapter = True
    for i, element in enumerate(content_elements):
        # Insertion illustration mode fixe
        if i in illustration_positions:
            ill_div = soup.new_tag('div', **{'class': 'illustration-page'})
            ill_div.string = "ILLUSTRATION"
            new_body.append(ill_div)

        target_header = None
        if isinstance(element, Tag):
            if element.name in ['h1', 'h2', 'h3']:
                target_header = element
            else:
                # Search for a header within the tag (handles nested chapters)
                target_header = element.find(['h1', 'h2', 'h3'])

        if target_header:
            text = target_header.get_text(strip=True)
            if section_pattern.match(text):
                if illustration_mode == 'chapter' and illustration_pattern.match(text):
                    ill_div = soup.new_tag('div', **{'class': 'illustration-page'})
                    ill_div.string = "ILLUSTRATION"
                    new_body.append(ill_div)

                if not is_first_chapter:
                    element['class'] = element.get('class', []) + ['section-break']
                else:
                    is_first_chapter = False
                    element['class'] = element.get('class', []) + ['first-chapter']

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
        illustration_mode = data.get('illustration_mode', 'none')
        illustration_count = int(data.get('illustration_count', 0))

        if not html_content:
            return jsonify({"error": "html_content is required."}), 400

        cleaned_html = clean_gutenberg_html(html_content, title, author, illustration_mode, illustration_count)

        css_string = """
    @import url('https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;0,700;0,800;1,400;1,500;1,600;1,700;1,800&display=swap');

    @page {
        size: A5;
        margin-top: 20mm;
        margin-bottom: 20mm;
        @bottom-center {
            content: counter(page);
            font-family: 'EB Garamond', serif;
            font-size: 10pt;
        }
    }

    @page :left {
        margin-left: 15mm;
        margin-right: 25mm;
    }

    @page :right {
        margin-left: 25mm;
        margin-right: 15mm;
    }

    /* No page number on the first page (Title Page) */
    @page :first {
        @bottom-center {
            content: none;
        }
    }

    /* No page number on illustration pages (always even/left) */
    @page illustration {
        @bottom-center {
            content: none;
        }
    }

    .illustration-page {
        page: illustration;
        break-before: left;
        display: flex;
        align-items: center;
        justify-content: center;
        height: 100%;
        font-size: 2em;
        color: #ccc;
        text-transform: uppercase;
        letter-spacing: 0.2em;
    }

    body {
        font-size: 11pt;
        font-family: 'EB Garamond', serif;
        line-height: 1.35;
        text-rendering: optimizeLegibility;
    }

    p {
        margin: 0;
        text-indent: 5mm;
        text-align: justify;
        hyphens: auto;
    }

    /* First paragraph after a title has no indent */
    h1 + p, h2 + p, h3 + p, .section-break + p, .first-chapter + p, .title-page + p {
        text-indent: 0;
    }

    /* Title Page Styling */
    .title-page {
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        height: 100%;
        text-align: center;
        break-after: right; /* Title page is recto (p. 1), forces a blank verso (p. 2) so next starts on p. 3 */
    }

    .title-page h1 {
        margin-bottom: 1em;
        font-size: 2.5em;
        text-indent: 0;
    }

    .title-page .author {
        font-size: 1.8em;
        font-style: italic;
        text-indent: 0;
    }

    /* Section Breaks */
    .section-break {
        break-before: right;
    }

    .first-chapter {
        break-before: right;
    }

    h1, h2, h3 {
        break-before: right;
        text-indent: 0;
    }

    /* Logic for Illustrations and Chapters:
       - Illustration must be on LEFT (even)
       - Chapter must be on RIGHT (odd)
    */
    .illustration-page + * {
        break-before: right;
    }
"""

        pdf_file = io.BytesIO()
        HTML(string=cleaned_html).write_pdf(pdf_file, stylesheets=[CSS(string=css_string)])
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
