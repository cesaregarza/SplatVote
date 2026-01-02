import React from 'react';
import { Link } from 'react-router-dom';

function Header() {
  return (
    <header className="border-b border-white/5 bg-slate-950/80 backdrop-blur">
      <div className="max-w-6xl mx-auto px-6 py-5">
        <div className="flex items-center justify-between">
          <Link to="/" className="flex items-center gap-4">
            <span className="text-xs uppercase tracking-[0.3em] text-slate-400">
              vote.splat.top
            </span>
            <span className="text-2xl font-semibold text-white">
              SplatVote
            </span>
          </Link>
          <nav className="flex items-center gap-4 text-sm">
            <Link
              to="/"
              className="text-slate-300 hover:text-white transition-colors"
            >
              Categories
            </Link>
          </nav>
        </div>
      </div>
    </header>
  );
}

export default Header;
