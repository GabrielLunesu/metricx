export default function CampaignTableHeader() {
  return (
    <div className="px-6 md:px-8 py-3 border-b border-slate-100 bg-slate-50/80 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
      <div className="grid grid-cols-[40px_minmax(0,3fr)_minmax(0,1.2fr)_minmax(0,1.4fr)_minmax(0,1.4fr)_minmax(0,0.9fr)_minmax(0,1fr)] gap-4 items-center">
        <div className="flex items-center">
          <input
            type="checkbox"
            className="custom-checkbox cursor-pointer"
            aria-label="Select all campaigns"
          />
        </div>
        <div>Campaign</div>
        <div>Platform</div>
        <div className="text-right">Spend</div>
        <div className="text-right">Revenue</div>
        <div className="text-right">ROAS</div>
        <div className="text-right">Trend</div>
      </div>
    </div>
  );
}
