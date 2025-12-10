"use client"

import * as React from "react"
import { Area, AreaChart, Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts"

import {
    ChartContainer,
    ChartTooltip,
    ChartTooltipContent,
    ChartLegend,
    ChartLegendContent
} from "@/components/ui/chart"

export function MetricxChart({
    data,
    config,
    type = 'area', // 'area' | 'bar'
    xAxisKey = 'date',
    height = "300px",
    className,
    isSingleDay = false
}) {
    // Guard: if config is missing, show placeholder
    if (!config || typeof config !== 'object') {
        console.warn('MetricxChart: config prop is required');
        return <div style={{ height }} className={className} />;
    }

    // Extract series keys from config
    const seriesKeys = Object.keys(config).filter(key => key !== 'label' && key !== 'color');

    const ChartComponent = type === 'bar' ? BarChart : AreaChart;

    return (
        <div style={{ height, width: '100%' }} className={className}>
            <ChartContainer config={config} className="h-full w-full aspect-auto">
                <ChartComponent
                    data={data}
                    margin={{
                        left: 0,
                        right: 0,
                        top: 10,
                        bottom: 0,
                    }}
                >
                    <defs>
                        {seriesKeys.map(key => (
                            <linearGradient key={key} id={`fill${key}`} x1="0" y1="0" x2="0" y2="1">
                                <stop
                                    offset="5%"
                                    stopColor={`var(--color-${key})`}
                                    stopOpacity={0.8}
                                />
                                <stop
                                    offset="95%"
                                    stopColor={`var(--color-${key})`}
                                    stopOpacity={0.1}
                                />
                            </linearGradient>
                        ))}
                    </defs>
                    <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="var(--border)" opacity={0.4} />
                    <YAxis
                        domain={[0, 'auto']}
                        tickLine={false}
                        axisLine={false}
                        tickMargin={8}
                        width={60}
                        tickFormatter={(value) => {
                            if (value >= 1000) {
                                return `$${(value / 1000).toFixed(1)}k`;
                            }
                            return `$${value}`;
                        }}
                    />
                    <XAxis
                        dataKey={xAxisKey}
                        tickLine={false}
                        axisLine={false}
                        tickMargin={8}
                        minTickGap={isSingleDay ? 20 : 32}
                        tickFormatter={(value) => {
                            const date = new Date(value);
                            if (!isNaN(date.getTime())) {
                                if (isSingleDay) {
                                    // Show HH:MM in user's local timezone for intraday (15-min intervals)
                                    return date.toLocaleTimeString('en-US', {
                                        hour: '2-digit',
                                        minute: '2-digit',
                                        hour12: false
                                    });
                                }
                                return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                            }
                            return value;
                        }}
                    />
                    <ChartTooltip
                        cursor={false}
                        content={
                            <ChartTooltipContent
                                indicator="line"
                                className="bg-white border border-slate-100 shadow-xl rounded-xl w-[180px]"
                                labelFormatter={(value) => {
                                    const date = new Date(value);
                                    if (!isNaN(date.getTime())) {
                                        return date.toLocaleDateString("en-US", {
                                            month: "long",
                                            day: "numeric",
                                            year: "numeric",
                                            ...(isSingleDay ? { hour: '2-digit', minute: '2-digit', hour12: false } : {})
                                        });
                                    }
                                    return value;
                                }}
                            />
                        }
                    />

                    {type === 'area' ? (
                        seriesKeys.map(key => (
                            <Area
                                key={key}
                                dataKey={key}
                                type="monotone"
                                fill={`url(#fill${key})`}
                                fillOpacity={0.4}
                                stroke={`var(--color-${key})`}
                                strokeWidth={2}
                                stackId={config[key]?.stackId} // Optional stacking
                                dot={isSingleDay} // Show dots for intraday to mark actual data points
                                connectNulls={true} // Connect across null gaps to show continuous line
                            />
                        ))
                    ) : (
                        seriesKeys.map(key => (
                            <Bar
                                key={key}
                                dataKey={key}
                                fill={`var(--color-${key})`}
                                radius={[4, 4, 0, 0]}
                                maxBarSize={50}
                            />
                        ))
                    )}
                </ChartComponent>
            </ChartContainer>
        </div>
    )
}
