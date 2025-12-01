import React, { useState } from 'react';
import { HtmlBook } from '../types';
import { ArrowLeft, Download, Loader2 } from 'lucide-react';
import { convertToPdf } from '../services/bookService';


interface PrintLayoutProps {
  book: HtmlBook;
  onBack: () => void;
}

const PrintLayout: React.FC<PrintLayoutProps> = ({ book, onBack }) => {
  const [isDownloading, setIsDownloading] = useState(false);

  const handleDownload = async () => {
    setIsDownloading(true);
    try {
      const blob = await convertToPdf(book.htmlContent, book.title, book.author);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${book.title}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error("Download failed:", error);
      alert("Une erreur s'est produite lors de la génération du PDF. Veuillez réessayer.");
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div className="h-screen flex flex-col bg-slate-100">
      {/* Toolbar */}
      <div className="bg-white border-b border-slate-200 px-4 py-3 flex items-center justify-between shrink-0 shadow-sm z-10">
        <button
          onClick={onBack}
          className="flex items-center text-slate-600 hover:text-indigo-600 transition-colors font-medium"
        >
          <ArrowLeft className="w-5 h-5 mr-2" />
          Retour à la recherche
        </button>

        <div className="text-center hidden sm:block">
          <h1 className="text-sm font-bold text-slate-800 truncate max-w-md">{book.title}</h1>
          <p className="text-xs text-slate-500">{book.author}</p>
        </div>

        <div className="flex items-center justify-end" style={{ minWidth: '150px' }}>
          <button
            onClick={handleDownload}
            disabled={isDownloading}
            className="flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-indigo-300"
          >
            {isDownloading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Download className="w-5 h-5 mr-2" />
            )}
            <span>{isDownloading ? 'Génération...' : 'Télécharger en PDF'}</span>
          </button>
        </div>
      </div>

      {/* HTML Content Viewer */}
      <div className="flex-1 relative w-full h-full bg-white">
        {/* 
          Using an iframe is the safest and most robust way to display 
          a complete HTML document (with its own head/body/styles) 
          inside a React application.
        */}
        <iframe 
          title="Book Content"
          srcDoc={book.htmlContent}
          className="w-full h-full border-none"
          sandbox="allow-same-origin allow-scripts"
        />
      </div>
    </div>
  );
};

export default PrintLayout;
