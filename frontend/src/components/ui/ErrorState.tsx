import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
}

const ErrorState: React.FC<ErrorStateProps> = ({ 
  message = "Không thể tải dữ liệu.", 
  onRetry 
}) => {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center bg-bg-secondary border border-cbx-border rounded-lg">
      <div className="bg-accent-red/10 p-3 rounded-full mb-4">
        <AlertTriangle className="text-accent-red w-8 h-8" />
      </div>
      <h3 className="text-lg font-bold text-[#EAECEF] mb-1">Đã xảy ra lỗi</h3>
      <p className="text-sm text-cbx-muted mb-6 max-w-xs mx-auto">
        {message} Vui lòng kiểm tra kết nối mạng hoặc thử lại sau.
      </p>
      {onRetry && (
        <button 
          onClick={onRetry}
          className="flex items-center gap-2 bg-bg-primary border border-cbx-border hover:border-accent-yellow text-cbx-text px-6 py-2 rounded text-sm font-bold transition-all"
        >
          <RefreshCw size={16} />
          <span>Thử lại</span>
        </button>
      )}
    </div>
  );
};

export default ErrorState;
