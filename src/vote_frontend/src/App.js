import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import CategoryList from './components/Categories/CategoryList';
import VoteContainer from './components/VoteMode/VoteContainer';
import ResultsContainer from './components/Results/ResultsContainer';
import Header from './components/shared/Header';

function App() {
  return (
    <BrowserRouter>
      <div className="relative min-h-screen bg-slate-950 text-slate-100">
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          <div className="absolute -top-40 left-[-10%] h-[420px] w-[420px] rounded-full bg-fuchsia-500/20 blur-3xl" />
          <div className="absolute top-24 right-[-8%] h-[360px] w-[360px] rounded-full bg-cyan-400/10 blur-3xl" />
          <div className="absolute bottom-0 left-1/2 h-[340px] w-[340px] -translate-x-1/2 rounded-full bg-fuchsia-700/10 blur-3xl" />
        </div>
        <div className="relative">
          <Header />
          <main className="max-w-6xl mx-auto px-6 py-10">
            <Routes>
              <Route path="/" element={<CategoryList />} />
              <Route path="/vote/:categoryId" element={<VoteContainer />} />
              <Route path="/results/:categoryId" element={<ResultsContainer />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
}

export default App;
