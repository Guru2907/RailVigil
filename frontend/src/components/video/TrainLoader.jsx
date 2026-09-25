const SLEEPERS = Array.from({ length: 24 }, (_, i) => 10 + i * 20);

export default function TrainLoader() {
  return (
    <>
      <div className="rv-widget" role="status" aria-label="Analysis in progress">
        {/* Track */}
        <div className="rv-track-layer" aria-hidden="true">
          <svg className="rv-track-svg" viewBox="0 0 480 20" preserveAspectRatio="none">
            {SLEEPERS.map((x) => (
              <line
                key={x}
                x1={x}
                y1="2"
                x2={x}
                y2="18"
                stroke="#18181B"
                strokeOpacity="0.25"
                strokeWidth="2.5"
                vectorEffect="non-scaling-stroke"
              />
            ))}
            <line x1="0" y1="5" x2="480" y2="5" stroke="#18181B" strokeOpacity="0.25" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
            <line x1="0" y1="15" x2="480" y2="15" stroke="#18181B" strokeOpacity="0.25" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
          </svg>
        </div>

        {/* Train */}
        <div className="rv-train-layer" aria-hidden="true">
          <svg className="rv-train-svg" viewBox="0 0 200 36" fill="none" xmlns="http://www.w3.org/2000/svg">
            {/* Carriage 2 */}
            <rect x="0" y="8" width="56" height="22" rx="4" fill="#022C22" />
            <rect x="0" y="22" width="56" height="2.5" fill="#34D399" />
            <rect x="6" y="12" width="11" height="7" rx="1.5" fill="#34D399" />
            <rect x="22" y="12" width="11" height="7" rx="1.5" fill="#34D399" />
            <rect x="38" y="12" width="11" height="7" rx="1.5" fill="#34D399" />
            <circle cx="12" cy="30.5" r="2.5" fill="#022C22" />
            <circle cx="44" cy="30.5" r="2.5" fill="#022C22" />
            <rect x="56" y="19" width="6" height="2" fill="#18181B" fillOpacity="0.25" />

            {/* Carriage 1 */}
            <rect x="62" y="8" width="56" height="22" rx="4" fill="#022C22" />
            <rect x="62" y="22" width="56" height="2.5" fill="#34D399" />
            <rect x="68" y="12" width="11" height="7" rx="1.5" fill="#34D399" />
            <rect x="84" y="12" width="11" height="7" rx="1.5" fill="#34D399" />
            <rect x="100" y="12" width="11" height="7" rx="1.5" fill="#34D399" />
            <circle cx="74" cy="30.5" r="2.5" fill="#022C22" />
            <circle cx="106" cy="30.5" r="2.5" fill="#022C22" />
            <rect x="118" y="19" width="6" height="2" fill="#18181B" fillOpacity="0.25" />

            {/* Locomotive */}
            <path d="M124 8H165C175 8 184 14 186 23L187 30H124V8Z" fill="#022C22" />
            <path d="M124 22H185.5L186 24.5H124V22Z" fill="#34D399" />
            <rect x="130" y="12" width="11" height="7" rx="1.5" fill="#34D399" />
            <rect x="146" y="12" width="11" height="7" rx="1.5" fill="#34D399" />
            <path d="M162 12H170C173 12 175.5 14 176.5 17L177.5 19H162V12Z" fill="#34D399" />
            <circle cx="184" cy="27" r="2" fill="#34D399" />
            <polygon points="186,26 198,24 198,30 186,28" fill="#34D399" opacity="0.4" />
            <circle cx="136" cy="30.5" r="2.5" fill="#022C22" />
            <circle cx="168" cy="30.5" r="2.5" fill="#022C22" />
          </svg>
        </div>

        {/* Status text */}
        <div className="rv-status-layer">
          <span className="rv-text">
            Processing
            <span className="rv-dots">
              <span className="rv-dot rv-dot-1">.</span>
              <span className="rv-dot rv-dot-2">.</span>
              <span className="rv-dot rv-dot-3">.</span>
            </span>
          </span>
        </div>
      </div>

      <style>{`
        .rv-widget {
          width: 100%;
          height: 120px;
          position: relative;
          overflow: hidden;
          border-radius: 16px;
          background: #FFFFFF;
          border: 1px solid rgba(0, 0, 0, 0.05);
          box-sizing: border-box;
          container-type: inline-size;
        }
        .rv-track-layer {
          position: absolute;
          left: 0;
          right: 0;
          bottom: 24px;
          height: 20px;
          pointer-events: none;
        }
        .rv-track-svg {
          width: 100%;
          height: 100%;
          display: block;
        }
        .rv-train-layer {
          position: absolute;
          left: 0;
          bottom: 26px;
          width: 200px;
          height: 36px;
          will-change: transform, opacity;
          animation: rv-train-cycle 8s infinite;
          pointer-events: none;
        }
        .rv-train-svg {
          width: 200px;
          height: 36px;
          display: block;
        }
        .rv-status-layer {
          position: absolute;
          inset: 0;
          display: flex;
          align-items: center;
          justify-content: center;
          padding-bottom: 28px;
          pointer-events: none;
          animation: rv-text-cycle 8s infinite;
          will-change: opacity, transform;
        }
        .rv-text {
          position: relative;
          font-family: ui-monospace, "JetBrains Mono", monospace;
          font-size: 14px;
          letter-spacing: 0.05em;
          color: #18181B;
          display: inline-flex;
          align-items: baseline;
          user-select: none;
        }
        .rv-dots {
          display: inline-flex;
          position: absolute;
          left: 100%;
        }
        .rv-dot {
          display: inline-block;
          animation: rv-dot-pulse 1.5s infinite ease-in-out;
        }
        .rv-dot-1 { animation-delay: 0s; }
        .rv-dot-2 { animation-delay: 0.25s; }
        .rv-dot-3 { animation-delay: 0.5s; }

        /* 8s loop: train crosses in 3s, text shows, then text fades out as the train fades back in */
        @keyframes rv-train-cycle {
          0% {
            transform: translateX(-120px);
            opacity: 1;
            animation-timing-function: cubic-bezier(0.42, 0, 0.58, 1);
          }
          37.5% {
            transform: translateX(calc(100cqw + 20px));
            opacity: 1;
            animation-timing-function: step-end;
          }
          37.6% {
            transform: translateX(calc(100cqw + 20px));
            opacity: 0;
          }
          90% {
            transform: translateX(-120px);
            opacity: 0;
            animation-timing-function: ease-in;
          }
          100% {
            transform: translateX(-120px);
            opacity: 1;
          }
        }
        @keyframes rv-text-cycle {
          0%, 37.5% { opacity: 0; transform: translateY(2px); }
          45%, 90% { opacity: 1; transform: translateY(0); }
          100% { opacity: 0; transform: translateY(-2px); }
        }
        @keyframes rv-dot-pulse {
          0%, 100% { opacity: 0.2; transform: translateY(0); }
          50% { opacity: 1; transform: translateY(-1px); }
        }
        @media (prefers-reduced-motion: reduce) {
          .rv-train-layer { display: none; animation: none; }
          .rv-status-layer { opacity: 1; transform: none; animation: none; }
          .rv-dot { animation: none; opacity: 1; transform: none; }
        }
      `}</style>
    </>
  );
}