import { Book } from "../types";

const GUTENDEX_API = "https://gutendex.com/books";

export const searchBooks = async (query: string, language: string = 'fr'): Promise<Book[]> => {
  if (!query) return [];
  // Append language filter to the API request
  const response = await fetch(`${GUTENDEX_API}?search=${encodeURIComponent(query)}&languages=${language}`);
  const data = await response.json();
  return data.results;
};

export const fetchBookContent = async (url: string): Promise<string> => {
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:5001';
  
  try {
    const response = await fetch(`${apiUrl}/api/fetch-gutenberg?url=${encodeURIComponent(url)}`);

    if (response.ok) {
      const text = await response.text();
      return text;
    } else {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || "Impossible de récupérer le contenu du livre via le serveur.");
    }
  } catch (error: any) {
    console.error(`Erreur lors de la récupération du livre:`, error);
    throw error;
  }
};

export const convertToPdf = async (
  htmlContent: string,
  title: string,
  author: string,
  illustrationMode: string = 'none',
  illustrationCount: number = 0
): Promise<Blob> => {
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:5001';
  const response = await fetch(`${apiUrl}/api/convert`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      html_content: htmlContent,
      title: title,
      author: author,
      illustration_mode: illustrationMode,
      illustration_count: illustrationCount,
    }),
  });

  if (!response.ok) {
    throw new Error('Failed to convert to PDF');
  }

  return response.blob();
};
