"use client";

import { useMemo } from "react";
import { Pie, PieChart } from "recharts";
import { TrendingUp } from "lucide-react";
import {
    Card,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import {
    ChartContainer,
    ChartTooltip,
    ChartTooltipContent,
} from "@/components/ui/chart";

export default function SpendCompositionCard({
    composition,
    rows,
    excludedRows,
    totalRevenue,
    totalSpend,
    selectedMonth,
}) {
    // Direct color palette (blue shades)
    const colors = [
        "hsl(220, 70%, 50%)",  // Blue
        "hsl(200, 70%, 60%)",  // Light blue  
        "hsl(240, 70%, 50%)",  // Deep blue
        "hsl(180, 70%, 50%)",  // Cyan
        "hsl(260, 70%, 50%)",  // Purple
    ];

    // Process data for the chart
    const { data, chartConfig } = useMemo(() => {
        if (!composition || !rows) return { data: [], chartConfig: {} };

        // Create chartConfig
        const config = {
            visitors: {
                label: "Spend",
            },
        };

        // Create data array
        const activeData = composition.map((item, index) => {
            const matchingRow = rows.find((r) => r.category === item.label);
            const isExcluded = matchingRow && excludedRows.has(matchingRow.id);
            const key = `category_${index}`;
            const color = colors[index % colors.length];

            // Add to config
            config[key] = {
                label: item.label,
                color: color,
            };

            return {
                browser: key,
                visitors: isExcluded ? 0 : item.value,
                originalValue: item.value,
                originalLabel: item.label,
                isExcluded,
                fill: color,
            };
        });

        return { data: activeData, chartConfig: config };
    }, [composition, rows, excludedRows, colors]);

    // Calculate margin
    const marginPct = useMemo(() => {
        if (!totalRevenue || totalRevenue === 0) return 0;
        return Math.round(((totalRevenue - totalSpend) / totalRevenue) * 100);
    }, [totalRevenue, totalSpend]);

    const monthNames = ["January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"];
    const monthName = selectedMonth ? monthNames[selectedMonth - 1] : "";

    if (!composition || composition.length === 0) {
        return null;
    }

    return (
        <Card className="h-full flex flex-col border-slate-200 shadow-sm">
            <CardHeader className="items-center pb-2">
                <div className="flex items-center gap-2">
                    <CardTitle className="text-base font-semibold text-slate-900">
                        Spend Composition
                    </CardTitle>
                    {monthName && (
                        <span className="text-sm font-medium text-blue-600 bg-blue-50 px-2.5 py-0.5 rounded-full">
                            {monthName}
                        </span>
                    )}
                </div>
                <CardDescription className="text-xs text-slate-500 mt-1">
                    Breakdown of your advertising and operational costs
                </CardDescription>
            </CardHeader>

            <CardContent className="flex-1 pb-0">
                <ChartContainer
                    config={chartConfig}
                    className="mx-auto aspect-square max-h-[250px]"
                >
                    <PieChart>
                        <ChartTooltip
                            cursor={false}
                            content={<ChartTooltipContent hideLabel />}
                        />
                        <Pie
                            data={data}
                            dataKey="visitors"
                            nameKey="browser"
                        />
                    </PieChart>
                </ChartContainer>
            </CardContent>

            <CardFooter className="flex-col gap-4 text-sm ">
                {/* Margin Display */}
                <div className="flex items-center gap-2 font-semibold leading-none">
                    <TrendingUp className="h-4 w-4 text-emerald-500" />
                    <span className="text-slate-700 text-xl">Margin: </span>
                    <span className="text-2xl font-extrabold text-emerald-600">{marginPct}%</span>
                </div>

                {/* Legend */}
                <div className="w-full space-y-2">
                    {data.map((item, index) => {
                        const label = item.originalLabel;
                        const color = colors[index % colors.length];

                        return (
                            <div
                                key={item.browser}
                                className={`flex items-center justify-between text-sm ${item.isExcluded ? "opacity-40" : ""
                                    }`}
                            >
                                <div className="flex items-center gap-2">
                                    <div
                                        className="h-2.5 w-2.5 rounded-full shrink-0"
                                        style={{
                                            backgroundColor: item.isExcluded
                                                ? "#9CA3AF"
                                                : color,
                                        }}
                                    />
                                    <span
                                        className={
                                            item.isExcluded
                                                ? "line-through text-slate-400 text-xs"
                                                : "text-slate-600 text-xs"
                                        }
                                    >
                                        {label}
                                    </span>
                                </div>
                                <span className="font-mono text-xs text-slate-700 font-semibold">
                                    ${item.originalValue.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                                </span>
                            </div>
                        );
                    })}
                </div>
            </CardFooter>
        </Card>
    );
}
