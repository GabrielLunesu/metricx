"use client";
import { useEffect, useState } from "react";
import { fetchWorkspaceKpis } from "../../../../lib/api";
import { currentUser } from "../../../../lib/workspace";

export default function VisitorsChartCard() {
  const [revenueData, setRevenueData] = useState(null);
  const [conversionsData, setConversionsData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [dayLabels, setDayLabels] = useState([]);

  useEffect(() => {
    let mounted = true;

    // Generate dynamic day labels for last 7 days
    const getDayLabels = () => {
      const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
      const labels = [];
      const today = new Date();
      
      for (let i = 6; i >= 0; i--) {
        const date = new Date(today);
        date.setDate(date.getDate() - i);
        labels.push(days[date.getDay()]);
      }
      
      return labels;
    };

    setDayLabels(getDayLabels());

    currentUser().then(user => {
      if (!mounted || !user) return;
      
      // Fetch last 7 days of revenue and conversions data
      return fetchWorkspaceKpis({
        workspaceId: user.workspace_id,
        metrics: ['revenue', 'conversions'],
        lastNDays: 7,
        dayOffset: 0,
        compareToPrevious: false,
        sparkline: true
      });
    }).then(data => {
      if (!mounted || !data) return;
      
      const revenueMetric = data.find(m => m.key === 'revenue');
      const conversionsMetric = data.find(m => m.key === 'conversions');
      
      setRevenueData(revenueMetric);
      setConversionsData(conversionsMetric);
      setLoading(false);
    }).catch(err => {
      console.error('Failed to fetch visitors data:', err);
      setLoading(false);
    });
    
    return () => { mounted = false; };
  }, []);

  // Calculate bar heights based on revenue data
  const getBarHeights = () => {
    if (!revenueData || !revenueData.sparkline || revenueData.sparkline.length === 0) {
      return ['45%', '60%', '52%', '75%', '85%', '100%', '68%']; // Fallback
    }

    const values = revenueData.sparkline.map(sp => sp.value || 0);
    const maxValue = Math.max(...values);
    
    if (maxValue === 0) {
      return values.map(() => '10%'); // Show minimal height if all zeros
    }

    return values.map(val => {
      const percentage = (val / maxValue) * 100;
      return `${Math.max(percentage, 10)}%`; // Minimum 10% height for visibility
    });
  };

  const barHeights = getBarHeights();
  const maxIndex = barHeights.indexOf(barHeights.reduce((max, current) => 
    parseFloat(current) > parseFloat(max) ? current : max
  ));

  // Calculate totals
  const totalRevenue = revenueData?.value || 0;
  const totalConversions = conversionsData?.value || 0;

  return (
    <div className="glass-card rounded-3xl p-8 border border-neutral-200/60 shadow-lg">
      <h3 className="text-xl font-semibold text-neutral-900 mb-6">Revenue - Last 7 Days</h3>
      
      {loading ? (
        <div className="h-48 flex items-center justify-center">
          <div className="w-8 h-8 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin"></div>
        </div>
      ) : (
        <>
          <div className="h-48 flex items-end justify-between gap-2">
            {barHeights.map((height, idx) => (
              <div
                key={idx}
                className={`flex-1 bg-gradient-to-t from-cyan-400 to-cyan-200 rounded-t-lg transition-all duration-300 ${
                  idx === maxIndex ? 'opacity-100' : 'opacity-60'
                }`}
                style={{ height }}
              ></div>
            ))}
          </div>
          <div className="mt-4 flex items-center justify-between text-xs text-neutral-500">
            {dayLabels.map((day, idx) => (
              <span key={idx}>{day}</span>
            ))}
          </div>
          <div className="mt-6 flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-cyan-400"></div>
              <span className="text-xs text-neutral-600">
                Revenue: ${totalRevenue.toLocaleString(undefined, { maximumFractionDigits: 0 })}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-cyan-600"></div>
              <span className="text-xs text-neutral-600">
                Conversions: {totalConversions.toLocaleString(undefined, { maximumFractionDigits: 0 })}
              </span>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

