import React, { useState } from 'react';
import { HtmlBook } from '../types';
import {
  ArrowLeft,
  Download,
  Loader2,
  FileText,
  Image,
  Trash2,
  RotateCcw,
  Eye,
  BookOpen,
  Sparkles
} from 'lucide-react';
import {
  convertToPdf,
  renderPreview,
  generateCustomPdf,
  PreviewPage,
  PageOperation
} from '../services/bookService';

interface PrintLayoutProps {
  book: HtmlBook;
  onBack: () => void;
}

interface EditablePage {
  id: string;
  originalIndex?: number;
  type: 'original' | 'blank' | 'illustration';
  image: string; // base64 representation if original, empty if blank/illustration
}

const PrintLayout: React.FC<PrintLayoutProps> = ({ book, onBack }) => {
  const [activeTab, setActiveTab] = useState<'html' | 'pages'>('html');
  const [isDownloading, setIsDownloading] = useState(false);
  const [illustrationMode, setIllustrationMode] = useState<'none' | 'fixed' | 'chapter'>('none');
  const [illustrationCount, setIllustrationCount] = useState(5);

  // Pages preview states
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const [pages, setPages] = useState<EditablePage[]>([]);
  const [originalPages, setOriginalPages] = useState<EditablePage[]>([]);
  const [previewError, setPreviewError] = useState<string | null>(null);

  const handleFetchPreview = async (force: boolean = false) => {
    if (pages.length > 0 && !force) return;

    setIsPreviewLoading(true);
    setPreviewError(null);
    try {
      const rawPages = await renderPreview(
        book.htmlContent,
        book.title,
        book.author,
        illustrationMode,
        illustrationCount
      );

      const mappedPages: EditablePage[] = rawPages.map(p => ({
        id: `original-${p.index}-${Math.random().toString(36).substr(2, 9)}`,
        originalIndex: p.index,
        type: p.type === 'title' ? 'original' : (p.type === 'blank' ? 'blank' : (p.type === 'illustration' ? 'illustration' : 'original')),
        image: p.image
      }));

      setPages(mappedPages);
      setOriginalPages(JSON.parse(JSON.stringify(mappedPages)));
    } catch (err: any) {
      console.error("Preview failed:", err);
      setPreviewError("Impossible de générer l'aperçu du PDF. Veuillez réessayer.");
    } finally {
      setIsPreviewLoading(false);
    }
  };

  const handleTabChange = (tab: 'html' | 'pages') => {
    setActiveTab(tab);
    if (tab === 'pages') {
      handleFetchPreview();
    }
  };

  const handleDownload = async () => {
    setIsDownloading(true);
    try {
      let blob: Blob;

      if (activeTab === 'pages' && pages.length > 0) {
        // Construct page operations for custom PDF compilation
        const operations: PageOperation[] = pages.map(p => {
          if (p.type === 'original' && p.originalIndex !== undefined) {
            return { type: 'original', original_index: p.originalIndex };
          } else if (p.type === 'blank') {
            return { type: 'blank' };
          } else {
            return { type: 'illustration' };
          }
        });

        blob = await generateCustomPdf(
          book.htmlContent,
          book.title,
          book.author,
          illustrationMode,
          illustrationCount,
          operations
        );
      } else {
        // Original PDF conversion
        blob = await convertToPdf(
          book.htmlContent,
          book.title,
          book.author,
          illustrationMode,
          illustrationCount
        );
      }

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

  const handleDeletePage = (indexToDelete: number) => {
    setPages(prev => prev.filter((_, idx) => idx !== indexToDelete));
  };

  const handleInsertPage = (afterIndex: number, type: 'blank' | 'illustration') => {
    const newPage: EditablePage = {
      id: `${type}-${Math.random().toString(36).substr(2, 9)}`,
      type: type,
      image: ''
    };

    setPages(prev => {
      const copy = [...prev];
      copy.splice(afterIndex + 1, 0, newPage);
      return copy;
    });
  };

  const handleResetPages = () => {
    if (window.confirm("Êtes-vous sûr de vouloir réinitialiser toutes les modifications apportées aux pages ?")) {
      setPages(JSON.parse(JSON.stringify(originalPages)));
    }
  };

  // Group pages in spreads: cover/page 1 on right, (page 2, page 3), (page 4, page 5), etc.
  const getSpreadRows = () => {
    const rows: { left: EditablePage | null; right: EditablePage | null }[] = [];
    if (pages.length === 0) return rows;

    // Row 0: Cover page on the right side
    rows.push({ left: null, right: pages[0] });

    // Subsequent rows: Left is even index, Right is odd index
    for (let i = 1; i < pages.length; i += 2) {
      rows.push({
        left: pages[i],
        right: pages[i + 1] || null
      });
    }
    return rows;
  };

  const spreadRows = getSpreadRows();

  return (
    <div className="h-screen flex flex-col bg-slate-100">
      {/* Toolbar */}
      <div className="bg-white border-b border-slate-200 px-4 py-3 flex flex-col md:flex-row md:items-center justify-between shrink-0 shadow-sm z-10 gap-3">
        <div className="flex items-center gap-4">
          <button
            onClick={onBack}
            className="flex items-center text-slate-600 hover:text-indigo-600 transition-colors font-medium text-sm shrink-0"
          >
            <ArrowLeft className="w-5 h-5 mr-2" />
            Retour
          </button>

          <div className="text-left hidden sm:block">
            <h1 className="text-sm font-bold text-slate-800 truncate max-w-[200px] md:max-w-xs">{book.title}</h1>
            <p className="text-xs text-slate-500 truncate max-w-[200px] md:max-w-xs">{book.author}</p>
          </div>
        </div>

        {/* View Selection Tabs */}
        <div className="flex bg-slate-100 p-1 rounded-xl border border-slate-200 shrink-0 self-center md:self-auto">
          <button
            onClick={() => handleTabChange('html')}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'html'
                ? 'bg-white text-slate-800 shadow-sm'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            <Eye className="w-4 h-4" />
            Aperçu HTML
          </button>
          <button
            onClick={() => handleTabChange('pages')}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'pages'
                ? 'bg-white text-slate-800 shadow-sm'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            <BookOpen className="w-4 h-4" />
            Découpage des pages (PDF)
          </button>
        </div>

        <div className="flex items-center justify-end gap-3 self-end md:self-auto">
          {/* Settings for Illustrations */}
          <div className="flex items-center bg-slate-50 p-1 rounded-lg border border-slate-200">
            <select
              value={illustrationMode}
              onChange={(e) => {
                const mode = e.target.value as any;
                setIllustrationMode(mode);
                if (activeTab === 'pages') {
                  // Prompt regeneration of pages
                  setTimeout(() => handleFetchPreview(true), 100);
                }
              }}
              className="bg-transparent text-xs font-semibold text-slate-600 outline-none px-2 py-1 cursor-pointer"
            >
              <option value="none">Pas d'illustrations</option>
              <option value="fixed">Répartition homogène</option>
              <option value="chapter">Avant chaque chapitre</option>
            </select>

            {illustrationMode === 'fixed' && (
              <div className="flex items-center border-l border-slate-200 ml-1 pl-2">
                <span className="text-[10px] uppercase text-slate-400 font-bold mr-2">Qté:</span>
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={illustrationCount}
                  onChange={(e) => {
                    const count = parseInt(e.target.value) || 0;
                    setIllustrationCount(count);
                    if (activeTab === 'pages') {
                      setTimeout(() => handleFetchPreview(true), 100);
                    }
                  }}
                  className="w-12 bg-white border border-slate-200 rounded text-xs px-1 py-0.5 font-bold text-slate-700"
                />
              </div>
            )}
          </div>

          {activeTab === 'pages' && pages.length > 0 && (
            <button
              onClick={handleResetPages}
              title="Réinitialiser toutes les modifications"
              className="p-2 bg-slate-50 hover:bg-slate-100 text-slate-600 rounded-lg border border-slate-200 transition-all shadow-sm"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          )}

          <button
            onClick={handleDownload}
            disabled={isDownloading || (activeTab === 'pages' && pages.length === 0)}
            className="flex items-center justify-center px-4 py-2 border border-transparent text-sm font-semibold rounded-lg text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-indigo-300 shadow-sm transition-colors"
          >
            {isDownloading ? (
              <Loader2 className="w-5 h-5 animate-spin mr-2" />
            ) : (
              <Download className="w-5 h-5 mr-2" />
            )}
            <span>{isDownloading ? 'Génération...' : 'Télécharger le PDF'}</span>
          </button>
        </div>
      </div>

      {/* Main content container */}
      <div className="flex-1 overflow-hidden relative">
        {activeTab === 'html' ? (
          /* HTML Content Viewer */
          <div className="w-full h-full bg-white">
            <iframe
              title="Book Content"
              srcDoc={book.htmlContent}
              className="w-full h-full border-none"
              sandbox="allow-same-origin allow-scripts"
            />
          </div>
        ) : (
          /* PDF Page Sorter / Editor */
          <div className="w-full h-full overflow-y-auto bg-slate-100">
            {isPreviewLoading ? (
              <div className="flex flex-col items-center justify-center h-96">
                <Loader2 className="w-12 h-12 text-indigo-600 animate-spin mb-4" />
                <h3 className="text-lg font-medium text-slate-700">Génération du découpage PDF...</h3>
                <p className="text-slate-500 text-sm mt-1">Nous préparons les miniatures de chaque page du livre</p>
              </div>
            ) : previewError ? (
              <div className="flex flex-col items-center justify-center h-96 px-4 text-center">
                <div className="text-red-500 text-sm font-semibold mb-2 bg-red-50 px-4 py-2 rounded-lg border border-red-100">
                  {previewError}
                </div>
                <button
                  onClick={() => handleFetchPreview(true)}
                  className="mt-4 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-semibold shadow"
                >
                  Réessayer la génération
                </button>
              </div>
            ) : (
              <div className="max-w-5xl mx-auto py-10 px-4">
                <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm mb-8 text-center max-w-2xl mx-auto">
                  <h2 className="text-sm font-bold text-slate-800 mb-1 flex items-center justify-center gap-1.5">
                    <Sparkles className="w-4 h-4 text-indigo-500" />
                    Éditeur visuel de pages PDF
                  </h2>
                  <p className="text-xs text-slate-500 leading-relaxed">
                    Ajustez l'ordre et le contenu physique du document final. Ajoutez des pages vierges ou d'illustrations
                    pour obtenir un vis-à-vis parfait. La numérotation se recalcule automatiquement à la validation.
                  </p>
                </div>

                {/* Spreads Grid rendering */}
                <div className="flex flex-col gap-10">
                  {spreadRows.map((row, rowIndex) => (
                    <div key={rowIndex} className="flex flex-col items-center">
                      <div className="flex justify-center items-stretch gap-4 sm:gap-8 md:gap-12 w-full max-w-3xl">

                        {/* Left page of the spread (verso) */}
                        <div className="w-full max-w-[240px]">
                          {row.left ? (
                            <div className="flex flex-col items-center p-3 bg-white rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow relative group animate-fade-in">
                              {/* Header with Type & Real Position */}
                              <div className="w-full flex justify-between items-center mb-2 px-1">
                                <span className="text-xs font-bold text-slate-400">
                                  Page {pages.indexOf(row.left) + 1}
                                </span>
                                {row.left.type !== 'original' && (
                                  <span className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded ${
                                    row.left.type === 'blank' ? 'bg-slate-100 text-slate-600' : 'bg-indigo-50 text-indigo-600'
                                  }`}>
                                    {row.left.type === 'blank' ? 'Vierge' : 'Illu'}
                                  </span>
                                )}
                              </div>

                              {/* Physical content preview */}
                              <div className="relative w-full aspect-[1/1.414] rounded-lg overflow-hidden border border-slate-100 bg-slate-50">
                                {row.left.type === 'blank' ? (
                                  <div className="w-full h-full flex flex-col items-center justify-center text-slate-400">
                                    <FileText className="w-8 h-8 mb-1" />
                                    <span className="text-[10px] font-bold">PAGE VIERGE</span>
                                  </div>
                                ) : row.left.type === 'illustration' ? (
                                  <div className="w-full h-full flex flex-col items-center justify-center bg-indigo-50/30 text-indigo-400 border border-indigo-100/50">
                                    <Image className="w-8 h-8 mb-1" />
                                    <span className="text-[10px] font-bold tracking-wider">ILLUSTRATION</span>
                                  </div>
                                ) : (
                                  <img
                                    src={row.left.image}
                                    alt={`Page ${pages.indexOf(row.left) + 1}`}
                                    className="w-full h-full object-cover"
                                  />
                                )}
                              </div>

                              {/* Quick Action Buttons */}
                              <div className="w-full grid grid-cols-3 gap-1 mt-3">
                                <button
                                  onClick={() => handleInsertPage(pages.indexOf(row.left!), 'blank')}
                                  title="Insérer une page vierge après"
                                  className="flex flex-col items-center justify-center py-1 bg-slate-50 hover:bg-slate-100 text-slate-600 rounded border border-slate-200 transition-colors"
                                >
                                  <FileText className="w-3.5 h-3.5" />
                                  <span className="text-[9px] mt-0.5 font-bold">+ Vierge</span>
                                </button>
                                <button
                                  onClick={() => handleInsertPage(pages.indexOf(row.left!), 'illustration')}
                                  title="Insérer une page d'illustration après"
                                  className="flex flex-col items-center justify-center py-1 bg-indigo-50/50 hover:bg-indigo-50 text-indigo-600 rounded border border-indigo-100 transition-colors"
                                >
                                  <Image className="w-3.5 h-3.5" />
                                  <span className="text-[9px] mt-0.5 font-bold">+ Illu</span>
                                </button>
                                <button
                                  onClick={() => handleDeletePage(pages.indexOf(row.left!))}
                                  title="Supprimer cette page"
                                  className="flex flex-col items-center justify-center py-1 bg-red-50 hover:bg-red-100 text-red-600 rounded border border-red-100 transition-colors"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                  <span className="text-[9px] mt-0.5 font-bold">Suppr.</span>
                                </button>
                              </div>
                            </div>
                          ) : (
                            /* Visual balance layout space (the cover starts on recto) */
                            <div className="hidden sm:block w-full aspect-[1/1.414] border border-dashed border-slate-300/40 rounded-xl bg-slate-50/20" />
                          )}
                        </div>

                        {/* Middle Spine separating Left & Right columns */}
                        <div className="w-1 border-r border-dashed border-slate-300 relative shrink-0">
                          <span className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-slate-100 text-[10px] text-slate-400 font-bold tracking-wider uppercase px-1.5 rotate-90 whitespace-nowrap select-none">
                            {rowIndex === 0 ? "Couverture" : "Pliure"}
                          </span>
                        </div>

                        {/* Right page of the spread (recto) */}
                        <div className="w-full max-w-[240px]">
                          {row.right ? (
                            <div className="flex flex-col items-center p-3 bg-white rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow relative group animate-fade-in">
                              {/* Header with Type & Real Position */}
                              <div className="w-full flex justify-between items-center mb-2 px-1">
                                <span className="text-xs font-bold text-slate-400">
                                  {pages.indexOf(row.right) === 0 ? "Couverture" : `Page ${pages.indexOf(row.right) + 1}`}
                                </span>
                                {row.right.type !== 'original' && (
                                  <span className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded ${
                                    row.right.type === 'blank' ? 'bg-slate-100 text-slate-600' : 'bg-indigo-50 text-indigo-600'
                                  }`}>
                                    {row.right.type === 'blank' ? 'Vierge' : 'Illu'}
                                  </span>
                                )}
                              </div>

                              {/* Physical content preview */}
                              <div className="relative w-full aspect-[1/1.414] rounded-lg overflow-hidden border border-slate-100 bg-slate-50">
                                {row.right.type === 'blank' ? (
                                  <div className="w-full h-full flex flex-col items-center justify-center text-slate-400">
                                    <FileText className="w-8 h-8 mb-1" />
                                    <span className="text-[10px] font-bold">PAGE VIERGE</span>
                                  </div>
                                ) : row.right.type === 'illustration' ? (
                                  <div className="w-full h-full flex flex-col items-center justify-center bg-indigo-50/30 text-indigo-400 border border-indigo-100/50">
                                    <Image className="w-8 h-8 mb-1" />
                                    <span className="text-[10px] font-bold tracking-wider">ILLUSTRATION</span>
                                  </div>
                                ) : (
                                  <img
                                    src={row.right.image}
                                    alt={`Page ${pages.indexOf(row.right) + 1}`}
                                    className="w-full h-full object-cover"
                                  />
                                )}
                              </div>

                              {/* Quick Action Buttons */}
                              <div className="w-full grid grid-cols-3 gap-1 mt-3">
                                <button
                                  onClick={() => handleInsertPage(pages.indexOf(row.right!), 'blank')}
                                  title="Insérer une page vierge après"
                                  className="flex flex-col items-center justify-center py-1 bg-slate-50 hover:bg-slate-100 text-slate-600 rounded border border-slate-200 transition-colors"
                                >
                                  <FileText className="w-3.5 h-3.5" />
                                  <span className="text-[9px] mt-0.5 font-bold">+ Vierge</span>
                                </button>
                                <button
                                  onClick={() => handleInsertPage(pages.indexOf(row.right!), 'illustration')}
                                  title="Insérer une page d'illustration après"
                                  className="flex flex-col items-center justify-center py-1 bg-indigo-50/50 hover:bg-indigo-50 text-indigo-600 rounded border border-indigo-100 transition-colors"
                                >
                                  <Image className="w-3.5 h-3.5" />
                                  <span className="text-[9px] mt-0.5 font-bold">+ Illu</span>
                                </button>
                                <button
                                  onClick={() => handleDeletePage(pages.indexOf(row.right!))}
                                  title="Supprimer cette page"
                                  className="flex flex-col items-center justify-center py-1 bg-red-50 hover:bg-red-100 text-red-600 rounded border border-red-100 transition-colors"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                  <span className="text-[9px] mt-0.5 font-bold">Suppr.</span>
                                </button>
                              </div>
                            </div>
                          ) : (
                            <div className="hidden sm:block w-full aspect-[1/1.414] border border-dashed border-slate-300/40 rounded-xl bg-slate-50/20" />
                          )}
                        </div>

                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default PrintLayout;
