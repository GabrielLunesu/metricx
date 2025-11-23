export default function StatusPill({ status }) {
  const value = status || '';
  const normalized = value.toLowerCase();

  let classes =
    'bg-slate-100 text-slate-600 border border-slate-200';

  if (normalized === 'active') {
    classes = 'bg-emerald-50 text-emerald-700 border border-emerald-100';
  } else if (normalized === 'paused') {
    classes = 'bg-amber-50 text-amber-700 border border-amber-100';
  } else if (normalized === 'learning') {
    classes = 'bg-sky-50 text-sky-700 border border-sky-100';
  }

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-md text-[10px] font-medium ${classes}`}
    >
      {value}
    </span>
  );
}
