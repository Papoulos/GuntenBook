import React from 'react';
import { HtmlBook } from '../types';
import { ArrowLeft } from 'lucide-react';

interface PrintLayoutProps {
  book: HtmlBook;
  onBack: () => void;
}

const PrintLayout: React.FC<PrintLayoutProps> = ({ book, onBack }) => {
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

        <div className="w-20"></div> {/* Spacer to center title */}
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
          sandbox="allow-same-origin" 
        />
      </div>
    </div>
  );
};

export default PrintLayout;
