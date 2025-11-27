import { Sparkles } from "lucide-react";

export default function AIInsightPanel() {
  return (
    <div className="mx-8 mb-8">
      <div className="glass-card rounded-3xl p-8 border border-cyan-200/60 shadow-lg relative overflow-hidden">
        <div className="absolute -right-20 -top-20 w-40 h-40 bg-cyan-400 rounded-full blur-[80px] opacity-10 aura-glow"></div>

        <div className="flex items-start gap-4 relative z-10">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-cyan-400 to-cyan-600 flex items-center justify-center flex-shrink-0 shadow-lg shadow-cyan-500/30">
            <Sparkles className="w-6 h-6 text-white" strokeWidth={1.5} />
          </div>

          <div className="flex-1">
            <h3 className="text-xl font-semibold mb-3 gradient-text">metricx Insight</h3>
            <p className="text-base font-light text-neutral-700 leading-relaxed">
              Revenue increased by <span className="font-medium text-cyan-600">18.2%</span> while spend decreased by <span className="font-medium text-cyan-600">5.3%</span>, improving ROAS efficiency to <span className="font-medium text-cyan-600">3.63x</span>.
              CTR improved across Meta placements, with <span className="font-medium text-cyan-600">+22.1%</span> increase in clicks.
              Consider reallocating budget from TikTok to Meta for optimized performance.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

