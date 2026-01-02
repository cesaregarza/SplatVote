import React from 'react';
import { Link } from 'react-router-dom';

function Header() {
  return (
    <header className="bg-gradient-to-r from-splat-orange to-splat-purple py-4 shadow-lg">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between">
          <Link to="/" className="flex items-center space-x-3">
            <span className="text-3xl font-bold text-white drop-shadow-lg">
              SplatVote
            </span>
          </Link>
          <nav className="flex items-center space-x-6">
            <Link
              to="/"
              className="text-white hover:text-yellow-300 transition-colors font-medium"
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
