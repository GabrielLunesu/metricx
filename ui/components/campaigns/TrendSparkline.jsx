/**
 * TrendSparkline - Responsive sparkline chart
 * 
 * @param {Object} props
 * @param {number[]} props.data - Array of values to plot
 * @param {string} props.color - Stroke color (default: blue)
 * @param {string} props.className - Additional CSS classes
 * @param {boolean} props.fillContainer - If true, fills parent container (default: false for inline use)
 */
export default function TrendSparkline({ 
  data = [], 
  color = '#60a5fa', 
  className = '',
  fillContainer = false 
}) {
  if (!data || data.length === 0) return null;
  
  const max = Math.max(...data);
  const min = Math.min(...data);
  
  // Add padding to prevent clipping at edges
  const padding = 5;
  const width = 100;
  const height = 100;
  
  const pts = data.map((v, i) => {
    const x = padding + (i / (data.length - 1)) * (width - padding * 2);
    const y = padding + (1 - ((v - min) / (max - min || 1))) * (height - padding * 2);
    return `${x},${y}`;
  }).join(' ');
  
  // Default size for inline use (collapsed cards)
  const sizeClass = fillContainer ? 'w-full h-full' : 'w-24 h-6';
  
  return (
    <svg 
      viewBox={`0 0 ${width} ${height}`} 
      preserveAspectRatio="none"
      className={`${sizeClass} ${className}`}
    >
      <polyline 
        fill="none" 
        stroke={color} 
        strokeWidth={fillContainer ? "1.5" : "2"} 
        strokeLinecap="round"
        strokeLinejoin="round"
        points={pts} 
      />
    </svg>
  );
}
