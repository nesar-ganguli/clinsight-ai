function timestamp(value: string | null | undefined): number {
  if (!value) {
    return Number.NEGATIVE_INFINITY;
  }

  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? Number.NEGATIVE_INFINITY : parsed;
}

export function compareClinicalDatesDescending(
  left: string | null | undefined,
  right: string | null | undefined,
): number {
  const leftTimestamp = timestamp(left);
  const rightTimestamp = timestamp(right);

  if (leftTimestamp !== rightTimestamp) {
    return rightTimestamp - leftTimestamp;
  }
  return (right || "").localeCompare(left || "");
}
