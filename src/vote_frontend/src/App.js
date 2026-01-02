import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import CategoryList from './components/Categories/CategoryList';
import VoteContainer from './components/VoteMode/VoteContainer';
import ResultsContainer from './components/Results/ResultsContainer';
import Header from './components/shared/Header';

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-900">
        <Header />
        <main className="container mx-auto px-4 py-8">
          <Routes>
            <Route path="/" element={<CategoryList />} />
            <Route path="/vote/:categoryId" element={<VoteContainer />} />
            <Route path="/results/:categoryId" element={<ResultsContainer />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
