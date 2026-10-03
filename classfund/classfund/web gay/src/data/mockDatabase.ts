import { 
  User, 
  LedgerEntry, 
  StudentRosterItem, 
  CollectionCampaign, 
  ChatMessage, 
  BankAccountInfo, 
  AuditLogItem 
} from '../types';

export const ASSET_PATHS = {
  macosWallpaper: '/src/assets/images/macos_wallpaper_light.jpg',
  liquidBackdrop: '/src/assets/images/liquid_droplet_backdrop_1790409580348.jpg',
  classBanner: '/src/assets/images/class_banner_students_1790409594803.jpg',
  vietQrMock: 'https://api.vietqr.io/image/970422-0876680302-51.jpg?accountName=HA%20DAI%20HAI',
  creatorAvatar: 'https://plain-apac-prod-public.komododecks.com/202609/26/LyZjWAf6Cm4tCwyWIQHc/image.jpg',
};

export const MOCK_USERS: Record<string, User> = {
  treasurer: {
    id: 'u_treasurer',
    name: 'Nguyễn Thu Trang',
    email: 'thutrang.treasurer@classfund.edu.vn',
    role: 'TREASURER',
    avatarUrl: 'https://api.dicebear.com/7.x/notionists/svg?seed=Trang&backgroundColor=e0f2fe',
    studentCode: 'HS-001',
  },
  moderator: {
    id: 'u_mod',
    name: 'Hoàng Minh Hải',
    email: 'hai.mod@classfund.edu.vn',
    role: 'MODERATOR',
    avatarUrl: ASSET_PATHS.creatorAvatar,
    studentCode: 'HS-008',
  },
  member: {
    id: 'u_member',
    name: 'Nguyễn Văn An',
    email: 'an.nguyen@classfund.edu.vn',
    role: 'MEMBER',
    avatarUrl: 'https://api.dicebear.com/7.x/notionists/svg?seed=An&backgroundColor=dbeafe',
    studentCode: 'HS-002',
  },
  public: {
    id: 'u_guest',
    name: 'Phụ huynh / Khách',
    email: 'guest@classfund.edu.vn',
    role: 'PUBLIC',
    avatarUrl: 'https://api.dicebear.com/7.x/notionists/svg?seed=Guest&backgroundColor=f1f5f9',
  }
};

export const MOCK_BANK_ACCOUNT: BankAccountInfo = {
  bank_name: 'MB Bank (Ngân hàng TMCP Quân Đội)',
  account_name: 'HA DAI HAI',
  account_number: '0876680302',
  branch: 'Hà Nội',
  qr_image_url: ASSET_PATHS.vietQrMock,
  transfer_syntax_example: 'HS [Họ tên] nop quy thang 10',
  deep_link: 'https://vietqr.net',
};

// Opening balance baseline
export const OPENING_BALANCE = 500000;

