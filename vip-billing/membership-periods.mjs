const PERIODS = [
  { months: 1, days: 30 },
  { months: 3, days: 90 },
  { months: 5, days: 150 },
  { months: 12, days: 365 }
];

export const PURCHASE_PERIODS = Object.freeze(PERIODS.map((period) => Object.freeze(period)));
export const PURCHASE_MONTHS = Object.freeze(PURCHASE_PERIODS.map(({ months }) => months));
export const RECOMMENDED_MONTHS = 5;

export function validMonths(value, fallback = RECOMMENDED_MONTHS) {
  const months = Number.parseInt(value, 10);
  return PURCHASE_MONTHS.includes(months) ? months : fallback;
}

export function periodForMonths(months) {
  return PURCHASE_PERIODS.find((period) => period.months === months) ?? null;
}

export function periodForDays(days) {
  const normalizedDays = Number(days);
  return PURCHASE_PERIODS.find((period) => period.days === normalizedDays) ?? null;
}

export function periodDays(months) {
  return periodForMonths(months)?.days ?? null;
}

export function monthsForDays(days) {
  return periodForDays(days)?.months ?? null;
}

export function periodLabel(months) {
  const days = periodDays(months);
  return days === null ? "기간 확인 필요" : `${days}일`;
}

export function periodLabelFromDays(days) {
  const period = periodForDays(days);
  return period ? `${period.days}일` : `${Number(days)}일`;
}
