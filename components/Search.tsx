import React, { useState, useEffect } from 'react';
import { Search as SearchIcon, BookOpen, Loader2, Globe, FileCode, ChevronRight } from 'lucide-react';
import { Book } from '../types';
import { searchBooks } from '../services/bookService';

interface SearchProps {
  onSelectBook: (book: Book) => void;
}

const LANGUAGES = [
  { code: 'fr', label: 'Français' },
  { code: 'en', label: 'English' },
  { code: 'es', label: 'Español' },
  { code: 'de', label: 'Deutsch' },
];

const Search: React.FC<SearchProps> = ({ onSelectBook }) => {
  const [query, setQuery] = useState('');
  const [language, setLanguage] = useState('fr');
  const [results, setResults] = useState<Book[]>([]);
  const [loading, setLoading] = useState(false);
  const [debouncedQuery, setDebouncedQuery] = useState(query);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(query), 500);
    return () => clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    const doSearch = async () => {
      if (debouncedQuery.trim().length < 2) {
        setResults([]);
        return;
      }
      setLoading(true);
      try {
        const books = await searchBooks(debouncedQuery, language);
        
        // On ne garde que les livres qui ont une version HTML disponible
        const validBooks = books.filter(b => 
          Object.keys(b.formats).some(key => key.startsWith('text/html'))
        );
        setResults(validBooks);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    doSearch();
  }, [debouncedQuery, language]);

  return (
    <div className="max-w-5xl mx-auto p-6">
      <div className="text-center mb-10">
        <h1 className="text-4xl font-serif font-bold text-slate-800 mb-4 flex items-center justify-center gap-3">
          <BookOpen className="w-10 h-10 text-indigo-600" />
          GutenReader
        </h1>
        <p className="text-slate-600 text-lg">
          Visionneuse simple pour Project Gutenberg (HTML)
        </p>
      </div>

      <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-200 mb-8 sticky top-4 z-10">
        <div className="flex flex-col md:flex-row gap-4">
          {/* Language Selector */}
          <div className="relative md:w-48 shrink-0">
             <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Globe className="h-5 w-5 text-gray-400" />
            </div>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="block w-full pl-10 pr-10 py-3 border border-slate-300 rounded-xl leading-5 bg-slate-50 text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 focus:bg-white transition-colors sm:text-base shadow-sm appearance-none cursor-pointer"
            >
              {LANGUAGES.map(lang => (
                <option key={lang.code} value={lang.code}>{lang.label}</option>
              ))}
            </select>
          </div>

          {/* Search Input */}
          <div className="relative flex-1">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <SearchIcon className="h-5 w-5 text-gray-400" />
            </div>
            <input
              type="text"
              className="block w-full pl-10 pr-3 py-3 border border-slate-300 rounded-xl leading-5 bg-slate-50 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 focus:bg-white transition-colors sm:text-base shadow-sm"
              placeholder={`Rechercher par titre ou auteur...`}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            {loading && (
              <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
                <Loader2 className="h-5 w-5 text-indigo-600 animate-spin" />
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Results List View */}
      <div className="space-y-3">
        {results.map((book) => (
          <div 
            key={book.id} 
            className="group bg-white rounded-xl border border-slate-200 shadow-sm hover:shadow-md hover:border-indigo-300 transition-all cursor-pointer overflow-hidden flex flex-col sm:flex-row items-start sm:items-center p-4 gap-4"
            onClick={() => onSelectBook(book)}
          >
            <div className="shrink-0 p-3 bg-indigo-50 rounded-lg text-indigo-600 group-hover:bg-indigo-100 transition-colors">
              <FileCode className="w-6 h-6" />
            </div>

            <div className="flex-1 min-w-0">
              <h3 className="font-serif text-lg font-bold text-slate-800 mb-1 leading-snug">
                {book.title}
              </h3>
              <p className="text-slate-600 text-sm">
                {book.authors.map(a => a.name).join(', ') || 'Auteur inconnu'}
              </p>
              <div className="flex flex-wrap items-center gap-3 mt-2 text-xs text-slate-400">
                <span className="flex items-center gap-1 bg-slate-100 px-2 py-0.5 rounded">
                  <Globe className="w-3 h-3" /> {book.languages.join('/').toUpperCase()}
                </span>
                <span>ID: {book.id}</span>
              </div>
            </div>

            <div className="shrink-0 self-end sm:self-center">
               <button className="flex items-center gap-2 px-4 py-2 bg-slate-50 text-indigo-600 text-sm font-medium rounded-lg border border-slate-200 group-hover:bg-indigo-600 group-hover:text-white group-hover:border-indigo-600 transition-all">
                 Ouvrir HTML
                 <ChevronRight className="w-4 h-4" />
               </button>
            </div>
          </div>
        ))}
      </div>
      
      {results.length === 0 && !loading && debouncedQuery.length > 2 && (
        <div className="text-center text-slate-500 py-12">
          Aucun livre HTML trouvé.
        </div>
      )}
    </div>
  );
};

export default Search;
