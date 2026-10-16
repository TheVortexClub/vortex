/** Rio de Janeiro at dusk: Corcovado, Sugarloaf and city lights (pure SVG, no image files). */
export function RioSkyline({ className = "" }: { className?: string }) {
  // deterministic "random" city lights
  const lights = Array.from({ length: 140 }, (_, i) => {
    const x = (i * 37.3) % 320;
    const y = 158 + ((i * 13.7) % 22) + (x > 210 ? 4 : 0);
    const warm = i % 5 !== 0;
    return { x, y, r: i % 7 === 0 ? 0.9 : 0.55, color: warm ? "#ffd27a" : "#9cc8ff", o: 0.5 + (i % 4) * 0.12 };
  });
  return (
    <svg viewBox="0 0 320 200" preserveAspectRatio="xMidYMax slice" className={className} aria-hidden="true">
      <defs>
        <linearGradient id="rio-sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#0b1020" stopOpacity="0" />
          <stop offset="0.35" stopColor="#1e1b4b" />
          <stop offset="0.62" stopColor="#5b2a6e" />
          <stop offset="0.8" stopColor="#c2410c" />
          <stop offset="0.9" stopColor="#f59e0b" />
        </linearGradient>
        <linearGradient id="rio-water" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#1b1640" />
          <stop offset="1" stopColor="#05070f" />
        </linearGradient>
      </defs>
      <rect width="320" height="185" fill="url(#rio-sky)" />
      {/* far hills */}
      <path d="M0 150 L40 128 L70 140 L110 120 L150 142 L200 132 L240 146 L320 136 L320 175 L0 175 Z" fill="#1a1838" opacity="0.9" />
      {/* Corcovado with Christ the Redeemer */}
      <path d="M20 175 L60 120 L78 96 L86 72 L92 70 L100 96 L120 130 L160 175 Z" fill="#0d0c1f" />
      <rect x="88.6" y="58" width="2.2" height="13" fill="#e9d5ff" opacity="0.9" />
      <rect x="84.2" y="61" width="11" height="1.8" fill="#e9d5ff" opacity="0.9" />
      {/* Sugarloaf */}
      <path d="M205 175 C210 140 222 112 238 108 C252 106 260 130 262 175 Z" fill="#0d0c1f" />
      <path d="M255 175 C258 160 266 148 276 148 C286 149 292 162 294 175 Z" fill="#100f25" />
      <line x1="238" y1="108" x2="276" y2="148" stroke="#c4b5fd" strokeWidth="0.4" opacity="0.6" />
      {/* city */}
      <path d="M0 175 L0 160 L12 160 L12 154 L20 154 L20 158 L34 158 L34 150 L40 150 L40 160 L60 160 L60 156 L74 156 L74 162 L96 162 L96 152 L104 152 L104 160 L130 160 L130 155 L146 155 L146 163 L180 163 L180 158 L198 158 L198 166 L320 166 L320 175 Z" fill="#090818" />
      <rect y="175" width="320" height="25" fill="url(#rio-water)" />
      {lights.map((l, i) => (
        <circle key={i} cx={l.x} cy={Math.min(l.y, 176)} r={l.r} fill={l.color} opacity={l.o} />
      ))}
      {/* reflections */}
      {lights.filter((_, i) => i % 6 === 0).map((l, i) => (
        <rect key={`r${i}`} x={l.x - 0.3} y={178} width={0.6} height={6 + (i % 4) * 3} fill={l.color} opacity={0.25} />
      ))}
    </svg>
  );
}
