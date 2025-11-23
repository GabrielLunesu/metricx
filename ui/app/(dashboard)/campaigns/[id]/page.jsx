'use client'

// page for ad set detail (ad level)

import { useEffect, useState, useTransition } from 'react';
import { useParams, useRouter } from 'next/navigation';
import DetailHeader from '../../../../components/campaigns/DetailHeader';
import EntityTable from '../../../../components/campaigns/EntityTable';
import RulesPanel from '../../../../components/campaigns/RulesPanel';
import { campaignsApiClient, campaignsAdapter } from '../../../../lib';

export default function CampaignDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params?.id;
  // TODO: Get workspace ID from auth context
  const workspaceId = "1e72698a-1f6c-4abb-9b99-48dba86508ce";
  
  const [filters, setFilters] = useState({ 
    timeframe: '7d',
    status: 'active',
    sortBy: 'roas',
    sortDir: 'desc',
    platform: null,
  });
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    if (!id) return;
    let isMounted = true;
    startTransition(() => {
      campaignsApiClient.fetchEntityPerformance({
        workspaceId,
        entityLevel: 'adset',
        parentId: id,
        timeframe: filters.timeframe,
        status: filters.status,
        sortBy: filters.sortBy,
        sortDir: filters.sortDir,
        platform: filters.platform,
        page: 1,
        pageSize: 50,
      })
        .then((payload) => {
          if (!isMounted) return;
          setData(campaignsAdapter.adaptEntityPerformance(payload));
          setError(null);
        })
        .catch((err) => {
          if (!isMounted) return;
          console.error('Failed to load ad sets', err);
          setError(err);
        });
    });
    return () => {
      isMounted = false;
    };
  }, [id, filters, workspaceId]);

  if (!id) {
    return <div className="text-slate-400">No campaign selected.</div>;
  }

  const rows = data?.rows || [];
  const meta = data?.meta;

  const handleAdSetClick = (adsetId) => {
    // Navigate to ad set detail page
    router.push(`/campaigns/${id}/${adsetId}`);
  };

  return (
    <div className="max-w-[1400px] mx-auto px-4 md:px-0">
      <DetailHeader
        name={meta?.title || 'Campaign'}
        platform={rows[0]?.platform || '—'}
        status={rows[0]?.status || '—'}
        timeframe={filters.timeframe}
        subtitle={meta?.subtitle}
        loading={isPending}
      />
      <div className="mb-4" />
      <EntityTable
        title="Ad Sets"
        rows={rows}
        loading={isPending}
        error={error}
        onRowClick={handleAdSetClick}
      />
      {/* <RulesPanel /> */}
    </div>
  );
}
