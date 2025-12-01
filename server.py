from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import io
import os
from weasyprint import HTML, CSS
from bs4 import BeautifulSoup, NavigableString, Tag

app = Flask(__name__)

# Configure CORS
frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
CORS(app, resources={r"/api/*": {"origins": frontend_url}})

def clean_gutenberg_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')

    # 1. Extract Title and Author (before any cleanup)
    title_tag = soup.find('h1')
    author_tag = None
    
    if title_tag:
        # Look for author in the next few elements
        for sibling in title_tag.find_next_siblings(limit=5):
            if isinstance(sibling, Tag) and sibling.name in ['h2', 'h3', 'p']:
                text = sibling.get_text(strip=True)
                if text and len(text) < 100 and "Chapter" not in text:
                    author_tag = sibling
                    break

    # 2. Create New Body
    new_body = soup.new_tag('body')
    
    # 3. Add Title Page
    title_page = soup.new_tag('div', **{'class': 'title-page'})
    if title_tag:
        title_page.append(title_tag.extract()) # Move title
        if author_tag:
            author_tag_clone = author_tag.extract()
            author_tag_clone['class'] = author_tag_clone.get('class', []) + ['author']
            title_page.append(author_tag_clone)
    new_body.append(title_page)

    # 4. Add Blank Page
    blank_page = soup.new_tag('div', **{'class': 'blank-page'})
    new_body.append(blank_page)

    # 5. Extract Preface and Chapters
    # We scan the original body for headers matching our criteria
    # and append them + their content to the new body.
    
    section_keywords = ["Préface", "Preface", "Chapitre", "Chapter"]
    
    # Find all potential section headers
    headers = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    
    current_section_container = None
    
    for header in headers:
        text = header.get_text(strip=True)
        is_target_section = any(keyword.lower() in text.lower() for keyword in section_keywords)
        
        if is_target_section:
            # Determine the level of the current header (e.g., 2 for h2)
            try:
                current_level = int(header.name[1])
            except (ValueError, IndexError):
                current_level = 6 # Fallback
            
            # Add section break class to header
            header['class'] = header.get('class', []) + ['section-break']
            
            # We need to capture the next sibling BEFORE we move the header
            curr = header.next_sibling
            
            # Append header to new body
            new_body.append(header)
            
            # Append all siblings until the next major header
            while curr:
                next_node = curr.next_sibling
                element_to_move = curr
                
                # Check if we hit another header
                if isinstance(element_to_move, Tag) and element_to_move.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                     curr_text = element_to_move.get_text(strip=True)
                     
                     # Check if it's a target section (always stop)
                     if any(k.lower() in curr_text.lower() for k in section_keywords):
                         break
                     
                     # Check if it's a header of same or higher importance (e.g. h2 -> h2, or h2 -> h1)
                     # This implies end of current section and start of an ignored section
                     try:
                         new_level = int(element_to_move.name[1])
                         if new_level <= current_level:
                             break
                     except (ValueError, IndexError):
                         pass

                # Move the element to the new body
                new_body.append(element_to_move)
                
                # Advance to the next node in the ORIGINAL tree
                curr = next_node

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
            /* No page number on the first page (Title Page) */
            @page :first {
                @bottom-center {
                    content: none;
                }
            }
            
            body {
                font-size: 12pt;
                font-family: serif;
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
