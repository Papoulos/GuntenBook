export interface Book {
  id: number;
  title: string;
  authors: Author[];
  formats: Record<string, string>;
  download_count: number;
  languages: string[];
}

export interface Author {
  name: string;
  birth_year: number | null;
  death_year: number | null;
}

// Structure simplifiée : on garde juste le contenu HTML brut
export interface HtmlBook {
  title: string;
  author: string;
  htmlContent: string;
  htmlUrl: string;
}
