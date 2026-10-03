import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { PublicCodeDisplay, InlinePublicCode } from '../PublicCodeDisplay';

describe('PublicCodeDisplay', () => {
  it('renders nothing when code is not provided', () => {
    render(<PublicCodeDisplay code={undefined} />);
    expect(screen.queryByRole('group')).not.toBeInTheDocument();
  });

  it('displays the public code with label', () => {
    render(<PublicCodeDisplay code="CF-20261003-A1B2C3" />);
    expect(screen.getByRole('group')).toBeInTheDocument();
    expect(screen.getByText('CF-20261003-A1B2C3')).toBeInTheDocument();
  });

  it('shows custom label', () => {
    render(<PublicCodeDisplay code="CF-20261003-A1B2C3" label="Mã tham chiếu" />);
    expect(screen.getByRole('group')).toHaveAttribute('aria-label', 'Mã tham chiếu');
  });

  it('copies to clipboard on button click', async () => {
    const mockWriteText = jest.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText: mockWriteText } });

    render(<PublicCodeDisplay code="CF-20261003-A1B2C3" />);
    
    const copyButton = screen.getByLabelText('Sao chép mã tham chiếu');
    await fireEvent.click(copyButton);
    
    expect(mockWriteText).toHaveBeenCalledWith('CF-20261003-A1B2C3');
  });

  it('shows copied state after click', async () => {
    const mockWriteText = jest.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText: mockWriteText } });

    render(<PublicCodeDisplay code="CF-20261003-A1B2C3" />);
    
    const copyButton = screen.getByLabelText('Sao chép mã tham chiếu');
    await fireEvent.click(copyButton);
    
    expect(screen.getByLabelText('Đã sao chép')).toBeInTheDocument();
  });

  it('applies size classes correctly', () => {
    const { rerender } = render(<PublicCodeDisplay code="CF-20261003-A1B2C3" size="sm" />);
    expect(screen.getByRole('group')).toHaveClass('text-[10px]');
    
    rerender(<PublicCodeDisplay code="CF-20261003-A1B2C3" size="md" />);
    expect(screen.getByRole('group')).toHaveClass('text-xs');
  });
});

describe('InlinePublicCode', () => {
  it('renders nothing when code is not provided', () => {
    render(<InlinePublicCode code={undefined} />);
    expect(screen.queryByText('CF-20261003-A1B2C3')).not.toBeInTheDocument();
  });

  it('displays the public code inline', () => {
    render(<InlinePublicCode code="CF-20261003-A1B2C3" />);
    expect(screen.getByText('CF-20261003-A1B2C3')).toBeInTheDocument();
  });
});