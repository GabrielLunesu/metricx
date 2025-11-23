import { Calendar, ChevronDown } from 'lucide-react';

export default function FinanceHeader({ title = 'Finance (P&L)', subtitle, currentRange = 'Last 7 Days' }) {
  return (
    <div className="flex  flex-col gap-4 lg:flex-row lg:items-center lg:justify-between mb-6">
      <div>
        <h2 className="text-2xl lg:text-3xl font-medium tracking-tight">{title}</h2>
        {subtitle ? <p className="text-slate-400 text-sm mt-1">{subtitle}</p> : null}
      </div>
      <div className="relative">
        <button className="rounded-full px-4 py-2 text-sm border border-slate-600/40 bg-slate-900/35 flex items-center gap-2">
          <Calendar size={16} className="text-cyan-300" />
          <span>{currentRange}</span>
          <ChevronDown size={16} className="text-slate-400" />
        </button>
      </div>
    </div>
  );
}
