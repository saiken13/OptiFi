export function calculate_months_to_goal(
  target: number,
  current: number,
  monthly: number
): number | null {
  if (monthly <= 0) return null;
  const remaining = target - current;
  if (remaining <= 0) return 0;
  return remaining / monthly;
}
