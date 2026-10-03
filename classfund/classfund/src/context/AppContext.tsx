import React, { createContext, useContext, useState, useMemo } from 'react';
import { 
  User, 
  UserRole, 
  LedgerEntry, 
  StudentRosterItem, 
  CollectionCampaign, 
  ChatMessage, 
  AuditLogItem, 
  ViewTab 
} from '../types';
import { 
  MOCK_USERS, 
  INITIAL_LEDGER_ENTRIES, 
  INITIAL_STUDENTS_ROSTER, 
  INITIAL_CAMPAIGN, 
  INITIAL_CHAT_MESSAGES, 
  INITIAL_AUDIT_LOGS,
  calculateLedgerBalances,
  formatVND,
  ASSET_PATHS
} from '../data/mockDatabase';
import { WALLPAPERS } from '../data/wallpapers';

interface ToastMessage {
  id: string;
  type: 'success' | 'error' | 'info' | 'warning';
  title: string;
  description?: string;
}

interface AppContextType {
  currentUser: User;
  setCurrentUser: (user: User) => void;
  switchRole: (role: UserRole) => void;
  currentTab: ViewTab;
  setCurrentTab: (tab: ViewTab) => void;
  ledgerEntries: LedgerEntry[];
  studentsRoster: StudentRosterItem[];
  campaign: CollectionCampaign;
  chatMessages: ChatMessage[];
  auditLogs: AuditLogItem[];
  balances: ReturnType<typeof calculateLedgerBalances>;
  selectedTransaction: LedgerEntry | null;
  setSelectedTransaction: (entry: LedgerEntry | null) => void;
  isRevertModalOpen: boolean;
  setIsRevertModalOpen: (open: boolean) => void;
  isExpenseModalOpen: boolean;
  setIsExpenseModalOpen: (open: boolean) => void;
  isCreateCampaignModalOpen: boolean;
  setIsCreateCampaignModalOpen: (open: boolean) => void;
  isE2EModalOpen: boolean;
  setIsE2EModalOpen: (open: boolean) => void;
  currentWallpaper: string;
  setCurrentWallpaper: (url: string) => void;
  isWallpaperModalOpen: boolean;
  setIsWallpaperModalOpen: (open: boolean) => void;
  isSecretWallpaperUnlocked: boolean;
  unlockSecretWallpaper: () => void;
  isPerimeterGlowActive: boolean;
  triggerPerimeterGlow: () => void;
  isLiquidGlassEnabled: boolean;
  setIsLiquidGlassEnabled: (enabled: boolean) => void;
  toggleLiquidGlass: () => void;
  liquidGlassBlur: number;
  setLiquidGlassBlur: (blur: number) => void;
  liquidGlassPreset: 'clear' | 'balanced' | 'frosted' | 'custom';
  setLiquidGlassPreset: (preset: 'clear' | 'balanced' | 'frosted') => void;
  toasts: ToastMessage[];
  addToast: (toast: Omit<ToastMessage, 'id'>) => void;
  removeToast: (id: string) => void;
  
