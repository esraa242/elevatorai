"use client";

import React, { useState, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Upload, Sparkles, Box, MessageCircle, 
  RotateCcw, Download, Share2, Phone, CheckCircle, 
  Loader2, Maximize2
} from 'lucide-react';

interface VisionAnalysis {
  primary_style: { name: string; confidence: number; description: string };
  secondary_styles: Array<{ name: string; confidence: number }>;
  color_palette: { dominant: string[]; accent: string[]; mood_temperature: string };
  materials: Array<{ name: string; finish: string; prominence: string }>;
  mood: { primary: string; lighting: string; atmosphere: string };
  confidence: number;
}

interface CabinMatch {
  id: string;
  name: string;
  style_tags: string[];
  materials: string[];
  color_palette: string[];
  price_usd: number;
  dimensions: { width: number; depth: number; height: number };
  capacity: number;
  thumbnail_url: string;
  features: string[];
  match_score: number;
}

interface GeneratedModel {
  model_files: Record<string, string>;
  preview_images: string[];
  specifications: { poly_count: number; vertex_count: number; dimensions: Record<string, number>; format: string };
}

interface QuoteData {
  quote_id: string;
  cabin_design: string;
  total: number;
  breakdown: Record<string, any>;
  delivery_time: string;
  warranty: string;
}

