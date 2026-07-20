from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import io
import os
import re
import requests
import base64
import fitz
from weasyprint import HTML, CSS
from bs4 import BeautifulSoup, NavigableString, Tag

app = Flask(__name__)

# Configure CORS
# Allow both localhost:3000 and localhost:3001 as they are common dev ports
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:3000", "http://localhost:3001"]}})

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
    else:
        # Wrap everything in <html> and set lang
        new_html = soup.new_tag('html', lang='fr')
        for child in list(soup.contents):
            new_html.append(child.extract())
        soup.append(new_html)

    # --- 3. S'assurer qu'on a une structure propre <html><body>...</body></html> ---
    if not soup.html:
        html_tag = soup.new_tag('html', lang='fr')
        for child in list(soup.contents):
            html_tag.append(child.extract())
        soup.append(html_tag)

    if not soup.body:
        body_tag = soup.new_tag('body')
        for child in list(soup.html.contents):
            body_tag.append(child.extract())
        soup.html.append(body_tag)

    # Nettoyer les éventuels doublons de body (arrive si on a wrappé un fragment)
    bodies = soup.find_all('body')
    if len(bodies) > 1:
        main_body = bodies[0]
        for extra in bodies[1:]:
            for child in list(extra.contents):
                main_body.append(child.extract())
            extra.decompose()

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

    # --- 8. Remplacement du contenu du body par le nouveau contenu propre ---
    # On vide le body actuel pour éviter les résidus de styles ou de balises Gutenberg
    if soup.body:
        soup.body.clear()
        for child in list(new_body.contents):
            soup.body.append(child)
    else:
        soup.append(new_body)

    return str(soup)

@app.route('/api/fetch-gutenberg', methods=['GET'])
def fetch_gutenberg():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "URL is required."}), 400

    # Security check: only allow Gutenberg domains
    allowed_domains = ['gutenberg.org', 'www.gutenberg.org', 'archive.org'] # Expanded
    from urllib.parse import urlparse
    parsed_url = urlparse(url)
    if not any(parsed_url.netloc.endswith(domain) for domain in allowed_domains):
        return jsonify({"error": f"Domain {parsed_url.netloc} is not allowed."}), 403

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        # Check if content type is likely HTML
        content_type = response.headers.get('Content-Type', '').lower()
        if 'text/html' not in content_type and not url.endswith(('.html', '.htm')):
             # If we can't confirm it's HTML, we might still want to try if it looks like it
             # but Project Gutenberg usually returns text/html
             pass

        return response.text
    except requests.RequestException as e:
        app.logger.error(f"Failed to fetch from Gutenberg: {e}")
        return jsonify({"error": "Could not fetch content from Project Gutenberg."}), 502

def get_preview_css_string():
    return """
    @import url('https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;0,700;0,800;1,400;1,500;1,600;1,700;1,800&display=swap');

    @page {
        size: 148.5mm 210mm;
        margin: 0;
    }

    @page :left {
        margin-top: 20mm !important;
        margin-bottom: 20mm !important;
        margin-left: 15mm !important;
        margin-right: 25mm !important;
    }

    @page :right {
        margin-top: 20mm !important;
        margin-bottom: 20mm !important;
        margin-left: 25mm !important;
        margin-right: 15mm !important;
    }

    @page :first {
        margin-top: 20mm !important;
        margin-bottom: 20mm !important;
        margin-left: 25mm !important;
        margin-right: 15mm !important;
    }

    @page :blank {
    }

    @page illustration {
        margin: 20mm 25mm 20mm 15mm !important;
    }

    html, body {
        margin: 0 !important;
        padding: 0 !important;
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
        height: 170mm; /* Fixed height to avoid overflow */
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
        margin: 0;
    }

    /* Logic for Illustrations and Chapters:
       - Illustration must be on LEFT (even)
       - Chapter must be on RIGHT (odd)
    */
    .illustration-page + * {
        break-before: right;
    }
"""

@app.route('/api/convert', methods=['POST'])
def convert_to_pdf():
    # Limit the size of the incoming request to 50MB to handle large books
    if request.content_length and request.content_length > 50 * 1024 * 1024:
        return jsonify({"error": "Request payload is too large (max 50MB)."}), 413

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
        css_string = get_preview_css_string()

        pdf_file = io.BytesIO()
        HTML(string=cleaned_html).write_pdf(pdf_file, stylesheets=[CSS(string=css_string)])
        pdf_file.seek(0)

        # Apply robust page numbering with PyMuPDF
        doc = fitz.open('pdf', pdf_file.read())
        for idx in range(len(doc)):
            page = doc[idx]
            text = page.get_text().strip()
            if idx == 0:
                continue
            elif not text:
                continue
            elif text == "ILLUSTRATION":
                continue
            else:
                rect = page.rect
                num_rect = fitz.Rect(0, rect.height - 50, rect.width, rect.height - 25)
                page.insert_textbox(num_rect, str(idx + 1), fontsize=10, fontname='times-roman', align=1)

        numbered_pdf_bytes = doc.write()
        doc.close()

        numbered_pdf_file = io.BytesIO(numbered_pdf_bytes)
        numbered_pdf_file.seek(0)

        return send_file(
            numbered_pdf_file,
            as_attachment=True,
            download_name=f"{title}.pdf" if title else "document.pdf",
            mimetype='application/pdf'
        )

    except Exception as e:
        # Log the exception for debugging purposes
        app.logger.error(f"PDF conversion failed: {e}")
        # Return a generic error message to the user
        return jsonify({"error": "An error occurred during PDF conversion."}), 500

