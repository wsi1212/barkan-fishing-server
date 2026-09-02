import test from "node:test";
import assert from "node:assert/strict";
import {
  PURCHASE_PERIODS,
  RECOMMENDED_MONTHS,
  monthsForDays,
  periodDays,
  periodForDays,
  periodForMonths,
  periodLabel,
  periodLabelFromDays,
  validMonths
} from "./membership-periods.mjs";

test("every purchasable period round-trips between months, days, and labels", () => {
  assert.deepEqual(
    PURCHASE_PERIODS.map(({ months, days }) => [months, days]),
    [[1, 30], [3, 90], [5, 150], [12, 365]]
  );

  for (const period of PURCHASE_PERIODS) {
    assert.deepEqual(periodForMonths(period.months), period);
    assert.deepEqual(periodForDays(period.days), period);
    assert.equal(periodDays(period.months), period.days);
    assert.equal(monthsForDays(period.days), period.months);
    assert.equal(periodLabel(period.months), period.months === 12 ? "1년" : `${period.months}개월`);
    assert.equal(periodLabelFromDays(period.days), period.months === 12 ? "1년" : `${period.months}개월`);
  }
});

test("invalid selections use the expected defaults without changing valid periods", () => {
  assert.equal(validMonths(undefined), RECOMMENDED_MONTHS);
  assert.equal(validMonths("not-a-period"), RECOMMENDED_MONTHS);
  assert.equal(validMonths("not-a-period", 1), 1);
  assert.equal(validMonths("3"), 3);
  assert.equal(validMonths("5"), 5);
  assert.equal(validMonths("1"), 1);
  assert.equal(validMonths("12"), 12);
  assert.equal(validMonths("5extra"), 5);
});

test("unknown stored day values are displayed as their exact day count", () => {
  assert.equal(periodForDays(31), null);
  assert.equal(monthsForDays(31), null);
  assert.equal(periodLabelFromDays(31), "31일");
});
