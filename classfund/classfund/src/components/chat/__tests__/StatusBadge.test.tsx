import React from 'react';
import { render, screen } from '@testing-library/react';
import { StatusBadge, StatusIndicator, StatusDot } from '../StatusBadge';
import { MessageStatus } from '../../types/chat';

describe('StatusBadge', () => {
  const statuses: MessageStatus[] = [
    'pending',
    'processing',
    'awaiting_review',
    'posted',
    'rejected',
    'failed',
    'recalled',
  ];

  statuses.forEach((status) => {
    it(`renders ${status} badge correctly`, () => {
      render(<StatusBadge status={status} />);
      expect(screen.getByRole('status')).toBeInTheDocument();
    });
  });

  it('shows label when showLabel is true', () => {
    render(<StatusBadge status="posted" showLabel />);
    expect(screen.getByText('Đã ghi sổ')).toBeInTheDocument();
  });

  it('hides label when showLabel is false', () => {
    render(<StatusBadge status="posted" showLabel={false} />);
    expect(screen.queryByText('Đã ghi sổ')).not.toBeInTheDocument();
  });

  it('shows icon when showIcon is true', () => {
    render(<StatusBadge status="posted" showIcon />);
    expect(screen.getByRole('status')).toContainHTML('svg');
  });

  it('applies size classes correctly', () => {
    const { rerender } = render(<StatusBadge status="posted" size="sm" />);
    expect(screen.getByRole('status')).toHaveClass('text-[10px]');
    
    rerender(<StatusBadge status="posted" size="md" />);
    expect(screen.getByRole('status')).toHaveClass('text-xs');
    
    rerender(<StatusBadge status="posted" size="lg" />);
    expect(screen.getByRole('status')).toHaveClass('text-sm');
  });

  it('applies custom className', () => {
    render(<StatusBadge status="posted" className="custom-class" />);
    expect(screen.getByRole('status')).toHaveClass('custom-class');
  });
});

describe('StatusIndicator', () => {
  it('renders with status label and icon', () => {
    render(<StatusIndicator status="processing" />);
    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByText('Đang xử lý')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(<StatusIndicator status="pending" className="custom-indicator" />);
    expect(screen.getByRole('status')).toHaveClass('custom-indicator');
  });
});

describe('StatusDot', () => {
  it('renders dot with status label', () => {
    render(<StatusDot status="rejected" />);
    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByText('Từ chối')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(<StatusDot status="failed" className="custom-dot" />);
    expect(screen.getByRole('status')).toHaveClass('custom-dot');
  });
});