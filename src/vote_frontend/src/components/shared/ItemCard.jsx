import React from 'react';

function ItemCard({ item, selected, onClick, disabled }) {
  return (
    <div
      onClick={() => !disabled && onClick?.(item)}
      className={`
        relative p-4 rounded-xl cursor-pointer transition-all duration-200
        ${selected
          ? 'bg-splat-orange ring-4 ring-yellow-400 scale-105'
          : 'bg-gray-800 hover:bg-gray-700'}
        ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
      `}
    >
      {item.image_url && (
        <div className="flex justify-center mb-3">
          <img
            src={item.image_url}
            alt={item.name}
            className="w-20 h-20 object-contain"
            onError={(e) => e.target.style.display = 'none'}
          />
        </div>
      )}
      <h3 className="text-center font-bold text-white text-lg">
        {item.name}
      </h3>
      {item.group_name && (
        <p className="text-center text-gray-400 text-sm mt-1">
          {item.group_name}
        </p>
      )}
      {selected && (
        <div className="absolute top-2 right-2">
          <span className="text-2xl">✓</span>
        </div>
      )}
    </div>
  );
}

export default ItemCard;
