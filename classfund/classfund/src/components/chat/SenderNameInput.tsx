import React, { useEffect } from 'react';
import { User, Edit2, Check } from 'lucide-react';

interface SenderNameInputProps {
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
  placeholder?: string;
  autoFocus?: boolean;
  className?: string;
}

export const SenderNameInput: React.FC<SenderNameInputProps> = ({
  value,
  onChange,
  required = true,
  placeholder = 'Nhập tên của bạn',
  autoFocus = false,
  className = '',
}) => {
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [localValue, setLocalValue] = useState(value);

  // Load from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('guest_sender_name');
    if (saved && !value) {
      setLocalValue(saved);
      onChange(saved);
    }
  }, [value, onChange]);

  // Sync with parent value
  useEffect(() => {
    if (value !== localValue) {
      setLocalValue(value);
    }
  }, [value]);

  // Save to localStorage on blur
  const handleBlur = () => {
    if (localValue.trim()) {
      localStorage.setItem('guest_sender_name', localValue.trim());
    }
    setIsEditing(false);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    setLocalValue(newValue);
    onChange(newValue);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleBlur();
    } else if (e.key === 'Escape') {
      setLocalValue(value);
      setIsEditing(false);
      inputRef.current?.blur();
    }
  };

  const handleFocus = () => {
    setIsEditing(true);
  };

  return (
    <div className={`relative ${className}`}>
      <label className="block text-xs font-semibold text-neutral-300 mb-1.5 flex items-center gap-1">
        <User className="w-3.5 h-3.5" aria-hidden="true" />
        <span>Tên người gửi {required && <span className="text-rose-400">*</span>}</span>
      </label>
      
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          value={localValue}
          onChange={handleChange}
          onBlur={handleBlur}
          onFocus={handleFocus}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          required={required}
          autoFocus={autoFocus}
          maxLength={120}
          className={`
            w-full px-4 py-2.5 pr-12 rounded-xl 
            bg-white/[0.04] border border-white/10 
            text-white text-sm 
            placeholder:text-neutral-500
            focus:outline-none focus:border-sky-400 focus:ring-1 focus:ring-sky-400/20
            transition-colors
            ${required && !localValue.trim() ? 'border-rose-400/50' : ''}
          `}
          aria-required={required}
          aria-describedby={required ? 'sender-name-hint' : undefined}
        />
        
        <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1">
          {required && !localValue.trim() && (
            <span className="text-rose-400" aria-hidden="true">*</span>
          )}
          {isEditing && localValue.trim() && (
            <button
              type="button"
              onClick={handleBlur}
              className="p-1 rounded-lg bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 transition-colors"
              aria-label="Lưu tên"
              title="Lưu tên"
            >
              <Check className="w-4 h-4" aria-hidden="true" />
            </button>
          )}
          {!isEditing && (
            <Edit2 className="w-4 h-4 text-neutral-500" aria-hidden="true" />
          )}
        </div>
      </div>

      {required && (
        <p id="sender-name-hint" className="mt-1.5 text-[10px] text-neutral-500">
          Tên sẽ được lưu để dùng lại lần sau. Tối thiểu 2 ký tự.
        </p>
      )}
    </div>
  );
};

// Simpler version for inline use in composer
export const InlineSenderNameInput: React.FC<{
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
  className?: string;
}> = ({ value, onChange, required = true, className = '' }) => {
  const [localValue, setLocalValue] = useState(value);

  useEffect(() => {
    setLocalValue(value);
  }, [value]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    setLocalValue(newValue);
    onChange(newValue);
  };

  const handleBlur = () => {
    if (localValue.trim()) {
      localStorage.setItem('guest_sender_name', localValue.trim());
    }
  };

  return (
    <div className={`relative ${className}`}>
      <input
        type="text"
        value={localValue}
        onChange={handleChange}
        onBlur={handleBlur}
        placeholder={required ? 'Tên của bạn *' : 'Tên của bạn'}
        maxLength={120}
        className={`
          w-full px-3 py-2 pr-8 rounded-xl 
          bg-white/[0.04] border border-white/10 
          text-white text-sm 
          placeholder:text-neutral-500
          focus:outline-none focus:border-sky-400
          transition-colors
        `}
        aria-label="Tên người gửi"
        required={required}
      />
      {required && (
        <span className="absolute right-3 top-1/2 -translate-y-1/2 text-rose-400 text-[10px] font-bold" aria-hidden="true">*</span>
      )}
    </div>
  );
};

import { useState } from 'react';