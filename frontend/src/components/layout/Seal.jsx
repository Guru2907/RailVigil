// The RailVigil mark: two rails and three sleepers, seen in perspective.
// `onAccent` draws it in white for the green top bar.
export function Seal({ size = "h-9 w-9", onAccent = false }) {
  const tone = onAccent ? "border-white/80 text-white" : "border-accent text-accent";
  return (
    <div className={`flex ${size} shrink-0 items-center justify-center rounded-full border-2 ${tone}`}>
      <svg viewBox="0 0 32 32" className="h-[58%] w-[58%]" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden>
        <path d="M11 3 7 29M21 3l4 26" />
        <path d="M9.5 10h13M8.5 17h15M7.5 24h17" strokeWidth="1.6" />
      </svg>
    </div>
  );
}
