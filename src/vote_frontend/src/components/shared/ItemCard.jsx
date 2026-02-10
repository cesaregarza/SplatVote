import React from 'react';
import Badge from './Badge';

function ItemCard({ item, selected, onClick, disabled }) {
  return (
    <div
      onClick={() => !disabled && onClick?.(item)}
      className={`
        relative p-4 rounded-xl cursor-pointer transition-all duration-200 border border-white/5
        ${selected
          ? 'bg-slate-900/80 ring-2 ring-fuchsia-400/50 shadow-[0_0_22px_rgba(217,70,239,0.25)]'
          : 'bg-slate-900/50 hover:bg-slate-900/70'}
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
      <h3 className="text-center font-semibold text-white text-lg">
        {item.name}
      </h3>
      {item.group_name && (
        <p className="text-center text-slate-400 text-sm mt-1">
          {item.group_name}
        </p>
      )}
      {selected && (
        <div className="absolute top-2 right-2">
          <Badge variant="mode" className="text-fuchsia-100">
            Selected
          </Badge>
        </div>
      )}
    </div>
  );
}

export default ItemCard;
