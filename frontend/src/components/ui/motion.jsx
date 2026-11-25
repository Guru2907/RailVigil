import { useEffect, useRef, useState } from "react";
import { animate, motion, useInView, useReducedMotion } from "motion/react";

// The app's motion in one place: one easing, short durations, and a still
// fallback for people who ask for reduced motion. Used on the landing page;
// working pages only use the CSS state transitions in index.css.

export const EASE = [0.23, 1, 0.32, 1];

// Content that rises slightly into place the first time it scrolls into view.
export function Reveal({ children, delay = 0, className = "" }) {
  const reduce = useReducedMotion();
  if (reduce) return <div className={className}>{children}</div>;
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, transform: "translateY(12px)" }}
      whileInView={{ opacity: 1, transform: "translateY(0px)" }}
      viewport={{ once: true, amount: 0.2 }}
      transition={{ duration: 0.5, ease: EASE, delay }}
    >
      {children}
    </motion.div>
  );
}

// A number that counts up once when it first appears. Shows the final value
// straight away under reduced motion, and "–" when there is no value.
export function CountUp({ value, duration = 1.1, format = (n) => Math.round(n).toLocaleString("en-IN") }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true });
  const reduce = useReducedMotion();
  const [shown, setShown] = useState(0);
  const known = typeof value === "number" && Number.isFinite(value);

  useEffect(() => {
    if (!known || !inView) return undefined;
    if (reduce) {
      setShown(value);
      return undefined;
    }
    const controls = animate(0, value, { duration, ease: EASE, onUpdate: setShown });
    return () => controls.stop();
  }, [known, inView, reduce, value, duration]);

  return (
    <span ref={ref} className="tabular">
      {known ? format(shown) : "–"}
    </span>
  );
}
