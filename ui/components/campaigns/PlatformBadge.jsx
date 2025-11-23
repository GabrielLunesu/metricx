import { Facebook, Instagram, Youtube, Search } from "lucide-react";

export default function PlatformBadge({ platform }) {
  const normalized =
    platform?.toLowerCase().replace(/\s+ads?$/i, "").trim() || "";

  let label = platform || "—";
  let dotColor = "bg-slate-400";
  let Icon = null;

  if (normalized === "meta" || normalized === "facebook") {
    label = "Meta";
    dotColor = "bg-blue-500";
    Icon = Facebook;
  } else if (normalized === "instagram") {
    label = "Meta";
    dotColor = "bg-purple-500";
    Icon = Instagram;
  } else if (normalized === "google") {
    label = "Google";
    dotColor = "bg-blue-500";
    Icon = Search;
  } else if (normalized === "youtube") {
    label = "YouTube";
    dotColor = "bg-red-500";
    Icon = Youtube;
  }

  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-slate-200 bg-white text-[10px] font-medium text-slate-600">
      <span className={`w-1 h-1 rounded-full ${dotColor}`} />
      {Icon && <Icon className="w-3 h-3 text-slate-500" />}
      <span>{label}</span>
    </span>
  );
}