type Step = 'upload' | 'analyzing' | 'matches' | 'viewer' | 'quote' | 'sent';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function ElevatorAIApp() {
  const [step, setStep] = useState<Step>('upload');
  const [imagePreview, setImagePreview] = useState<string>('');
  const [analysis, setAnalysis] = useState<VisionAnalysis | null>(null);
  const [matches, setMatches] = useState<CabinMatch[]>([]);
  const [selectedCabin, setSelectedCabin] = useState<CabinMatch | null>(null);
  const [model, setModel] = useState<GeneratedModel | null>(null);
  const [quote, setQuote] = useState<QuoteData | null>(null);
  const [phoneNumber, setPhoneNumber] = useState('');
  const [customerName, setCustomerName] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string>('');

  const handleUpload = useCallback(async (file: File) => {
    setIsLoading(true);
    setError('');
    const reader = new FileReader();
    reader.onloadend = () => setImagePreview(reader.result as string);
    reader.readAsDataURL(file);
    setStep('analyzing');

    try {
      const formData = new FormData();
      formData.append('file', file);
      const response = await fetch(`${API_BASE}/api/v2/full-pipeline`, { method: 'POST', body: formData });
      if (!response.ok) throw new Error('Pipeline failed');
      const result = await response.json();
      setAnalysis(result.vision_analysis);
      setMatches(result.matched_cabins || []);
      setSelectedCabin(result.selected_cabin);
      setModel(result.generated_model);
      setQuote(result.quote);
      setStep(result.quote ? 'sent' : 'viewer');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setStep('upload');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleGetQuote = useCallback(async () => {
    if (!selectedCabin || !phoneNumber) return;
    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/v2/get-quote`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          cabin_id: selectedCabin.id,
          customer_phone: phoneNumber,
          customer_name: customerName,
          customizations: selectedCabin.features
        })
      });
      if (!response.ok) throw new Error('Quote generation failed');
      const result = await response.json();
      setQuote(result.quote);
      setStep('sent');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send quote');
    } finally {
      setIsLoading(false);
    }
  }, [selectedCabin, phoneNumber, customerName]);

  return (
    <main className="min-h-screen bg-[#0a0a0f] text-white font-sans">
      <nav className="fixed top-0 w-full z-50 bg-black/50 backdrop-blur-xl border-b border-white/10">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center font-bold text-lg">E</div>
            <span className="text-xl font-semibold">Elevator<span className="text-blue-400">AI</span></span>
          </div>
          <span className="px-3 py-1 rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/30 text-sm">Powered by Google ADK</span>
        </div>
      </nav>

      <div className="pt-28 pb-20 px-6">
        <AnimatePresence mode="wait">
          {step === 'upload' && <UploadStep key="upload" onUpload={handleUpload} isLoading={isLoading} />}
          {step === 'analyzing' && <AnalyzingStep key="analyzing" imagePreview={imagePreview} />}
          {step === 'matches' && analysis && matches.length > 0 && (
            <MatchesStep key="matches" analysis={analysis} matches={matches} onSelect={(c) => { setSelectedCabin(c); setStep('viewer'); }} />
          )}
          {step === 'viewer' && selectedCabin && (
            <ViewerStep key="viewer" cabin={selectedCabin} model={model} onGetQuote={() => setStep('quote')} />
          )}
          {step === 'quote' && selectedCabin && (
            <QuoteStep key="quote" cabin={selectedCabin} phoneNumber={phoneNumber} setPhoneNumber={setPhoneNumber} customerName={customerName} setCustomerName={setCustomerName} onSubmit={handleGetQuote} isLoading={isLoading} />
          )}
          {step === 'sent' && quote && <SentStep key="sent" quote={quote} phoneNumber={phoneNumber} />}
        </AnimatePresence>
        {error && <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="max-w-xl mx-auto mt-6 p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-center">{error}</motion.div>}
      </div>
    </main>
  );
}

function UploadStep({ onUpload, isLoading }: { onUpload: (file: File) => void; isLoading: boolean }) {
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) onUpload(file);
  };

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="max-w-3xl mx-auto text-center pt-12">
      <h1 className="text-5xl md:text-6xl font-bold mb-6">Design Your Perfect<br /><span className="bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">Elevator Cabin</span></h1>
      <p className="text-xl text-gray-400 mb-12 max-w-xl mx-auto">Upload your villa interior photo. Our AI agents will analyze the style, match the perfect cabin design, generate a 3D preview, and send you a quote via WhatsApp.</p>
      <div onDrop={handleDrop} onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }} onDragLeave={() => setIsDragOver(false)} onClick={() => fileInputRef.current?.click()}
        className={`relative rounded-3xl border-2 border-dashed p-16 cursor-pointer transition-all ${isDragOver ? 'border-blue-500 bg-blue-500/10' : 'border-white/20 hover:border-blue-400 hover:bg-white/5'}`}>
        <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={(e) => e.target.files?.[0] && onUpload(e.target.files[0])} />
        <div className="flex flex-col items-center gap-4">
          <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-blue-500/20 to-indigo-600/20 flex items-center justify-center">
            <Upload className="w-10 h-10 text-blue-400" />
          </div>
          <div>
            <p className="text-lg font-medium">{isDragOver ? 'Drop your photo here' : 'Drop your villa interior photo'}</p>
            <p className="text-sm text-gray-500 mt-1">or click to browse • JPG, PNG up to 20MB</p>
          </div>
        </div>
      </div>
      <div className="flex justify-center gap-8 mt-12 text-sm text-gray-500">
        <span className="flex items-center gap-2"><Sparkles className="w-4 h-4 text-blue-400" /> AI Style Analysis</span>
        <span className="flex items-center gap-2"><Box className="w-4 h-4 text-blue-400" /> Smart Matching</span>
        <span className="flex items-center gap-2"><Maximize2 className="w-4 h-4 text-blue-400" /> 3D Preview</span>
        <span className="flex items-center gap-2"><MessageCircle className="w-4 h-4 text-blue-400" /> WhatsApp Quote</span>
      </div>
    </motion.div>
  );
}

function AnalyzingStep({ imagePreview }: { imagePreview: string }) {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="max-w-4xl mx-auto pt-12">
      <div className="grid md:grid-cols-2 gap-12 items-center">
        <div className="relative rounded-2xl overflow-hidden aspect-[4/3]">
          <img src={imagePreview} alt="Upload" className="w-full h-full object-cover" />
          <div className="absolute inset-0 bg-blue-500/10">
            <motion.div className="absolute left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-blue-400 to-transparent" animate={{ top: ['0%', '100%'] }} transition={{ duration: 2, repeat: Infinity, ease: 'linear' }} />
          </div>
        </div>
        <div className="space-y-6">
          <h2 className="text-3xl font-bold">AI Agents Analyzing...</h2>
          <div className="space-y-4">
            {['Detecting design style', 'Extracting color palette', 'Identifying materials', 'Analyzing spatial layout'].map((label, i) => (
              <motion.div key={label} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.3 }} className="flex items-center gap-3">
                <Loader2 className="w-5 h-5 text-blue-400 animate-spin" /><span className="text-gray-300">{label}</span>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

function MatchesStep({ analysis, matches, onSelect }: { analysis: VisionAnalysis; matches: CabinMatch[]; onSelect: (c: CabinMatch) => void }) {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="max-w-7xl mx-auto pt-8">
      <div className="mb-10 p-6 rounded-2xl bg-white/5 border border-white/10">
        <div className="flex items-center gap-3 mb-4"><Sparkles className="w-6 h-6 text-blue-400" /><h2 className="text-2xl font-bold">Style Analysis Complete</h2></div>
        <div className="grid grid-cols-4 gap-6">
          <div><p className="text-sm text-gray-500 mb-1">Primary Style</p><p className="text-lg font-semibold">{analysis.primary_style.name}</p><p className="text-sm text-blue-400">{analysis.primary_style.confidence}% confidence</p></div>
          <div><p className="text-sm text-gray-500 mb-1">Mood</p><p className="text-lg font-semibold capitalize">{analysis.mood.primary}</p><p className="text-sm text-gray-400">{analysis.mood.lighting} lighting</p></div>
          <div><p className="text-sm text-gray-500 mb-1">Colors</p><div className="flex gap-2">{analysis.color_palette.dominant.map((c, i) => <div key={i} className="w-8 h-8 rounded-lg border border-white/20" style={{ backgroundColor: c }} />)}</div></div>
          <div><p className="text-sm text-gray-500 mb-1">Materials</p><div className="flex flex-wrap gap-1">{analysis.materials.slice(0, 3).map((m, i) => <span key={i} className="px-2 py-0.5 rounded-full bg-white/10 text-xs">{m.name}</span>)}</div></div>
        </div>
      </div>

      <h3 className="text-2xl font-bold mb-6">Top Matched Cabin Designs</h3>
      <div className="grid md:grid-cols-3 gap-6">
        {matches.map((cabin, i) => (
          <motion.div key={cabin.id} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }}
            className="group rounded-2xl bg-white/5 border border-white/10 overflow-hidden hover:border-blue-500/50 transition-all cursor-pointer" onClick={() => onSelect(cabin)}>
            <div className="relative aspect-[4/3] bg-gray-800 flex items-center justify-center">
              <Box className="w-12 h-12 text-gray-600" />
              <div className="absolute top-3 right-3 px-3 py-1 rounded-full bg-green-500/20 text-green-400 text-sm font-bold">{cabin.match_score}% Match</div>
            </div>
            <div className="p-5">
              <h4 className="text-xl font-bold mb-1">{cabin.name}</h4>
              <p className="text-sm text-gray-400 mb-3">{cabin.style_tags.join(' • ')}</p>
              <div className="space-y-2 mb-4">
                {cabin.features.slice(0, 3).map((f, fi) => (
                  <div key={fi} className="flex items-center gap-2 text-sm text-gray-300"><CheckCircle className="w-4 h-4 text-blue-400" />{f}</div>
                ))}
              </div>
              <div className="flex items-center justify-between pt-4 border-t border-white/10">
                <span className="text-2xl font-bold text-blue-400">${cabin.price_usd.toLocaleString()}</span>
                <button className="px-4 py-2 rounded-xl bg-blue-500 hover:bg-blue-600 transition text-sm font-medium">View 3D</button>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}

function ViewerStep({ cabin, model, onGetQuote }: { cabin: CabinMatch; model: GeneratedModel | null; onGetQuote: () => void }) {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="max-w-6xl mx-auto pt-8">
      <div className="grid lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">
          <div className="rounded-2xl bg-gradient-to-b from-gray-900 to-black border border-white/10 overflow-hidden">
            <div className="aspect-square flex items-center justify-center relative">
              <div className="text-center">
                <Box className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                <p className="text-gray-500">3D Viewer Placeholder</p>
                <p className="text-sm text-gray-600 mt-1">{model ? `${model.specifications.poly_count} polygons` : 'Generating...'}</p>
              </div>
              <div className="absolute bottom-4 left-4 right-4 flex justify-between">
                <div className="flex gap-2">
                  <button className="p-2 rounded-lg bg-black/50 hover:bg-black/70 transition"><RotateCcw className="w-5 h-5" /></button>
                  <button className="p-2 rounded-lg bg-black/50 hover:bg-black/70 transition"><Download className="w-5 h-5" /></button>
                </div>
                <button className="px-4 py-2 rounded-lg bg-black/50 hover:bg-black/70 transition flex items-center gap-2 text-sm"><Share2 className="w-4 h-4" /> Share</button>
              </div>
            </div>
          </div>
        </div>
        <div className="space-y-6">
          <div><h2 className="text-3xl font-bold mb-2">{cabin.name}</h2><p className="text-gray-400">{cabin.style_tags.join(' • ')}</p></div>
          <div className="p-4 rounded-xl bg-white/5 border border-white/10">
            <p className="text-sm text-gray-500 mb-1">Match Score</p>
            <div className="flex items-center gap-3">
              <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden"><div className="h-full bg-gradient-to-r from-blue-500 to-green-500 rounded-full" style={{ width: `${cabin.match_score}%` }} /></div>
              <span className="text-xl font-bold text-green-400">{cabin.match_score}%</span>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 rounded-xl bg-white/5 border border-white/10"><p className="text-xs text-gray-500 mb-1">Dimensions</p><p className="text-lg font-semibold">{cabin.dimensions.width}×{cabin.dimensions.depth}m</p></div>
            <div className="p-4 rounded-xl bg-white/5 border border-white/10"><p className="text-xs text-gray-500 mb-1">Capacity</p><p className="text-lg font-semibold">{cabin.capacity} Persons</p></div>
          </div>
          <div><p className="text-sm text-gray-500 mb-2">Materials</p><div className="flex flex-wrap gap-2">{cabin.materials.map((m, i) => <span key={i} className="px-3 py-1 rounded-full bg-white/5 border border-white/10 text-sm">{m}</span>)}</div></div>
          <div><p className="text-sm text-gray-500 mb-2">Features</p><div className="space-y-2">{cabin.features.map((f, i) => <div key={i} className="flex items-center gap-2 text-sm text-gray-300"><CheckCircle className="w-4 h-4 text-blue-400" />{f}</div>)}</div></div>
          <div className="pt-4 border-t border-white/10">
            <div className="flex items-center justify-between mb-4"><span className="text-gray-400">Total Price</span><span className="text-3xl font-bold text-blue-400">${cabin.price_usd.toLocaleString()}</span></div>
            <button onClick={onGetQuote} className="w-full py-4 rounded-xl bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 transition font-bold text-lg flex items-center justify-center gap-3">
              <MessageCircle className="w-6 h-6" />Get Quote via WhatsApp
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

function QuoteStep({ cabin, phoneNumber, setPhoneNumber, customerName, setCustomerName, onSubmit, isLoading }: any) {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="max-w-md mx-auto pt-16">
      <div className="text-center mb-8">
        <MessageCircle className="w-16 h-16 text-green-400 mx-auto mb-4" />
        <h2 className="text-3xl font-bold mb-2">Get Your Quote</h2>
        <p className="text-gray-400">We'll send a detailed quote to your WhatsApp</p>
      </div>
      <div className="p-6 rounded-2xl bg-white/5 border border-white/10 space-y-6">
        <div><label className="block text-sm text-gray-400 mb-2">Selected Design</label><div className="p-4 rounded-xl bg-white/5 border border-white/10"><p className="font-bold">{cabin.name}</p><p className="text-sm text-gray-400">${cabin.price_usd.toLocaleString()}</p></div></div>
        <div><label className="block text-sm text-gray-400 mb-2">Your Name</label><input type="text" value={customerName} onChange={(e) => setCustomerName(e.target.value)} placeholder="John Smith" className="w-full p-4 rounded-xl bg-white/5 border border-white/10 focus:border-green-500 focus:outline-none transition" /></div>
        <div><label className="block text-sm text-gray-400 mb-2">WhatsApp Number</label><div className="relative"><Phone className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" /><input type="tel" value={phoneNumber} onChange={(e) => setPhoneNumber(e.target.value)} placeholder="+1 234 567 8900" className="w-full pl-12 pr-4 py-4 rounded-xl bg-white/5 border border-white/10 focus:border-green-500 focus:outline-none transition" /></div><p className="text-xs text-gray-500 mt-2">Include country code (e.g., +1, +44, +971)</p></div>
        <button onClick={onSubmit} disabled={!phoneNumber || isLoading} className="w-full py-4 rounded-xl bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 transition font-bold text-lg flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed">
          {isLoading ? <><Loader2 className="w-5 h-5 animate-spin" />Sending...</> : <><MessageCircle className="w-5 h-5" />Send Quote to WhatsApp</>}
        </button>
      </div>
    </motion.div>
  );
}

function SentStep({ quote, phoneNumber }: { quote: QuoteData; phoneNumber: string }) {
  return (
    <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} className="max-w-lg mx-auto pt-16 text-center">
      <div className="w-20 h-20 rounded-full bg-green-500/20 flex items-center justify-center mx-auto mb-6"><CheckCircle className="w-10 h-10 text-green-400" /></div>
      <h2 className="text-3xl font-bold mb-2">Quote Sent!</h2>
      <p className="text-gray-400 mb-8">We've sent a detailed quote to <span className="text-white font-medium">{phoneNumber}</span> via WhatsApp</p>
      <div className="p-6 rounded-2xl bg-white/5 border border-white/10 text-left mb-8">
        <div className="flex justify-between items-center mb-4 pb-4 border-b border-white/10"><span className="text-gray-400">Quote ID</span><span className="font-mono">{quote.quote_id}</span></div>
        <div className="flex justify-between items-center mb-4 pb-4 border-b border-white/10"><span className="text-gray-400">Design</span><span className="font-medium">{quote.cabin_design}</span></div>
        <div className="flex justify-between items-center"><span className="text-gray-400">Total</span><span className="text-2xl font-bold text-green-400">${quote.total.toLocaleString()}</span></div>
      </div>
      <div className="space-y-3">
        <p className="text-sm text-gray-500">What happens next?</p>
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div className="p-4 rounded-xl bg-white/5 border border-white/10"><Phone className="w-6 h-6 text-blue-400 mx-auto mb-2" /><p className="text-gray-300">Consultation Call</p></div>
          <div className="p-4 rounded-xl bg-white/5 border border-white/10"><Box className="w-6 h-6 text-blue-400 mx-auto mb-2" /><p className="text-gray-300">Final Design</p></div>
          <div className="p-4 rounded-xl bg-white/5 border border-white/10"><CheckCircle className="w-6 h-6 text-blue-400 mx-auto mb-2" /><p className="text-gray-300">Installation</p></div>
        </div>
      </div>
      <button onClick={() => window.location.reload()} className="mt-8 px-6 py-3 rounded-xl bg-white/5 hover:bg-white/10 transition text-sm">Start New Design</button>
    </motion.div>
  );
}
