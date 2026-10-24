import { useRef } from "react";

// Click on the photo to outline the railway land. Points are stored
// normalized (0-1), so the same zone applies to photos of any size.
export default function ZoneCanvas({ src, points, onChange }) {
  const boxRef = useRef(null);

  function addPoint(e) {
    const rect = boxRef.current.getBoundingClientRect();
    const x = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width));
    const y = Math.min(1, Math.max(0, (e.clientY - rect.top) / rect.height));
    onChange([...points, [Number(x.toFixed(4)), Number(y.toFixed(4))]]);
  }

  const svgPoints = points.map(([x, y]) => `${x * 100},${y * 100}`).join(" ");

  return (
    <div ref={boxRef} onClick={addPoint} className="relative cursor-crosshair select-none overflow-hidden rounded-md bg-black">
      <img src={src} alt="Photo to mark" className="block w-full" draggable={false} />
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="pointer-events-none absolute inset-0 h-full w-full">
        {points.length >= 3 && (
          <polygon points={svgPoints} fill="rgba(34,211,238,0.22)" stroke="#22D3EE" strokeWidth="0.4" />
        )}
        {points.length > 0 && points.length < 3 && (
          <polyline points={svgPoints} fill="none" stroke="#22D3EE" strokeWidth="0.4" />
        )}
      </svg>
      {points.map(([x, y], i) => (
        <span
          key={i}
          className="pointer-events-none absolute h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white bg-cyan-400"
          style={{ left: `${x * 100}%`, top: `${y * 100}%` }}
        />
      ))}
    </div>
  );
}
