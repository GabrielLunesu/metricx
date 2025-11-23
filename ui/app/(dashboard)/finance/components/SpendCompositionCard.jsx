"use client";

import { useMemo } from "react";
import { PieChart, Pie, Cell, Label, ResponsiveContainer, Tooltip } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function SpendCompositionCard({
    composition,
    rows,
    excludedRows,
    totalRevenue,
    totalSpend,
}) {
    // Process data for the chart
    const { data, totalActiveSpend } = useMemo(() => {
        if (!composition || !rows) return { data: [], totalActiveSpend: 0 };

        const activeData = composition.map((item) => {
            const matchingRow = rows.find((r) => r.category === item.label);
            const isExcluded = matchingRow && excludedRows.has(matchingRow.id);
            return {
                name: item.label,
                value: isExcluded ? 0 : item.value,
                originalValue: item.value,
                isExcluded,
                color: item.color, // Assuming color might be passed, or we assign it
            };
        });

        const total = activeData.reduce((sum, item) => sum + item.value, 0);
        return { data: activeData, totalActiveSpend: total };
    }, [composition, rows, excludedRows]);

    // Calculate margin
    const marginPct = useMemo(() => {
        if (!totalRevenue || totalRevenue === 0) return 0;
        return Math.round(((totalRevenue - totalSpend) / totalRevenue) * 100);
    }, [totalRevenue, totalSpend]);

    // Colors matching the design/previous implementation
    const COLORS = [
        '#06B6D4', // Cyan
        '#22D3EE', // Light Cyan
        '#3B82F6', // Blue
        '#6366F1', // Indigo
        '#8B5CF6', // Purple
        '#A855F7', // Purple Light
        '#EC4899', // Pink
    ];

    if (!composition || composition.length === 0) {
        return null;
    }

    return (
        <Card className="h-full border-slate-200 shadow-sm">
            <CardHeader className="pb-2">
                <CardTitle className="text-lg font-semibold text-slate-800">
                    Spend Composition
                </CardTitle>
            </CardHeader>
            <CardContent>
                <div className="h-[240px] w-full relative">
                    <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                            <Pie
                                data={data}
                                cx="50%"
                                cy="50%"
                                innerRadius={70}
                                outerRadius={95}
                                paddingAngle={2}
                                dataKey="value"
                                stroke="none"
                            >
                                {data.map((entry, index) => (
                                    <Cell
                                        key={`cell-${index}`}
                                        fill={COLORS[index % COLORS.length]}
                                        className="stroke-background hover:opacity-80 transition-opacity"
                                    />
                                ))}
                                <Label
                                    content={({ viewBox }) => {
                                        if (viewBox && "cx" in viewBox && "cy" in viewBox) {
                                            return (
                                                <text
                                                    x={viewBox.cx}
                                                    y={viewBox.cy}
                                                    textAnchor="middle"
                                                    dominantBaseline="middle"
                                                >
                                                    <tspan
                                                        x={viewBox.cx}
                                                        y={viewBox.cy - 15}
                                                        className="fill-cyan-500 text-sm font-medium"
                                                    >
                                                        Margin
                                                    </tspan>
                                                    <tspan
                                                        x={viewBox.cx}
                                                        y={viewBox.cy + 20}
                                                        className="fill-foreground text-4xl font-bold"
                                                    >
                                                        {marginPct}%
                                                    </tspan>
                                                </text>
                                            );
                                        }
                                    }}
                                />
                            </Pie>
                            <Tooltip
                                formatter={(value) => [`$${value.toLocaleString()}`, 'Spend']}
                                contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                            />
                        </PieChart>
                    </ResponsiveContainer>
                </div>

                <div className="mt-8 space-y-4">
                    {data.map((item, index) => (
                        <div
                            key={item.name}
                            className={`flex items-center justify-between text-base ${item.isExcluded ? "opacity-40" : ""
                                }`}
                        >
                            <div className="flex items-center gap-3">
                                <div
                                    className="h-3 w-3 rounded-full"
                                    style={{
                                        backgroundColor: item.isExcluded
                                            ? "#9CA3AF"
                                            : COLORS[index % COLORS.length],
                                    }}
                                />
                                <span className={item.isExcluded ? "line-through text-slate-400" : "text-slate-600"}>
                                    {item.name}
                                </span>
                            </div>
                            <span className="font-medium text-slate-600">
                                ${item.originalValue.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                            </span>
                        </div>
                    ))}
                </div>
            </CardContent>
        </Card>
    );
}