export const INITIAL_LEDGER_ENTRIES: LedgerEntry[] = [
  {
    id: 'tx_01',
    type: 'CREDIT',
    amount: 50000,
    currency: 'VND',
    source: 'IMAGE',
    transaction_code: 'VCB8921734',
    sender_name: 'Nguyễn Văn An',
    uploaded_by: 'Nguyễn Văn An',
    created_at: '2026-09-24 09:15',
    effective_at: '2026-09-24 09:15',
    status: 'VERIFIED',
    ai_confidence: 99.4,
    extracted_bank: 'Vietcombank',
    note: 'Đóng quỹ tháng 10',
    campaign_id: 'camp_oct2026',
    image_url: 'https://images.unsplash.com/photo-1554224155-8d04cb21cd6c?w=600&auto=format&fit=crop&q=80',
    image_hash: 'hash_vcb_8921734_sha256',
  },
  {
    id: 'tx_02',
    type: 'CREDIT',
    amount: 50000,
    currency: 'VND',
    source: 'IMAGE',
    transaction_code: 'MB90123847',
    sender_name: 'Trần Bảo Ngọc',
    uploaded_by: 'Trần Bảo Ngọc',
    created_at: '2026-09-24 11:30',
    effective_at: '2026-09-24 11:30',
    status: 'VERIFIED',
    ai_confidence: 98.7,
    extracted_bank: 'MB Bank',
    note: 'Nộp tiền quỹ đợt 1',
    campaign_id: 'camp_oct2026',
    image_url: 'https://images.unsplash.com/photo-1554224154-26032ffc0d07?w=600&auto=format&fit=crop&q=80',
    image_hash: 'hash_mb_90123847_sha256',
  },
  {
    id: 'tx_03',
    type: 'DEBIT',
    amount: 250000,
    currency: 'VND',
    source: 'MANUAL',
    transaction_code: 'EXP_PRINT_01',
    sender_name: 'Thủ quỹ Trang',
    uploaded_by: 'Nguyễn Thu Trang',
    created_at: '2026-09-24 16:00',
    effective_at: '2026-09-24 16:00',
    status: 'VERIFIED',
    note: 'In ấn 35 bộ đề cương ôn tập Toán & Lý giữa kì 1',
  },
  {
    id: 'tx_04',
    type: 'CREDIT',
    amount: 500000,
    currency: 'VND',
    source: 'IMAGE',
    transaction_code: 'ACB3341829',
    sender_name: 'Bác Hội Trưởng PH',
    uploaded_by: 'Hoàng Minh Hải',
    created_at: '2026-09-25 08:20',
    effective_at: '2026-09-25 08:20',
    status: 'VERIFIED',
    ai_confidence: 99.1,
    extracted_bank: 'ACB',
    note: 'Hội phụ huynh ủng hộ bổ sung tiền nước uống học sinh',
    image_url: 'https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=600&auto=format&fit=crop&q=80',
  },
  {
    id: 'tx_05',
    type: 'CREDIT',
    amount: 500000,
    currency: 'VND',
    source: 'IMAGE',
    transaction_code: 'TCB7788112',
    sender_name: 'Lê Hoàng Long',
    uploaded_by: 'Lê Hoàng Long',
    created_at: '2026-09-25 14:10',
    effective_at: '2026-09-25 14:10',
    status: 'VERIFIED',
    ai_confidence: 99.0,
    extracted_bank: 'Techcombank',
    note: 'Đóng tiền quỹ cả năm 10 tháng',
  },
  {
    id: 'tx_06_reverted',
    type: 'CREDIT',
    amount: 100000,
    currency: 'VND',
    source: 'IMAGE',
    transaction_code: 'BIDV662910',
    sender_name: 'Phạm Thuỳ Chi',
    uploaded_by: 'Phạm Thuỳ Chi',
    created_at: '2026-09-23 10:00',
    effective_at: '2026-09-23 10:00',
    status: 'REVERTED',
    ai_confidence: 97.2,
    extracted_bank: 'BIDV',
    note: 'Chuyển nhầm tiền quỹ hội trại vào tài khoản quỹ lớp',
    revert_reason: 'Học sinh chuyển nhầm số tiền, đã hoàn trả lại tiền mặt và thu hồi giao dịch trên sổ cái',
    reverted_by: 'Nguyễn Thu Trang (Thủ quỹ)',
    reverted_at: '2026-09-23 15:30',
    reversal_entry_id: 'tx_06_rev_entry',
  },
  {
    id: 'tx_06_rev_entry',
    type: 'REVERT',
    amount: 100000,
    currency: 'VND',
    source: 'REVERT',
    transaction_code: 'REV_BIDV662910',
    sender_name: 'Thủ quỹ Trang (Đảo giao dịch)',
    uploaded_by: 'Nguyễn Thu Trang',
    created_at: '2026-09-23 15:30',
    effective_at: '2026-09-23 15:30',
    status: 'VERIFIED',
    original_entry_id: 'tx_06_reverted',
    note: 'Bút toán đảo: Thu hồi giao dịch BIDV662910 chuyển nhầm',
  },
  {
    id: 'tx_07',
    type: 'CREDIT',
    amount: 50000,
    currency: 'VND',
    source: 'IMAGE',
    transaction_code: 'VCB4481023',
    sender_name: 'Đặng Tuấn Kiệt',
    uploaded_by: 'Đặng Tuấn Kiệt',
    created_at: '2026-09-25 19:40',
    effective_at: '2026-09-25 19:40',
    status: 'VERIFIED',
    ai_confidence: 98.9,
    extracted_bank: 'Vietcombank',
    note: 'Đóng quỹ tháng 10',
    campaign_id: 'camp_oct2026',
  },
  {
    id: 'tx_08',
    type: 'CREDIT',
    amount: 50000,
    currency: 'VND',
    source: 'IMAGE',
    transaction_code: 'MB11223344',
    sender_name: 'Vũ Hải Yến',
    uploaded_by: 'Vũ Hải Yến',
    created_at: '2026-09-26 07:15',
    effective_at: '2026-09-26 07:15',
    status: 'VERIFIED',
    ai_confidence: 99.6,
    extracted_bank: 'MB Bank',
    note: 'Quy thang 10',
    campaign_id: 'camp_oct2026',
  },
  {
    id: 'tx_09_pending',
    type: 'CREDIT',
    amount: 50000,
    currency: 'VND',
    source: 'IMAGE',
    transaction_code: 'VCB9988771',
    sender_name: 'Lê Quốc Hưng',
    uploaded_by: 'Lê Quốc Hưng',
    created_at: '2026-09-26 08:30',
    effective_at: '2026-09-26 08:30',
    status: 'NEEDS_REVIEW',
    ai_confidence: 76.5,
    extracted_bank: 'Vietcombank',
    note: 'Ảnh chụp bị mờ mã giao dịch, cần thủ quỹ kiểm tra lại sao kê ngân hàng',
  }
];