  // Financial Actions
  addLedgerEntry: (entry: Omit<LedgerEntry, 'id' | 'created_at' | 'effective_at'>) => LedgerEntry;
  revertTransaction: (transactionId: string, reason: string) => boolean;
  addManualExpense: (amount: number, recipient: string, reason: string) => void;
  sendChatMessage: (content: string, type?: 'TEXT' | 'ANNOUNCEMENT', isPinned?: boolean) => void;
  markStudentPaid: (studentId: string, paid: boolean) => void;
  resetToDefaultData: () => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentUser, setCurrentUser] = useState<User>(MOCK_USERS.treasurer);
  const [currentTab, setCurrentTab] = useState<ViewTab>('dashboard');
  const [ledgerEntries, setLedgerEntries] = useState<LedgerEntry[]>(INITIAL_LEDGER_ENTRIES);
  const [studentsRoster, setStudentsRoster] = useState<StudentRosterItem[]>(INITIAL_STUDENTS_ROSTER);
  const [campaign, setCampaign] = useState<CollectionCampaign>(INITIAL_CAMPAIGN);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>(INITIAL_CHAT_MESSAGES);
  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>(INITIAL_AUDIT_LOGS);
  
  const [selectedTransaction, setSelectedTransaction] = useState<LedgerEntry | null>(null);
  const [isRevertModalOpen, setIsRevertModalOpen] = useState(false);
  const [isExpenseModalOpen, setIsExpenseModalOpen] = useState(false);
  const [isCreateCampaignModalOpen, setIsCreateCampaignModalOpen] = useState(false);
  const [isE2EModalOpen, setIsE2EModalOpen] = useState(false);
  const [currentWallpaper, setCurrentWallpaperState] = useState<string>(() => {
    try {
      return localStorage.getItem('classfund_wallpaper') || WALLPAPERS[0].url;
    } catch {
      return WALLPAPERS[0].url;
    }
  });
  const [isWallpaperModalOpen, setIsWallpaperModalOpen] = useState(false);
  const [isSecretWallpaperUnlocked, setIsSecretWallpaperUnlocked] = useState<boolean>(() => {
    try {
      return localStorage.getItem('classfund_secret_wallpaper_unlocked') === 'true';
    } catch {
      return false;
    }
  });

  const [isPerimeterGlowActive, setIsPerimeterGlowActive] = useState(false);

  const unlockSecretWallpaper = () => {
    setIsSecretWallpaperUnlocked(true);
    try {
      localStorage.setItem('classfund_secret_wallpaper_unlocked', 'true');
    } catch {}
  };

  const triggerPerimeterGlow = () => {
    setIsPerimeterGlowActive(true);
    setTimeout(() => {
      setIsPerimeterGlowActive(false);
    }, 3000);
  };

  const setCurrentWallpaper = (url: string) => {
    setCurrentWallpaperState(url);
    try {
      localStorage.setItem('classfund_wallpaper', url);
    } catch {}
    addToast({
      type: 'success',
      title: 'Đã đổi hình nền',
      description: 'Kính mờ trong suốt tự động phản chiếu theo hình nền mới.',
    });
  };
  const [isLiquidGlassEnabled, setIsLiquidGlassEnabled] = useState(true); // Default to TRUE: Liquid Glass enabled!
  const [liquidGlassBlur, setLiquidGlassBlurState] = useState(35); // 0 = trong suốt rõ, 100 = mờ nhiều
  const [liquidGlassPreset, setLiquidGlassPresetState] = useState<'clear' | 'balanced' | 'frosted' | 'custom'>('balanced');

  const toggleLiquidGlass = () => {
    setIsLiquidGlassEnabled((prev) => !prev);
  };

  const setLiquidGlassBlur = (val: number) => {
    const clamped = Math.max(0, Math.min(100, Math.round(val)));
    setLiquidGlassBlurState(clamped);
    if (clamped <= 20) {
      setLiquidGlassPresetState('clear');
    } else if (clamped >= 70) {
      setLiquidGlassPresetState('frosted');
    } else if (clamped >= 35 && clamped <= 55) {
      setLiquidGlassPresetState('balanced');
    } else {
      setLiquidGlassPresetState('custom');
    }
  };

  const setLiquidGlassPreset = (preset: 'clear' | 'balanced' | 'frosted') => {
    setLiquidGlassPresetState(preset);
    if (preset === 'clear') {
      setLiquidGlassBlurState(15); // Trong suốt rõ
      addToast({
        type: 'info',
        title: 'Chế độ Liquid Glass: Trong suốt rõ (Clear)',
        description: 'Độ trong suốt cực đại, vân khúc xạ quang học tinh khiết.'
      });
    } else if (preset === 'balanced') {
      setLiquidGlassBlurState(45); // Cân bằng
      addToast({
        type: 'info',
        title: 'Chế độ Liquid Glass: Cân bằng (Balanced)',
        description: 'Chuẩn Liquid Glassmorphism với ánh sáng và đổ bóng mềm mại.'
      });
    } else if (preset === 'frosted') {
      setLiquidGlassBlurState(85); // Mờ nhiều
      addToast({
        type: 'info',
        title: 'Chế độ Liquid Glass: Mờ nhiều (Frosted)',
        description: 'Tán xạ ánh sáng sương đục dày, chiều sâu thị giác sang trọng.'
      });
    }
  };
  
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const addToast = (toast: Omit<ToastMessage, 'id'>) => {
    const id = 'toast_' + Date.now() + Math.random().toString(36).substring(2, 5);
    setToasts((prev) => [...prev, { ...toast, id }]);
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const switchRole = (role: UserRole) => {
    if (role === 'TREASURER') setCurrentUser(MOCK_USERS.treasurer);
    else if (role === 'MODERATOR') setCurrentUser(MOCK_USERS.moderator);
    else if (role === 'MEMBER') setCurrentUser(MOCK_USERS.member);
    else setCurrentUser(MOCK_USERS.public);

    addToast({
      type: 'info',
      title: `Đã đổi vai trò sang: ${role}`,
      description: role === 'PUBLIC' ? 'Chế độ khách xem quỹ công khai' : `Đăng nhập dưới quyền ${role}`
    });
  };

  // Strictly calculate balances from ledger
  const balances = useMemo(() => {
    return calculateLedgerBalances(ledgerEntries);
  }, [ledgerEntries]);

  // Financial core mutation: Add ledger entry
  const addLedgerEntry = (newEntryData: Omit<LedgerEntry, 'id' | 'created_at' | 'effective_at'>): LedgerEntry => {
    const now = new Date();
    const timeStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
    
    const entryId = 'tx_' + Date.now();
    const fullEntry: LedgerEntry = {
      ...newEntryData,
      id: entryId,
      created_at: timeStr,
      effective_at: timeStr,
    };

    setLedgerEntries((prev) => [fullEntry, ...prev]);

    // If verified, match student if possible
    if (fullEntry.status === 'VERIFIED' && fullEntry.type === 'CREDIT') {
      const normalizedSender = fullEntry.sender_name.toLowerCase().trim();
      setStudentsRoster((prev) => {
        let updatedCount = 0;
        const newRoster = prev.map((s) => {
          if (s.status === 'UNPAID' && normalizedSender.includes(s.full_name.toLowerCase())) {
            updatedCount++;
            return {
              ...s,
              status: 'PAID' as const,
              matched_amount: fullEntry.amount,
              matched_transaction_code: fullEntry.transaction_code,
              paid_at: `${now.getDate()}/${now.getMonth() + 1}`,
            };
          }
          return s;
        });

        if (updatedCount > 0) {
          setCampaign((c) => ({
            ...c,
            paid_students_count: c.paid_students_count + updatedCount,
            total_collected_amount: c.total_collected_amount + fullEntry.amount,
          }));
        }
        return newRoster;
      });
    }

    // Add audit log
    const auditId = 'aud_' + Date.now();
    setAuditLogs((prev) => [
      {
        id: auditId,
        actor_name: currentUser.name,
        actor_role: currentUser.role,
        action: fullEntry.type === 'DEBIT' ? 'POST_DEBIT' : 'POST_CREDIT',
        entity_type: 'TRANSACTION',
        entity_id: entryId,
        details: `${fullEntry.sender_name} (${formatVND(fullEntry.amount)}) - ${fullEntry.note || fullEntry.transaction_code}`,
        created_at: timeStr,
      },
      ...prev,
    ]);

    // Add activity to chat
    if (fullEntry.source === 'IMAGE') {
      const msgId = 'msg_' + Date.now();
      setChatMessages((prev) => [
        {
          id: msgId,
          sender_id: currentUser.id,
          sender_name: fullEntry.uploaded_by,
          sender_role: currentUser.role,
          message_type: 'RECEIPT',
          content: `Đã gửi ảnh xác nhận chuyển khoản ${formatVND(fullEntry.amount)}`,
          receipt_data: {
            entry_id: entryId,
            amount: fullEntry.amount,
            transaction_code: fullEntry.transaction_code,
            image_url: fullEntry.image_url || 'https://images.unsplash.com/photo-1554224155-8d04cb21cd6c?w=600&auto=format&fit=crop&q=80',
            status: fullEntry.status,
            sender_name: fullEntry.sender_name,
            uploader_name: fullEntry.uploaded_by,
            time: timeStr,
          },
          created_at: timeStr,
        },
        ...prev,
      ]);
    }

    return fullEntry;
  };

  // Revert transaction logic (Phase 9 & 11)
  const revertTransaction = (transactionId: string, reason: string): boolean => {
    const original = ledgerEntries.find((e) => e.id === transactionId);
    if (!original) {
      addToast({ type: 'error', title: 'Lỗi', description: 'Không tìm thấy giao dịch để thu hồi.' });
      return false;
    }

    if (original.status === 'REVERTED') {
      addToast({ type: 'warning', title: 'Cảnh báo', description: 'Giao dịch này đã được thu hồi trước đó.' });
      return false;
    }

    const now = new Date();
    const timeStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
    const reversalId = 'tx_rev_' + Date.now();

    // 1. Create reversal entry
    const reversalEntry: LedgerEntry = {
      id: reversalId,
      type: 'REVERT',
      amount: original.amount,
      currency: 'VND',
      source: 'REVERT',
      transaction_code: `REV_${original.transaction_code}`,
      sender_name: `${currentUser.name} (Đảo bút toán)`,
      uploaded_by: currentUser.name,
      created_at: timeStr,
      effective_at: timeStr,
      status: 'VERIFIED',
      original_entry_id: original.id,
      note: `Bút toán đảo: Thu hồi giao dịch ${original.transaction_code}. Lý do: ${reason}`,
    };

    // 2. Mark original entry as REVERTED
    setLedgerEntries((prev) => 
      prev.map((e) => {
        if (e.id === transactionId) {
          return {
            ...e,
            status: 'REVERTED' as const,
            revert_reason: reason,
            reverted_by: `${currentUser.name} (${currentUser.role})`,
            reverted_at: timeStr,
            reversal_entry_id: reversalId,
          };
        }
        return e;
      }).concat(reversalEntry)
    );

    // 3. Update student roster if matched
    setStudentsRoster((prev) =>
      prev.map((s) => {
        if (s.matched_transaction_code === original.transaction_code) {
          return {
            ...s,
            status: 'UNPAID' as const,
            matched_amount: undefined,
            matched_transaction_code: undefined,
            paid_at: undefined,
            notes: `Giao dịch đã bị thu hồi: ${reason}`,
          };
        }
        return s;
      })
    );

    // 4. Update campaign stats if it was a credit
    if (original.type === 'CREDIT') {
      setCampaign((c) => ({
        ...c,
        paid_students_count: Math.max(0, c.paid_students_count - 1),
        total_collected_amount: Math.max(0, c.total_collected_amount - original.amount),
      }));
    }

    // 5. Audit log
    setAuditLogs((prev) => [
      {
        id: 'aud_' + Date.now(),
        actor_name: currentUser.name,
        actor_role: currentUser.role,
        action: 'REVERT_TRANSACTION',
        entity_type: 'TRANSACTION',
        entity_id: original.id,
        details: `Thu hồi giao dịch ${original.transaction_code} (${formatVND(original.amount)}). Lý do: ${reason}`,
        created_at: timeStr,
      },
      ...prev,
    ]);

    // 6. Notify chat
    setChatMessages((prev) => [
      {
        id: 'msg_rev_' + Date.now(),
        sender_id: currentUser.id,
        sender_name: currentUser.name,
        sender_role: currentUser.role,
        message_type: 'SYSTEM',
        content: `Đã thu hồi giao dịch ${original.transaction_code} (${formatVND(original.amount)}). Lý do: ${reason}`,
        created_at: timeStr,
      },
      ...prev,
    ]);

    addToast({
      type: 'success',
      title: 'Đã thu hồi giao dịch thành công',
      description: `Đã tạo bút toán đảo ${reversalEntry.transaction_code} và hoàn nguyên số dư.`
    });

    return true;
  };

  // Add manual expense (Debit)
  const addManualExpense = (amount: number, recipient: string, reason: string) => {
    const code = 'EXP_' + Date.now().toString().slice(-6);
    addLedgerEntry({
      type: 'DEBIT',
      amount,
      currency: 'VND',
      source: 'MANUAL',
      transaction_code: code,
      sender_name: recipient,
      uploaded_by: currentUser.name,
      status: 'VERIFIED',
      note: reason,
    });

    addToast({
      type: 'success',
      title: 'Đã ghi sổ chi tiền quỹ',
      description: `Khoản chi ${formatVND(amount)} cho "${recipient}" đã được lưu vào sổ cái.`
    });
  };

  // Chat message send
  const sendChatMessage = (content: string, type: 'TEXT' | 'ANNOUNCEMENT' = 'TEXT', isPinned: boolean = false) => {
    if (!content.trim()) return;
    const now = new Date();
    const timeStr = `${now.getHours()}:${String(now.getMinutes()).padStart(2, '0')}`;
    
    const newMsg: ChatMessage = {
      id: 'msg_' + Date.now(),
      sender_id: currentUser.id,
      sender_name: currentUser.name,
      sender_role: currentUser.role,
      message_type: currentUser.role === 'MODERATOR' || currentUser.role === 'TREASURER' ? type : 'TEXT',
      content: content.trim(),
      is_pinned: isPinned,
      created_at: timeStr,
    };

    setChatMessages((prev) => [newMsg, ...prev]);
  };

  // Mark student paid manually
  const markStudentPaid = (studentId: string, paid: boolean) => {
    setStudentsRoster((prev) =>
      prev.map((s) => {
        if (s.id === studentId) {
          return {
            ...s,
            status: paid ? 'PAID' : 'UNPAID',
            matched_amount: paid ? campaign.expected_amount_per_student : undefined,
            matched_transaction_code: paid ? 'CASH_MANUAL' : undefined,
            paid_at: paid ? 'Hôm nay' : undefined,
          };
        }
        return s;
      })
    );

    setCampaign((c) => ({
      ...c,
      paid_students_count: paid ? c.paid_students_count + 1 : Math.max(0, c.paid_students_count - 1),
      total_collected_amount: paid 
        ? c.total_collected_amount + campaign.expected_amount_per_student
        : Math.max(0, c.total_collected_amount - campaign.expected_amount_per_student),
    }));

    addToast({
      type: 'info',
      title: 'Đã cập nhật trạng thái học sinh',
      description: paid ? 'Đã đánh dấu ĐÃ NỘP tiền mặt' : 'Đã chuyển về trạng thái CHƯA NỘP'
    });
  };

  const resetToDefaultData = () => {
    setLedgerEntries(INITIAL_LEDGER_ENTRIES);
    setStudentsRoster(INITIAL_STUDENTS_ROSTER);
    setCampaign(INITIAL_CAMPAIGN);
    setChatMessages(INITIAL_CHAT_MESSAGES);
    setAuditLogs(INITIAL_AUDIT_LOGS);
    setCurrentUser(MOCK_USERS.treasurer);
    addToast({
      type: 'info',
      title: 'Đã đặt lại dữ liệu mẫu ban đầu',
      description: 'Số dư quỹ và lịch sử đã được khôi phục về trạng thái gốc.'
    });
  };

  return (
    <AppContext.Provider
      value={{
        currentUser,
        setCurrentUser,
        switchRole,
        currentTab,
        setCurrentTab,
        ledgerEntries,
        studentsRoster,
        campaign,
        chatMessages,
        auditLogs,
        balances,
        selectedTransaction,
        setSelectedTransaction,
        isRevertModalOpen,
        setIsRevertModalOpen,
        isExpenseModalOpen,
        setIsExpenseModalOpen,
        isCreateCampaignModalOpen,
        setIsCreateCampaignModalOpen,
        isE2EModalOpen,
        setIsE2EModalOpen,
        currentWallpaper,
        setCurrentWallpaper,
        isWallpaperModalOpen,
        setIsWallpaperModalOpen,
        isSecretWallpaperUnlocked,
        unlockSecretWallpaper,
        isPerimeterGlowActive,
        triggerPerimeterGlow,
        isLiquidGlassEnabled,
        setIsLiquidGlassEnabled,
        toggleLiquidGlass,
        liquidGlassBlur,
        setLiquidGlassBlur,
        liquidGlassPreset,
        setLiquidGlassPreset,
        toasts,
        addToast,
        removeToast,
        addLedgerEntry,
        revertTransaction,
        addManualExpense,
        sendChatMessage,
        markStudentPaid,
        resetToDefaultData,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};
