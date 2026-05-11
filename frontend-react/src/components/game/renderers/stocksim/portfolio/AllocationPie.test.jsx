import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/react';
import AllocationPie from './AllocationPie';

describe('AllocationPie', () => {
  it('renders one path per slice', () => {
    const slices = [{ label: 'IT', value: 60 }, { label: 'Pharma', value: 40 }];
    const { container } = render(<AllocationPie slices={slices} size={120} />);
    const paths = container.querySelectorAll('path[data-slice]');
    expect(paths).toHaveLength(2);
  });

  it('calls onSliceClick with label when slice clicked', () => {
    const slices = [{ label: 'IT', value: 60 }, { label: 'Pharma', value: 40 }];
    const onClick = vi.fn();
    const { container } = render(<AllocationPie slices={slices} onSliceClick={onClick} />);
    fireEvent.click(container.querySelector('path[data-slice="IT"]'));
    expect(onClick).toHaveBeenCalledWith('IT');
  });

  it('renders empty pie placeholder when total is zero', () => {
    const slices = [{ label: 'Cash', value: 0 }];
    const { container } = render(<AllocationPie slices={slices} />);
    const svg = container.querySelector('svg[aria-label="pie-empty"]');
    expect(svg).toBeTruthy();
    expect(container.querySelectorAll('path[data-slice]')).toHaveLength(0);
  });
});