export const INITIAL_STUDENTS_ROSTER: StudentRosterItem[] = [
  { id: 'st_01', full_name: 'Nguyễn Văn An', student_code: '12A1-01', status: 'PAID', matched_amount: 50000, matched_transaction_code: 'VCB8921734', paid_at: '24/09' },
  { id: 'st_02', full_name: 'Trần Bảo Ngọc', student_code: '12A1-02', status: 'PAID', matched_amount: 50000, matched_transaction_code: 'MB90123847', paid_at: '24/09' },
  { id: 'st_03', full_name: 'Đặng Tuấn Kiệt', student_code: '12A1-03', status: 'PAID', matched_amount: 50000, matched_transaction_code: 'VCB4481023', paid_at: '25/09' },
  { id: 'st_04', full_name: 'Vũ Hải Yến', student_code: '12A1-04', status: 'PAID', matched_amount: 50000, matched_transaction_code: 'MB11223344', paid_at: '26/09' },
  { id: 'st_05', full_name: 'Lê Hoàng Long', student_code: '12A1-05', status: 'PAID', matched_amount: 50000, matched_transaction_code: 'TCB7788112', paid_at: '25/09' },
  { id: 'st_06', full_name: 'Phạm Minh Đức', student_code: '12A1-06', status: 'PAID', matched_amount: 50000, matched_transaction_code: 'VCB5566778', paid_at: '23/09' },
  { id: 'st_07', full_name: 'Bùi Phương Linh', student_code: '12A1-07', status: 'PAID', matched_amount: 50000, matched_transaction_code: 'ACB9911223', paid_at: '23/09' },
  { id: 'st_08', full_name: 'Hoàng Minh Hải', student_code: '12A1-08', status: 'PAID', matched_amount: 50000, matched_transaction_code: 'CASH_HAI', paid_at: '22/09' },
  { id: 'st_09', full_name: 'Nguyễn Thu Trang', student_code: '12A1-09', status: 'PAID', matched_amount: 50000, matched_transaction_code: 'CASH_TRANG', paid_at: '22/09' },
  { id: 'st_10', full_name: 'Đỗ Quang Huy', student_code: '12A1-10', status: 'PAID', matched_amount: 50000, matched_transaction_code: 'BIDV334455', paid_at: '24/09' },
  { id: 'st_11', full_name: 'Trần Gia Hân', student_code: '12A1-11', status: 'PAID', matched_amount: 50000, matched_transaction_code: 'VCB112299', paid_at: '24/09' },
  { id: 'st_12', full_name: 'Lý Quốc Bảo', student_code: '12A1-12', status: 'PAID', matched_amount: 50000, matched_transaction_code: 'MB778899', paid_at: '24/09' },
  { id: 'st_13', full_name: 'Mai Thanh Hằng', student_code: '12A1-13', status: 'PAID', matched_amount: 50000, matched_transaction_code: 'VPB445566', paid_at: '25/09' },
  { id: 'st_14', full_name: 'Dương Đình Trọng', student_code: '12A1-14', status: 'PAID', matched_amount: 50000, matched_transaction_code: 'ACB114477', paid_at: '25/09' },
  { id: 'st_15', full_name: 'Chu Ngọc Anh', student_code: '12A1-15', status: 'PAID', matched_amount: 50000, matched_transaction_code: 'TCB996633', paid_at: '25/09' },
  { id: 'st_16', full_name: 'Võ Thị Mỹ Duyên', student_code: '12A1-16', status: 'PAID', matched_amount: 50000, matched_transaction_code: 'MB332211', paid_at: '25/09' },
  { id: 'st_17', full_name: 'Lương Thế Vinh', student_code: '12A1-17', status: 'PAID', matched_amount: 50000, matched_transaction_code: 'VCB665544', paid_at: '25/09' },
  { id: 'st_18', full_name: 'Tạ Minh Tuấn', student_code: '12A1-18', status: 'PAID', matched_amount: 50000, matched_transaction_code: 'BIDV887766', paid_at: '25/09' },
  { id: 'st_19', full_name: 'Hồ Quỳnh Mai', student_code: '12A1-19', status: 'PAID', matched_amount: 50000, matched_transaction_code: 'ACB552211', paid_at: '25/09' },
  { id: 'st_20', full_name: 'Phan Tuấn Tú', student_code: '12A1-20', status: 'PAID', matched_amount: 50000, matched_transaction_code: 'TCB441188', paid_at: '25/09' },
  { id: 'st_21', full_name: 'Nông Thuỳ Chi', student_code: '12A1-21', status: 'PAID', matched_amount: 50000, matched_transaction_code: 'VCB774411', paid_at: '26/09' },
  { id: 'st_22', full_name: 'Đoàn Nhật Quang', student_code: '12A1-22', status: 'PAID', matched_amount: 50000, matched_transaction_code: 'MB995511', paid_at: '26/09' },
  // 13 students UNPAID (Total 22/35 PAID)
  { id: 'st_23', full_name: 'Nguyễn Thành Nam', student_code: '12A1-23', status: 'UNPAID' },
  { id: 'st_24', full_name: 'Trịnh Hoàng Bách', student_code: '12A1-24', status: 'UNPAID' },
  { id: 'st_25', full_name: 'Lê Quốc Hưng', student_code: '12A1-25', status: 'UNPAID', notes: 'Biên lai đang chờ duyệt' },
  { id: 'st_26', full_name: 'Phạm Thị Thu Trang', student_code: '12A1-26', status: 'UNPAID' },
  { id: 'st_27', full_name: 'Vũ Đức Thịnh', student_code: '12A1-27', status: 'UNPAID' },
  { id: 'st_28', full_name: 'Hoàng Kim Ngân', student_code: '12A1-28', status: 'UNPAID' },
  { id: 'st_29', full_name: 'Lâm Gia Bảo', student_code: '12A1-29', status: 'UNPAID' },
  { id: 'st_30', full_name: 'Thân Trọng Nghĩa', student_code: '12A1-30', status: 'UNPAID' },
  { id: 'st_31', full_name: 'Đỗ Thị Thu Hương', student_code: '12A1-31', status: 'UNPAID' },
  { id: 'st_32', full_name: 'Cao Tiến Đạt', student_code: '12A1-32', status: 'UNPAID' },
  { id: 'st_33', full_name: 'Ngô Mỹ Linh', student_code: '12A1-33', status: 'UNPAID' },
  { id: 'st_34', full_name: 'Trương Vĩnh Kỳ', student_code: '12A1-34', status: 'UNPAID' },
  { id: 'st_35', full_name: 'Bạch Đình Duy', student_code: '12A1-35', status: 'UNPAID' },
];

