import React from 'react';

const VARIANT_CLASS_MAP = {
  default: 'border-white/10 bg-white/5 text-slate-200',
  mode: 'border-fuchsia-500/30 bg-fuchsia-500/10 text-fuchsia-200',
  discord: 'border-sky-500/30 bg-sky-500/10 text-sky-200',
  success: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200',
  muted: 'border-slate-500/30 bg-slate-800/50 text-slate-300',
};

const SIZE_CLASS_MAP = {
  sm: 'px-2.5 py-1 text-[0.65rem] tracking-wide',
  md: 'px-3 py-1 text-[0.7rem] tracking-wide',
  lg: 'px-4 py-1 text-xs tracking-[0.3em]',
};

function Badge({
  children,
  variant = 'default',
  size = 'sm',
  uppercase = true,
  className = '',
}) {
  const variantClass = VARIANT_CLASS_MAP[variant] || VARIANT_CLASS_MAP.default;
  const sizeClass = SIZE_CLASS_MAP[size] || SIZE_CLASS_MAP.sm;

  return (
    <span
      className={`rounded-full border font-semibold ${sizeClass} ${variantClass} ${
        uppercase ? 'uppercase' : ''
      } ${className}`}
    >
      {children}
    </span>
  );
}

export default Badge;
