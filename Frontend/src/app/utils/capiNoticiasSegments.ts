export const SEGMENT_KEYS = ['daily', 'weekly', 'monthly'] as const;
export type SegmentKey = typeof SEGMENT_KEYS[number];

export const SEGMENT_LABELS: Record<SegmentKey, string> = {
  daily: 'Diario',
  weekly: 'Semanal',
  monthly: 'Mensual',
};

export const DEFAULT_SEGMENT_MIN_PRIORITY: Record<SegmentKey, number> = {
  daily: 4,
  weekly: 5.5,
  monthly: 6.5,
};

