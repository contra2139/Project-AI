import React from 'react';

interface SkeletonProps {
  className?: string;
}

const Skeleton: React.FC<SkeletonProps> = ({ className = "" }) => {
  return (
    <div
      className={`bg-[#2B2F36] animate-pulse rounded ${className}`}
    />
  );
};

export default Skeleton;
