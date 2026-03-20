import React from 'react';

interface BadgeProps {
  variant?: 'success' | 'danger' | 'warning' | 'neutral';
  children: React.ReactNode;
  className?: string;
}

const Badge: React.FC<BadgeProps> = ({ variant = 'neutral', children, className = '' }) => {
  const styles = {
    success: 'bg-[#0ECB81]/20 text-[#0ECB81]',
    danger: 'bg-[#F6465D]/20 text-[#F6465D]',
    warning: 'bg-[#F0B90B]/20 text-[#F0B90B]',
    neutral: 'bg-[#2B2F36] text-[#848E9C]',
  };

  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium inline-flex items-center justify-center ${styles[variant]} ${className}`}>
      {children}
    </span>
  );
};

export default Badge;
