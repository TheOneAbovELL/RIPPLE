/** Three arcs spreading from a point: the product's idea (a change and its waves) as the
 * mark. Inline SVG in currentColor, so it needs no asset and follows the theme. */
export function BrandMark({ className = "brand-mark" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 32 32" aria-hidden="true" focusable="false">
      <circle cx="9" cy="23" r="3" fill="currentColor" />
      <path
        d="M9 14.5a8.5 8.5 0 0 1 8.5 8.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.4"
        strokeLinecap="round"
      />
      <path
        d="M9 8.5A14.5 14.5 0 0 1 23.5 23"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.4"
        strokeLinecap="round"
        opacity="0.7"
      />
      <path
        d="M9 2.5A20.5 20.5 0 0 1 29.5 23"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.4"
        strokeLinecap="round"
        opacity="0.4"
      />
    </svg>
  );
}
