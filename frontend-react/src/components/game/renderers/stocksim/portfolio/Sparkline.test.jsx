import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import Sparkline from './Sparkline';

describe('Sparkline', () => {
  it('renders an svg with a polyline path when given values', () => {
    const { container } = render(<Sparkline values={[10, 12, 8, 14, 11]} width={200} height={40} />);
    expect(container.querySelector('svg')).toBeTruthy();
    expect(container.querySelector('polyline')).toBeTruthy();
  });

  it('renders an empty placeholder when no values', () => {
    const { container } = render(<Sparkline values={[]} />);
    expect(container.querySelector('polyline')).toBeFalsy();
  });
});
