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
  // Force HTTPS to avoid mixed content issues
  const targetUrl = url.replace(/^http:\/\//i, 'https://');
  
  // Strategy: Try multiple CORS proxies in a specific order
  const proxies = [
    (u: string) => `https://api.codetabs.com/v1/proxy?quest=${encodeURIComponent(u)}`,
    (u: string) => `https://api.allorigins.win/raw?url=${encodeURIComponent(u)}`,
    (u: string) => `https://corsproxy.io/?${encodeURIComponent(u)}`
  ];

  for (const createProxyUrl of proxies) {
    try {
      const proxyUrl = createProxyUrl(targetUrl);
      console.log(`Tentative via proxy: ${proxyUrl}`);
      
      const response = await fetch(proxyUrl);
      if (response.ok) {
        const text = await response.text();
        
        // Basic validation
        if (text.length > 500) {
          return text;
        }
      }
    } catch (error) {
      console.warn(`Erreur proxy:`, error);
      // Continue to next proxy
    }
  }

  throw new Error("Impossible de récupérer le contenu du livre. Les serveurs Project Gutenberg limitent parfois l'accès.");
};