export const INITIAL_CAMPAIGN: CollectionCampaign = {
  id: 'camp_oct2026',
  title: 'Quỹ hoạt động tháng 10 & 20/10',
  description: 'Đợt thu thường niên chi phí nước uống, in ấn tài liệu cương ôn thi giữa kì và chuẩn bị quà tặng cô giáo ngày 20/10.',
  expected_amount_per_student: 50000,
  target_students_count: 35,
  paid_students_count: 22,
  total_collected_amount: 1100000,
  start_at: '2026-09-20',
  end_at: '2026-09-30',
  status: 'ACTIVE',
};

export const INITIAL_CHAT_MESSAGES: ChatMessage[] = [
  {
    id: 'msg_mod_01',
    sender_id: 'u_mod',
    sender_name: 'Hoàng Minh Hải',
    sender_role: 'MODERATOR',
    message_type: 'ANNOUNCEMENT',
    content: 'Thông báo: Hạn đóng quỹ tháng 10 là ngày 30/09/2026. Các bạn vui lòng quét mã VietQR ở góc trên hoặc chuyển khoản kèm nội dung cú pháp, sau đó chụp ảnh màn hình tải lên đây để hệ thống AI tự động ghi nhận nhé!',
    is_pinned: true,
    created_at: '2026-09-22 08:00',
  },
  {
    id: 'msg_02',
    sender_id: 'u_member',
    sender_name: 'Nguyễn Văn An',
    sender_role: 'MEMBER',
    message_type: 'RECEIPT',
    content: 'Mình vừa chuyển 50k quỹ tháng 10 bằng Vietcombank xong nè, bot duyệt giúp mình nhé!',
    receipt_data: {
      entry_id: 'tx_01',
      amount: 50000,
      transaction_code: 'VCB8921734',
      image_url: 'https://images.unsplash.com/photo-1554224155-8d04cb21cd6c?w=600&auto=format&fit=crop&q=80',
      status: 'VERIFIED',
      sender_name: 'Nguyễn Văn An',
      uploader_name: 'Nguyễn Văn An',
      time: '24/09 09:15',
    },
    created_at: '2026-09-24 09:16',
  },
  {
    id: 'msg_03',
    sender_id: 'u_treasurer',
    sender_name: 'Nguyễn Thu Trang',
    sender_role: 'TREASURER',
    message_type: 'TEXT',
    content: 'Cảm ơn An nha, hệ thống AI đã khớp mã giao dịch VCB8921734 và tự động cập nhật trạng thái "Đã nộp" trên danh sách lớp rồi nhé!',
    created_at: '2026-09-24 09:18',
  },
  {
    id: 'msg_04',
    sender_id: 'u_member_2',
    sender_name: 'Trần Bảo Ngọc',
    sender_role: 'MEMBER',
    message_type: 'RECEIPT',
    content: 'Tớ nộp qua MB Bank lúc 11h30 ạ.',
    receipt_data: {
      entry_id: 'tx_02',
      amount: 50000,
      transaction_code: 'MB90123847',
      image_url: 'https://images.unsplash.com/photo-1554224154-26032ffc0d07?w=600&auto=format&fit=crop&q=80',
      status: 'VERIFIED',
      sender_name: 'Trần Bảo Ngọc',
      uploader_name: 'Trần Bảo Ngọc',
      time: '24/09 11:30',
    },
    created_at: '2026-09-24 11:31',
  },
  {
    id: 'msg_05',
    sender_id: 'u_mod',
    sender_name: 'Hoàng Minh Hải',
    sender_role: 'MODERATOR',
    message_type: 'ANNOUNCEMENT',
    content: 'Hiện tại đã có 22/35 bạn hoàn thành đợt thu tháng 10. Còn 13 bạn chưa nộp tranh thủ trước hạn 30/09 nha, nếu có trục trặc chuyển khoản nhắn liền cho mình hoặc Trang!',
    is_pinned: false,
    created_at: '2026-09-25 18:00',
  }
];

