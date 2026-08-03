'use client';

type HealthBadgeProps = {
  status: 'ok' | 'degraded' | 'unknown';
};

const labels: Record<HealthBadgeProps['status'], string> = {
  ok: '정상',
  degraded: '저하',
  unknown: '알 수 없음',
};

export function HealthBadge({ status }: HealthBadgeProps) {
  return <span data-status={status}>{labels[status]}</span>;
}
