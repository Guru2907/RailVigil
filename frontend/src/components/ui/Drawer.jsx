import { useEffect, useRef } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { X } from "lucide-react";

// A panel that slides in from the right for details, keeping the list behind it
// in view. Closes on Escape and on a click outside; focus moves in on open and
// returns to the trigger on close.
export function Drawer({ open, onClose, title, children, footer, width = "max-w-md" }) {
  const panel = useRef(null);
  const reduce = useReducedMotion();

  useEffect(() => {
    if (!open) return undefined;
    const previous = document.activeElement;
    panel.current?.focus();
    const onKey = (e) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      previous?.focus?.();
    };
  }, [open, onClose]);

  const hidden = reduce ? { opacity: 0 } : { opacity: 0, transform: "translateX(100%)" };
  const shown = reduce ? { opacity: 1 } : { opacity: 1, transform: "translateX(0%)" };

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[1200]">
          <motion.div
            className="absolute inset-0 bg-canvas-2/70"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
            aria-hidden
          />
          <motion.aside
            ref={panel}
            role="dialog"
            aria-modal="true"
            aria-label={title}
            tabIndex={-1}
            className={`absolute inset-y-0 right-0 flex w-full ${width} flex-col border-l border-line bg-surface text-ink outline-none`}
            initial={hidden}
            animate={shown}
            exit={hidden}
            transition={{ duration: 0.32, ease: [0.32, 0.72, 0, 1] }}
          >
            <header className="flex h-14 shrink-0 items-center justify-between gap-3 border-b border-line px-5">
              <h2 className="truncate text-sm font-semibold">{title}</h2>
              <button
                type="button"
                onClick={onClose}
                aria-label="Close panel"
                className="press -mr-2 flex h-10 w-10 items-center justify-center rounded-lg text-muted hover:bg-surface-2 hover:text-ink"
              >
                <X className="h-4 w-4" aria-hidden />
              </button>
            </header>
            <div className="min-h-0 flex-1 overflow-y-auto p-5">{children}</div>
            {footer && <footer className="shrink-0 border-t border-line p-4">{footer}</footer>}
          </motion.aside>
        </div>
      )}
    </AnimatePresence>
  );
}
