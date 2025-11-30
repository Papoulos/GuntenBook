import React, { useState } from 'react';
import { Book, HtmlBook } from './types';
import Search from './components/Search';
import PrintLayout from './components/PrintLayout';
import { fetchBookContent } from './services/bookService';
import { Loader2, AlertCircle } from 'lucide-react';

const App: React.FC = () => {
  const [currentView, setCurrentView] = useState<'search' | 'reading'>('search');
  const [selectedBook, setSelectedBook] = useState<HtmlBook | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSelectBook = async (book: Book) => {
    setLoading(true);
    setError(null);
    try {
      // 1. Chercher l'URL du fichier HTML
      const formats = book.formats;
      const htmlKeys = Object.keys(formats).filter(key => key.startsWith('text/html'));
      
      // On prend le premier disponible
      const htmlUrl = htmlKeys.length > 0 ? formats[htmlKeys[0]] : null;
      
      if (!htmlUrl) {
        throw new Error("Format HTML non disponible pour ce livre.");
      }

      // 2. Télécharger le contenu brut
      const rawHtml = await fetchBookContent(htmlUrl);
      
      // 3. Afficher tel quel
      setSelectedBook({
        title: book.title,
        author: book.authors.map(a => a.name).join(", "),
        htmlContent: rawHtml,
        htmlUrl: htmlUrl
      });
      
      setCurrentView('reading');
    } catch (err: any) {
      setError(err.message || "Erreur inconnue lors du chargement du livre.");
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    setCurrentView('search');
    setSelectedBook(null);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center">
        <Loader2 className="w-12 h-12 text-indigo-600 animate-spin mb-4" />
        <h2 className="text-xl font-medium text-slate-700">Récupération du fichier...</h2>
        <p className="text-slate-500 mt-2">Connexion à Gutenberg via Proxy</p>
      </div>
    );
  }

  return (
    <main className="h-screen w-full">
       {error && (
        <div className="fixed top-4 right-4 max-w-md bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg shadow-lg flex items-start gap-3 z-50">
          <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="font-bold text-sm">Erreur</h3>
            <p className="text-sm mt-1">{error}</p>
            <button 
              onClick={() => setError(null)}
              className="mt-2 text-xs font-semibold uppercase tracking-wide text-red-600 hover:text-red-800"
            >
              Fermer
            </button>
          </div>
        </div>
      )}

      {currentView === 'search' && (
        <Search onSelectBook={handleSelectBook} />
      )}

      {currentView === 'reading' && selectedBook && (
        <PrintLayout book={selectedBook} onBack={handleBack} />
      )}
    </main>
  );
};

export default App;
