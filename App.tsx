import React, { useState } from 'react';
import { Book, HtmlBook } from './types';
import Search from './components/Search';
import PrintLayout from './components/PrintLayout';
import { fetchBookContent } from './services/bookService';
import { Loader2, AlertCircle, Upload } from 'lucide-react';

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

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target?.result as string;
      setSelectedBook({
        title: file.name.replace(/\.[^/.]+$/, ""), // Use filename as title
        author: "Upload manuel",
        htmlContent: content,
        htmlUrl: ""
      });
      setCurrentView('reading');
    };
    reader.onerror = () => {
      setError("Erreur lors de la lecture du fichier.");
    };
    reader.readAsText(file);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center">
        <Loader2 className="w-12 h-12 text-indigo-600 animate-spin mb-4" />
        <h2 className="text-xl font-medium text-slate-700">Récupération du fichier...</h2>
        <p className="text-slate-500 mt-2">Le serveur récupère le fichier directement depuis Gutenberg</p>
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
        <>
          <Search onSelectBook={handleSelectBook} />

          <div className="max-w-5xl mx-auto px-6 pb-12">
            <div className="flex flex-col items-center p-8 border-2 border-dashed border-slate-300 rounded-2xl bg-slate-50/50 hover:bg-slate-50 transition-colors">
              <Upload className="w-10 h-10 text-slate-400 mb-4" />
              <h3 className="text-lg font-medium text-slate-700 mb-2">Ou importez votre propre fichier</h3>
              <p className="text-slate-500 text-center mb-6 max-w-md">
                Si la récupération automatique échoue, vous pouvez télécharger le fichier HTML depuis Gutenberg et le charger ici.
              </p>
              <label className="cursor-pointer bg-white px-6 py-2.5 rounded-xl border border-slate-300 text-slate-700 font-medium hover:bg-slate-50 transition-colors shadow-sm">
                Choisir un fichier HTML
                <input
                  type="file"
                  className="hidden"
                  accept=".html,.htm"
                  onChange={handleFileUpload}
                />
              </label>
            </div>
          </div>
        </>
      )}

      {currentView === 'reading' && selectedBook && (
        <PrintLayout book={selectedBook} onBack={handleBack} />
      )}
    </main>
  );
};

export default App;
