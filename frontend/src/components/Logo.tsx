export function Logo({ className = 'h-8 w-8' }: { className?: string }) {
  return (
    <svg viewBox="0 0 48 48" className={className} role="img" aria-label="PomidorAI">
      <circle cx="24" cy="29" r="15" fill="#dc2626" />
      <path
        d="M24 14c-4.5-5.5-11-6.5-15-5 1 5.5 6 10 15 10.5z"
        fill="#16a34a"
      />
      <path
        d="M24 14c4.5-5.5 11-6.5 15-5-1 5.5-6 10-15 10.5z"
        fill="#22c55e"
      />
      <path d="M23 6h2v9h-2z" fill="#15803d" />
      <ellipse cx="18" cy="25" rx="4" ry="5" fill="#ef4444" opacity="0.55" />
    </svg>
  );
}