@app.route('/api/render-preview', methods=['POST'])
def render_preview():
    if request.content_length and request.content_length > 50 * 1024 * 1024:
        return jsonify({"error": "Request payload is too large (max 50MB)."}), 413

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
        css_string = get_preview_css_string()

        pdf_file = io.BytesIO()
        HTML(string=cleaned_html).write_pdf(pdf_file, stylesheets=[CSS(string=css_string)])
        pdf_file.seek(0)

        doc = fitz.open('pdf', pdf_file.read())
        pages_data = []

        for idx in range(len(doc)):
            page = doc[idx]
            text = page.get_text().strip()

            page_type = 'content'
            if idx == 0:
                page_type = 'title'
            elif not text:
                page_type = 'blank'
            elif text == "ILLUSTRATION":
                page_type = 'illustration'

            # Temporarily add page number to content pages for rendering the thumbnail image
            if page_type == 'content':
                rect = page.rect
                num_rect = fitz.Rect(0, rect.height - 50, rect.width, rect.height - 25)
                page.insert_textbox(num_rect, str(idx + 1), fontsize=10, fontname='times-roman', align=1)

            # High-performance, sharp thumbnail at 0.8x scale
            pix = page.get_pixmap(matrix=fitz.Matrix(0.8, 0.8))
            img_bytes = pix.tobytes('png')
            img_base64 = base64.b64encode(img_bytes).decode('utf-8')

            pages_data.append({
                'index': idx,
                'type': page_type,
                'image': f"data:image/png;base64,{img_base64}"
            })

        doc.close()
        return jsonify({"pages": pages_data})

    except Exception as e:
        app.logger.error(f"Preview rendering failed: {e}")
        return jsonify({"error": "An error occurred during preview rendering."}), 500

@app.route('/api/generate-custom-pdf', methods=['POST'])
def generate_custom_pdf():
    if request.content_length and request.content_length > 50 * 1024 * 1024:
        return jsonify({"error": "Request payload is too large (max 50MB)."}), 413

    if not request.is_json:
        return jsonify({"error": "Unsupported Media Type. Must be application/json."}), 415

    try:
        data = request.get_json()
        html_content = data.get('html_content')
        title = data.get('title')
        author = data.get('author')
        illustration_mode = data.get('illustration_mode', 'none')
        illustration_count = int(data.get('illustration_count', 0))
        operations = data.get('operations', [])

        if not html_content:
            return jsonify({"error": "html_content is required."}), 400

        cleaned_html = clean_gutenberg_html(html_content, title, author, illustration_mode, illustration_count)
        css_string = get_preview_css_string()

        pdf_file = io.BytesIO()
        HTML(string=cleaned_html).write_pdf(pdf_file, stylesheets=[CSS(string=css_string)])
        pdf_file.seek(0)

        in_doc = fitz.open('pdf', pdf_file.read())
        out_doc = fitz.open()

        if len(in_doc) > 0:
            first_page = in_doc[0]
            w = first_page.rect.width
            h = first_page.rect.height
        else:
            w, h = 420.945, 595.276

        for op in operations:
            op_type = op.get('type')
            if op_type == 'original':
                orig_idx = op.get('original_index')
                if 0 <= orig_idx < len(in_doc):
                    out_doc.insert_pdf(in_doc, from_page=orig_idx, to_page=orig_idx)
            elif op_type == 'blank':
                out_doc.new_page(width=w, height=h)
            elif op_type == 'illustration':
                page = out_doc.new_page(width=w, height=h)
                rect = fitz.Rect(0, h/2 - 50, w, h/2 + 50)
                page.insert_textbox(rect, "ILLUSTRATION", fontsize=18, fontname='times-roman', align=1, color=(0.7, 0.7, 0.7))

        # Dynamically apply page numbering on the custom layout
        for idx in range(len(out_doc)):
            page = out_doc[idx]
            text = page.get_text().strip()

            if idx == 0:
                continue
            elif not text:
                continue
            elif text == "ILLUSTRATION":
                continue
            else:
                rect = page.rect
                num_rect = fitz.Rect(0, rect.height - 50, rect.width, rect.height - 25)
                page.insert_textbox(num_rect, str(idx + 1), fontsize=10, fontname='times-roman', align=1)

        custom_pdf_bytes = out_doc.write()
        out_doc.close()
        in_doc.close()

        custom_pdf_file = io.BytesIO(custom_pdf_bytes)
        custom_pdf_file.seek(0)

        return send_file(
            custom_pdf_file,
            as_attachment=True,
            download_name=f"{title}.pdf" if title else "document.pdf",
            mimetype='application/pdf'
        )

    except Exception as e:
        app.logger.error(f"Custom PDF generation failed: {e}")
        return jsonify({"error": "An error occurred during custom PDF generation."}), 500

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug_mode, port=5001)
