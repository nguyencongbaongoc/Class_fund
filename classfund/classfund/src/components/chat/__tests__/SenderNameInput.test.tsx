import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { SenderNameInput, InlineSenderNameInput } from '../SenderNameInput';

describe('SenderNameInput', () => {
  const mockOnChange = jest.fn();

  beforeEach(() => {
    localStorage.clear();
    jest.clearAllMocks();
  });

  it('renders label and input', () => {
    render(<SenderNameInput value="" onChange={mockOnChange} required />);
    expect(screen.getByLabelText('Tên người gửi *')).toBeInTheDocument();
  });

  it('calls onChange when input changes', () => {
    render(<SenderNameInput value="" onChange={mockOnChange} required />);
    fireEvent.change(screen.getByLabelText('Tên người gửi *'), { target: { value: 'Test User' } });
    expect(mockOnChange).toHaveBeenCalledWith('Test User');
  });

  it('shows required indicator when required', () => {
    render(<SenderNameInput value="" onChange={mockOnChange} required />);
    expect(screen.getByText('*')).toBeInTheDocument();
  });

  it('does not show required indicator when not required', () => {
    render(<SenderNameInput value="" onChange={mockOnChange} required={false} />);
    expect(screen.queryByText('*')).not.toBeInTheDocument();
  });

  it('saves to localStorage on blur', () => {
    render(<SenderNameInput value="Test User" onChange={mockOnChange} required />);
    fireEvent.blur(screen.getByLabelText('Tên người gửi *'));
    expect(localStorage.getItem('guest_sender_name')).toBe('Test User');
  });

  it('loads from localStorage on mount', () => {
    localStorage.setItem('guest_sender_name', 'Saved User');
    render(<SenderNameInput value="" onChange={mockOnChange} required />);
    expect(screen.getByLabelText('Tên người gửi *')).toHaveValue('Saved User');
  });

  it('applies custom className', () => {
    render(<SenderNameInput value="" onChange={mockOnChange} className="custom-input" />);
    expect(screen.getByLabelText('Tên người gửi *').parentElement).toHaveClass('custom-input');
  });
});

describe('InlineSenderNameInput', () => {
  const mockOnChange = jest.fn();

  beforeEach(() => {
    localStorage.clear();
    jest.clearAllMocks();
  });

  it('renders input with placeholder', () => {
    render(<InlineSenderNameInput value="" onChange={mockOnChange} required />);
    expect(screen.getByLabelText('Tên người gửi')).toHaveAttribute('placeholder', 'Tên của bạn *');
  });

  it('calls onChange when input changes', () => {
    render(<InlineSenderNameInput value="" onChange={mockOnChange} required />);
    fireEvent.change(screen.getByLabelText('Tên người gửi'), { target: { value: 'Test User' } });
    expect(mockOnChange).toHaveBeenCalledWith('Test User');
  });

  it('saves to localStorage on blur', () => {
    render(<InlineSenderNameInput value="Test User" onChange={mockOnChange} required />);
    fireEvent.blur(screen.getByLabelText('Tên người gửi'));
    expect(localStorage.getItem('guest_sender_name')).toBe('Test User');
  });

  it('shows required indicator', () => {
    render(<InlineSenderNameInput value="" onChange={mockOnChange} required />);
    expect(screen.getByText('*')).toBeInTheDocument();
  });
});