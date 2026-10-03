import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { RecallButton, RecallTrigger } from '../RecallButton';
import { MessageStatus } from '../../types/chat';

describe('RecallButton', () => {
  const mockOnRecall = jest.fn();

  it('renders nothing when canRecall is false', () => {
    render(<RecallButton messageId="msg-1" status="posted" canRecall={false} onRecall={mockOnRecall} />);
    expect(screen.queryByText('THU HỘI')).not.toBeInTheDocument();
  });

  it('renders THU HỘI button when canRecall is true', () => {
    render(<RecallButton messageId="msg-1" status="posted" canRecall={true} onRecall={mockOnRecall} />);
    expect(screen.getByText('THU HỘI')).toBeInTheDocument();
  });

  it('shows correct label for pending status', () => {
    render(<RecallButton messageId="msg-1" status="pending" canRecall={true} onRecall={mockOnRecall} />);
    expect(screen.getByText('THU HỘI')).toHaveAttribute('aria-label', 'Thu hồi yêu cầu');
  });

  it('shows correct label for posted status', () => {
    render(<RecallButton messageId="msg-1" status="posted" canRecall={true} onRecall={mockOnRecall} />);
    expect(screen.getByText('THU HỘI')).toHaveAttribute('aria-label', 'Yêu cầu đảo bút toán');
  });

  it('opens confirmation modal on click', () => {
    render(<RecallButton messageId="msg-1" status="pending" canRecall={true} onRecall={mockOnRecall} />);
    
    fireEvent.click(screen.getByText('THU HỘI'));
    
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Xác nhận thu hồi yêu cầu')).toBeInTheDocument();
  });

  it('calls onRecall with messageId and reason on confirm', () => {
    render(<RecallButton messageId="msg-1" status="pending" canRecall={true} onRecall={mockOnRecall} />);
    
    fireEvent.click(screen.getByText('THU HỘI'));
    fireEvent.change(screen.getByLabelText('Lý do thu hồi'), { target: { value: 'Test reason' } });
    fireEvent.click(screen.getByText('Xác nhận thu hồi'));
    
    expect(mockOnRecall).toHaveBeenCalledWith('msg-1', 'pending', 'Test reason');
  });

  it('does not call onRecall when cancel is clicked', () => {
    render(<RecallButton messageId="msg-1" status="pending" canRecall={true} onRecall={mockOnRecall} />);
    
    fireEvent.click(screen.getByText('THU HỘI'));
    fireEvent.click(screen.getByText('Hủy'));
    
    expect(mockOnRecall).not.toHaveBeenCalled();
  });

  it('disables button when isRecalling is true', () => {
    render(<RecallButton messageId="msg-1" status="pending" canRecall={true} onRecall={mockOnRecall} isRecalling />);
    expect(screen.getByText('Đang thu hồi...')).toBeDisabled();
  });

  it('applies custom className', () => {
    render(<RecallButton messageId="msg-1" status="pending" canRecall={true} onRecall={mockOnRecall} className="custom-btn" />);
    expect(screen.getByText('THU HỘI')).toHaveClass('custom-btn');
  });
});

describe('RecallTrigger', () => {
  it('renders nothing when canRecall is false', () => {
    render(<RecallTrigger messageId="msg-1" status="posted" canRecall={false} onRecall={jest.fn()} />);
    expect(screen.queryByText('Thu hồi')).not.toBeInTheDocument();
  });

  it('renders Thu hồi button when canRecall is true', () => {
    render(<RecallTrigger messageId="msg-1" status="pending" canRecall={true} onRecall={jest.fn()} />);
    expect(screen.getByRole('menuitem')).toBeInTheDocument();
    expect(screen.getByText('Thu hồi')).toBeInTheDocument();
  });
});