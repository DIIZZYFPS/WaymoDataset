import { useQuery } from "@tanstack/react-query";

// Automatically use production API in production, localhost in development
const API_BASE = import.meta.env.PROD
  ? "https://waymodataset-production.up.railway.app"
  : "http://localhost:8000";

// Phase 2 Optimization: Single batched dashboard summary endpoint
export const useDashboardSummary = () => {
  return useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/api/dashboard-summary`);
      if (!res.ok) throw new Error("Failed to fetch dashboard summary");
      return res.json();
    },
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
    gcTime: 10 * 60 * 1000, // Keep in cache for 10 minutes
  });
};

// Hooks that derive from batched summary
export const useStats = () => {
  const summary = useDashboardSummary();
  return {
    data: summary.data?.stats,
    isLoading: summary.isLoading,
    error: summary.error,
  };
};

export const useFilters = () => {
  const summary = useDashboardSummary();
  return {
    data: summary.data?.filters,
    isLoading: summary.isLoading,
    error: summary.error,
  };
};

export const usePieChartData = () => {
  const summary = useDashboardSummary();
  return {
    data: summary.data?.charts?.pie,
    isLoading: summary.isLoading,
    error: summary.error,
  };
};

export const useHistogramData = () => {
  return useQuery({
    queryKey: ["charts", "histogram"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/api/charts/histogram`);
      if (!res.ok) throw new Error("Failed to fetch histogram data");
      return res.json();
    },
  });
};

export const useBoxPlotData = () => {
  return useQuery({
    queryKey: ["charts", "boxplot"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/api/charts/box-plot-data`);
      if (!res.ok) throw new Error("Failed to fetch box plot data");
      return res.json();
    },
  });
};

export const useTopFilesData = () => {
  return useQuery({
    queryKey: ["charts", "topfiles"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/api/charts/top-files`);
      if (!res.ok) throw new Error("Failed to fetch top files data");
      return res.json();
    },
  });
};

export const useIntentData = () => {
  const summary = useDashboardSummary();
  return {
    data: summary.data?.charts?.intent,
    isLoading: summary.isLoading,
    error: summary.error,
  };
};

export const useScatterData = () => {
  return useQuery({
    queryKey: ["charts", "scatter"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/api/charts/scatter`);
      if (!res.ok) throw new Error("Failed to fetch scatter data");
      return res.json();
    },
  });
};

export const usePreFlaggedData = (page: number) => {
  return useQuery({
    queryKey: ["preflagged", page],
    queryFn: async () => {
      const res = await fetch(
        `${API_BASE}/api/query/pre-flagged?page=${page}`
      );
      if (!res.ok) throw new Error("Failed to fetch pre-flagged data");
      return res.json();
    },
  });
};

export const useFrameDetail = (frameId: string | null) => {
  return useQuery({
    queryKey: ["frame", frameId],
    queryFn: async () => {
      if (!frameId) return null;
      const res = await fetch(`${API_BASE}/api/frame/${frameId}`);
      if (!res.ok) throw new Error("Failed to fetch frame detail");
      return res.json();
    },
    enabled: !!frameId,
  });
};

export const useAdHocQuery = (queryName: string | null) => {
  return useQuery({
    queryKey: ["adhoc", queryName],
    queryFn: async () => {
      if (!queryName) return [];
      const res = await fetch(
        `${API_BASE}/api/query/ad-hoc/${queryName}`
      );
      if (!res.ok) throw new Error(`Failed to fetch ad-hoc query: ${queryName}`);
      return res.json();
    },
    enabled: !!queryName,
  });
};

export const useAdHocQueries = () => {
  return useQuery({
    queryKey: ["adhoc-queries"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/api/adhoc/queries`);
      if (!res.ok) throw new Error("Failed to fetch available queries");
      return res.json();
    },
    staleTime: Infinity, // Query list rarely changes, cache indefinitely
  });
};
