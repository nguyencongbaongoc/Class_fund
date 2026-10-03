import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ImageUploadArea } from '../ImageUploadArea';
import { UploadState } from '../../types/chat';

const createMockFile = (name = 'test.jpg', size = 1000, type = 'image/jpeg') => {
  const file = new File(['test'], name, { type });
  Object.defineProperty(file, 'size', { value: size });
  return file;
};

describe('ImageUploadArea', () => {
  const mockOnChange = jest.fn();
  const mockOnAddUpload = jest.fn().mockImplementation((file) => `upload_${Date.now()}`);
  const mockOnRemoveUpload = jest.fn();
  const mockOnRetryUpload = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders drop zone when no images', () => {
    render(<ImageUploadArea images={[]} onChange={mockOnChange} onAddUpload={mockOnAddUpload} onRemoveUpload={mockOnRemoveUpload} onRetryUpload={mockOnRetryUpload} />);
    expect(screen.getByText(/Kéo thả ảnh biên lai/)).toBeInTheDocument();
  });

  it('shows preview grid when images exist', () => {
    const images: UploadState[] = [
      {
        id: 'upload_1',
        file: createMockFile('test.jpg'),
        preview_url: 'blob:test',
        progress: 100,
        status: 'completed',
        upload_id: 'up_1',
      },
    ];

    render(<ImageUploadArea images={images} onChange={mockOnChange} onAddUpload={mockOnAddUpload} onRemoveUpload={mockOnRemoveUpload} onRetryUpload={mockOnRetryUpload} />);
    expect(screen.getByRole('list')).toBeInTheDocument();
    expect(screen.getByRole('listitem')).toBeInTheDocument();
  });

  it('calls onAddUpload when file is selected', () => {
    render(<ImageUploadArea images={[]} onChange={mockOnChange} onAddUpload={mockOnAddUpload} onRemoveUpload={mockOnRemoveUpload} onRetryUpload={mockOnRetryUpload} />);
    
    const file = createMockFile();
    const input = screen.getByLabelText('Đính kèm ảnh biên lai');
    fireEvent.change(input, { target: { files: [file] } });
    
    expect(mockOnAddUpload).toHaveBeenCalledWith(file);
  });

  it('shows file count', () => {
    const images: UploadState[] = [
      { id: 'upload_1', file: createMockFile('test1.jpg'), preview_url: 'blob:test', progress: 100, status: 'completed' },
      { id: 'upload_2', file: createMockFile('test2.jpg'), preview_url: 'blob:test', progress: 50, status: 'uploading' },
    ];

    render(<ImageUploadArea images={images} onChange={mockOnChange} onAddUpload={mockOnAddUpload} onRemoveUpload={mockOnRemoveUpload} onRetryUpload={mockOnRetryUpload} />);
    expect(screen.getByText('Đã chọn 2/5 ảnh')).toBeInTheDocument();
  });

  it('shows progress summary when uploading', () => {
    const images: UploadState[] = [
      { id: 'upload_1', file: createMockFile('test1.jpg'), preview_url: 'blob:test', progress: 50, status: 'uploading' },
    ];

    render(<ImageUploadArea images={images} onChange={mockOnChange} onAddUpload={mockOnAddUpload} onRemoveUpload={mockOnRemoveUpload} onRetryUpload={mockOnRetryUpload} />);
    expect(screen.getByText('Đang tải lên...')).toBeInTheDocument();
  });

  it('disables when disabled prop is true', () => {
    render(<ImageUploadArea images={[]} onChange={mockOnChange} onAddUpload={mockOnAddUpload} onRemoveUpload={mockOnRemoveUpload} onRetryUpload={mockOnRetryUpload} disabled />);
    expect(screen.getByLabelText('Đính kèm ảnh biên lai')).toBeDisabled();
  });
});