'use client';

import React from 'react';
import { useToastStore } from '@/store/toastStore';
import { CheckCircle, XCircle, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const ToastContainer = () => {
  const { toasts, removeToast } = useToastStore();

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 min-w-[300px] max-w-md">
      <AnimatePresence>
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className={`
              flex items-center gap-3 p-4 rounded-lg shadow-lg border
              ${toast.type === 'success' 
                ? 'bg-[#0ECB81]/10 border-[#0ECB81] text-[#0ECB81]' 
                : toast.type === 'error'
                ? 'bg-[#F6465D]/10 border-[#F6465D] text-[#F6465D]'
                : 'bg-[#2B2F36] border-cbx-border text-cbx-text'
              }
            `}
          >
            {toast.type === 'success' && <CheckCircle className="w-5 h-5 shrink-0" />}
            {toast.type === 'error' && <XCircle className="w-5 h-5 shrink-0" />}
            
            <p className="flex-1 text-sm font-medium">{toast.message}</p>
            
            <button 
              onClick={() => removeToast(toast.id)}
              className="p-1 hover:bg-white/10 rounded-full transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
};

export default ToastContainer;
