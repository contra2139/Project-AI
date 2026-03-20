import React from 'react';

interface ToggleProps {
  checked: boolean;
  onChange: (value: boolean) => void;
  label?: string;
  size?: 'sm' | 'md';
}

const Toggle: React.FC<ToggleProps> = ({ checked, onChange, label, size = 'md' }) => {
  const isSm = size === 'sm';
  
  return (
    <label className="inline-flex items-center cursor-pointer group select-none">
      <div className="relative inline-flex items-center">
        <input 
          type="checkbox" 
          className="sr-only peer" 
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
        />
        <div className={`
          ${isSm ? 'w-8 h-4' : 'w-11 h-6'} 
          bg-[#2B2F36] peer-focus:outline-none rounded-full peer 
          peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full 
          peer-checked:after:border-white after:content-[''] after:absolute 
          ${isSm ? 'after:top-[2px] after:start-[2px] after:h-3 after:w-3' : 'after:top-[2px] after:start-[2px] after:h-5 after:w-5'} 
          after:bg-white after:border-gray-300 after:border after:rounded-full after:transition-all 
          peer-checked:bg-[#F0B90B]
        `}></div>
      </div>
      {label && (
        <span className={`ms-3 text-sm font-medium text-[#848E9C] group-hover:text-[#EAECEF] transition-colors`}>
          {label}
        </span>
      )}
    </label>
  );
};

export default Toggle;