export const INITIAL_AUDIT_LOGS: AuditLogItem[] = [
  {
    id: 'aud_01',
    actor_name: 'Hệ thống AI & Ledger Core',
    actor_role: 'TREASURER',
    action: 'POST_CREDIT',
    entity_type: 'TRANSACTION',
    entity_id: 'tx_01',
    details: 'Xác thực biên lai VCB8921734 từ Nguyễn Văn An (+50.000 ₫). Confidence: 99.4%.',
    created_at: '2026-09-24 09:15',
  },
  {
    id: 'aud_02',
    actor_name: 'Nguyễn Thu Trang',
    actor_role: 'TREASURER',
    action: 'POST_DEBIT',
    entity_type: 'TRANSACTION',
    entity_id: 'tx_03',
    details: 'Chi quỹ 250.000 ₫ in đề cương ôn tập Toán - Lý kì 1 cho 35 học sinh.',
    created_at: '2026-09-24 16:00',
  },
  {
    id: 'aud_03',
    actor_name: 'Nguyễn Thu Trang',
    actor_role: 'TREASURER',
    action: 'REVERT_TRANSACTION',
    entity_type: 'TRANSACTION',
    entity_id: 'tx_06_reverted',
    details: 'Thu hồi giao dịch BIDV662910 (+100.000 ₫) do học sinh chuyển nhầm. Tạo bút toán đảo REV_BIDV662910.',
    created_at: '2026-09-23 15:30',
  },
];

/**
 * Ledger Helper: calculate verified balances in accordance with Section 1.1:
 * current_balance = opening_balance + sum(valid_credits) - sum(valid_debits)
 */
export function calculateLedgerBalances(entries: LedgerEntry[], opening: number = OPENING_BALANCE) {
  let totalCredit = 0;
  let totalDebit = 0;

  for (const entry of entries) {
    if (entry.status !== 'VERIFIED') continue;

    if (entry.type === 'CREDIT') {
      totalCredit += entry.amount;
    } else if (entry.type === 'DEBIT') {
      totalDebit += entry.amount;
    } else if (entry.type === 'REVERT') {
      // Reversal entry cancels the corresponding credit
      totalDebit += entry.amount;
    }
  }

  const currentBalance = opening + totalCredit - totalDebit;

  return {
    openingBalance: opening,
    totalCredit,
    totalDebit,
    currentBalance,
  };
}

export function formatVND(amount: number): string {
  return new Intl.NumberFormat('vi-VN', {
    style: 'currency',
    currency: 'VND',
    maximumFractionDigits: 0,
  }).format(amount);
}
