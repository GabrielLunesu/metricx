"use client";
import { useState, useEffect } from "react";
import { X, Search, Check } from "lucide-react";
import { fetchWorkspaceCampaigns } from "@/lib/api";

export default function FilterModal({
    isOpen,
    onClose,
    onSelect,
    workspaceId,
    selectedProvider,
    selectedCampaignId
}) {
    const [campaigns, setCampaigns] = useState([]);
    const [loading, setLoading] = useState(false);
    const [searchQuery, setSearchQuery] = useState("");

    useEffect(() => {
        if (!isOpen || !workspaceId) return;

        let mounted = true;
        setLoading(true);

        fetchWorkspaceCampaigns({
            workspaceId,
            provider: selectedProvider === 'all' ? null : selectedProvider,
            status: 'active'
        })
            .then((data) => {
                if (!mounted) return;
                setCampaigns(data.campaigns || []);
                setLoading(false);
            })
            .catch((err) => {
                console.error("Failed to fetch campaigns for filter:", err);
                if (mounted) setLoading(false);
            });

        return () => { mounted = false; };
    }, [isOpen, workspaceId, selectedProvider]);

    if (!isOpen) return null;

    const filteredCampaigns = campaigns.filter(c =>
        c.name.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/20 backdrop-blur-sm animate-fade-in">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden border border-neutral-100 animate-scale-up">

                {/* Header */}
                <div className="p-4 border-b border-neutral-100 flex justify-between items-center">
                    <h3 className="font-semibold text-slate-800">Filter by Campaign</h3>
                    <button onClick={onClose} className="p-1 rounded-full hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Search */}
                <div className="p-4 border-b border-neutral-50 bg-slate-50/50">
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                        <input
                            type="text"
                            placeholder="Search campaigns..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full pl-9 pr-4 py-2 rounded-xl border border-slate-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500/20 focus:border-cyan-500 transition-all"
                            autoFocus
                        />
                    </div>
                </div>

                {/* List */}
                <div className="max-h-[300px] overflow-y-auto p-2">
                    {loading ? (
                        <div className="p-8 text-center">
                            <div className="w-6 h-6 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                            <p className="text-xs text-slate-400">Loading campaigns...</p>
                        </div>
                    ) : filteredCampaigns.length === 0 ? (
                        <div className="p-8 text-center text-slate-400 text-sm">
                            No campaigns found.
                        </div>
                    ) : (
                        <div className="space-y-1">
                            <button
                                onClick={() => onSelect(null)}
                                className={`w-full text-left px-3 py-2 rounded-lg text-sm flex items-center justify-between group transition-colors ${!selectedCampaignId ? 'bg-cyan-50 text-cyan-700 font-medium' : 'hover:bg-slate-50 text-slate-700'
                                    }`}
                            >
                                <span>All Campaigns</span>
                                {!selectedCampaignId && <Check className="w-4 h-4 text-cyan-600" />}
                            </button>

                            {filteredCampaigns.map((campaign) => (
                                <button
                                    key={campaign.id}
                                    onClick={() => onSelect(campaign)}
                                    className={`w-full text-left px-3 py-2 rounded-lg text-sm flex items-center justify-between group transition-colors ${selectedCampaignId === campaign.id ? 'bg-cyan-50 text-cyan-700 font-medium' : 'hover:bg-slate-50 text-slate-700'
                                        }`}
                                >
                                    <div className="truncate pr-2">
                                        <div className="truncate">{campaign.name}</div>
                                        <div className="text-[10px] text-slate-400 font-normal capitalize">{campaign.platform}</div>
                                    </div>
                                    {selectedCampaignId === campaign.id && <Check className="w-4 h-4 text-cyan-600 flex-shrink-0" />}
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
