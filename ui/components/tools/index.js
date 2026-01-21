/**
 * Calculator Tools Index
 *
 * WHAT: Exports all calculator/tool components
 * WHY: Single import point for calculator tools
 *
 * @example
 * import { ROASCalculator, roasCalculatorData } from '@/components/tools';
 */

export {
  CalculatorLayout,
  CalculatorInput,
  CalculatorResult,
} from "./CalculatorLayout";

export { ROASCalculator, roasCalculatorData } from "./ROASCalculator";
export { CPACalculator, cpaCalculatorData } from "./CPACalculator";
export { CPMCalculator, cpmCalculatorData } from "./CPMCalculator";
export { CTRCalculator, ctrCalculatorData } from "./CTRCalculator";
export { AdSpendPlanner, adSpendPlannerData } from "./AdSpendPlanner";
export { BreakEvenCalculator, breakEvenCalculatorData } from "./BreakEvenCalculator";

/**
 * All calculator data for use in page generation.
 */
export const allCalculators = [
  {
    name: "ROAS Calculator",
    slug: "roas-calculator",
    description: "Calculate your Return on Ad Spend instantly",
    component: "ROASCalculator",
  },
  {
    name: "CPA Calculator",
    slug: "cpa-calculator",
    description: "Calculate your Cost Per Acquisition",
    component: "CPACalculator",
  },
  {
    name: "CPM Calculator",
    slug: "cpm-calculator",
    description: "Calculate Cost Per Thousand Impressions",
    component: "CPMCalculator",
  },
  {
    name: "CTR Calculator",
    slug: "ctr-calculator",
    description: "Calculate your Click-Through Rate",
    component: "CTRCalculator",
  },
  {
    name: "Ad Spend Planner",
    slug: "ad-spend-calculator",
    description: "Plan your advertising budget based on goals",
    component: "AdSpendPlanner",
  },
  {
    name: "Break-even ROAS Calculator",
    slug: "break-even-roas-calculator",
    description: "Find your break-even ROAS threshold",
    component: "BreakEvenCalculator",
  },
];
