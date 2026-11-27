/** Marca FullBikers: monograma con la curva de la vía y nombre en tipografía ancha. */
export default function Logo({ claro = false }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: "0.55rem" }}>
      <svg width="34" height="34" viewBox="0 0 64 64" aria-hidden="true">
        <rect width="64" height="64" rx="20" fill={claro ? "#FBFCFB" : "#0F4C42"} />
        <path
          d="M10 50 C 26 44, 30 22, 54 14"
          fill="none"
          stroke="#F2C230"
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray="8 7"
        />
      </svg>
      <span
        style={{
          fontWeight: 820,
          fontVariationSettings: '"wdth" 125',
          fontSize: "1.2rem",
          letterSpacing: "-0.02em",
          color: claro ? "#FBFCFB" : "var(--asfalto)",
        }}
      >
        FullBikers
      </span>
    </span>
  );
}
