// Generic card surface wrapper used across the dashboard
// Keep this presentational: it only renders UI and children.
import { cn } from "../lib/cn";

export default function Card({ className, children }) {
  return (
    <div
      className={cn(
        "rounded-xl p-4 md:p-6 card-surface shadow-soft",
        "border border-slate-800/60 bg-white backdrop-blur",
        className
      )}
    >
      {children}
    </div>
  );
}
