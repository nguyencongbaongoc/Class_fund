import React from 'react';
import { LiquidGlassCard } from './LiquidGlassCard';

export interface LiquidCardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  variant?: 'default' | 'elevated' | 'droplet' | 'mod' | 'clear' | 'frosted' | 'modal';
  clarity?: 'clear' | 'balanced' | 'frosted';
  className?: string;
  useLiquidShader?: boolean;
  roundedClass?: string;
  interactive?: boolean;
}

export const LiquidCard: React.FC<LiquidCardProps> = ({
  children,
  variant = 'default',
  clarity,
  className = '',
  useLiquidShader = false,
  roundedClass = 'rounded-2xl md:rounded-3xl',
  interactive = true,
  ...props
}) => {
  let paddingClass = 'p-5 md:p-6';
  if (variant === 'elevated' || variant === 'frosted' || variant === 'modal') {
    paddingClass = 'p-6 md:p-8';
  }

  return (
    <LiquidGlassCard
      variant={variant}
      clarity={clarity}
      className={`${paddingClass} ${className}`}
      roundedClass={roundedClass}
      interactive={interactive}
      {...props}
    >
      {children}
    </LiquidGlassCard>
  );
};
