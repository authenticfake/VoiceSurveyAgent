/**
 * Utility function tests.
 * REQ-023: Frontend campaign management UI
 */

import { cn, formatDate, formatDateTime, formatTime, formatPercentage, truncate } from '@/lib/utils';

describe('cn', () => {
  it('merges class names', () => {
    expect(cn('foo', 'bar')).toBe('foo bar');
  });

  it('handles conditional classes', () => {
    expect(cn('foo', false && 'bar', 'baz')).toBe('foo baz');
  });

  it('merges tailwind classes correctly', () => {
    expect(cn('px-2', 'px-4')).toBe('px-4');
  });
});

describe('formatDate', () => {
  it('formats date string', () => {
    const result = formatDate('2024-01-15T10:30:00Z');
    expect(result).toMatch(/Jan.*15.*2024/);
  });

  it('formats Date object', () => {
    const result = formatDate(new Date('2024-01-15T10:30:00Z'));
    expect(result).toMatch(/Jan.*15.*2024/);
  });
});

describe('formatDateTime', () => {
  it('formats date and time', () => {
    const result = formatDateTime('2024-01-15T10:30:00Z');
    expect(result).toMatch(/Jan.*15.*2024/);
  });
});

describe('formatTime', () => {
  it('formats time string', () => {
    expect(formatTime('09:30:00')).toBe('09:30');
  });

  it('returns dash for null', () => {
    expect(formatTime(null)).toBe('-');
  });
});

describe('formatPercentage', () => {
  it('formats decimal as percentage', () => {
    expect(formatPercentage(0.95)).toBe('95.0%');
  });

  it('respects decimal places', () => {
    expect(formatPercentage(0.9567, 2)).toBe('95.67%');
  });
});

describe('truncate', () => {
  it('truncates long strings', () => {
    expect(truncate('Hello World', 5)).toBe('Hello...');
  });

  it('does not truncate short strings', () => {
    expect(truncate('Hi', 5)).toBe('Hi');
  });
});