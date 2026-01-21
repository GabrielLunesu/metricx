/**
 * UpgradeModal - Modal prompting users to upgrade from free to paid tier
 *
 * WHAT: Shows upgrade prompt when free tier users try to access pro features
 * WHY: Convert free users to paid by showing value proposition
 *
 * REFERENCES:
 *   - docs-arch/living-docs/BILLING.md
 *   - ui/lib/workspace.js (createCheckout)
 */
'use client';

import { useRouter } from "next/navigation";
import { X, Zap, BarChart2, Users, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";

const FEATURES = [
  { icon: BarChart2, label: "Unlimited ad accounts", description: "Connect all your Meta & Google accounts" },
  { icon: Zap, label: "Full Analytics & Finance", description: "Deep dive into performance and P&L" },
  { icon: Sparkles, label: "AI Copilot", description: "Get AI-powered insights and recommendations" },
  { icon: Users, label: "Team collaboration", description: "Invite up to 10 team members" },
];

export function UpgradeModal({ open, onClose, feature }) {
  const router = useRouter();

  const handleUpgrade = () => {
    onClose();
    router.push('/subscribe');
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md bg-white">
        <DialogHeader>
          <DialogTitle className="text-xl flex items-center gap-2">
            <Zap className="w-5 h-5 text-amber-500" />
            Upgrade to Unlock {feature}
          </DialogTitle>
          <DialogDescription>
            Get full access to all features with our Starter plan.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 py-4">
          {FEATURES.map((item) => (
            <div key={item.label} className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-cyan-50 flex items-center justify-center flex-shrink-0">
                <item.icon className="w-4 h-4 text-cyan-600" />
              </div>
              <div>
                <p className="font-medium text-neutral-900 text-sm">{item.label}</p>
                <p className="text-xs text-neutral-500">{item.description}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="flex flex-col gap-2 pt-2">
          <Button onClick={handleUpgrade} className="w-full bg-cyan-600 hover:bg-cyan-700">
            Upgrade Now - $29.99/month
          </Button>
          <p className="text-xs text-center text-neutral-500">
            Or save 45% with annual billing ($196/year)
          </p>
        </div>
      </DialogContent>
    </Dialog>
  );
}
