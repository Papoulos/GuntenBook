import sys
from weasyprint import HTML

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 convert.py <input_file.html> <output_file.pdf>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    try:
        html = HTML(input_file)
        html.write_pdf(output_file)
        print(f"Successfully converted {input_file} to {output_file}")
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
