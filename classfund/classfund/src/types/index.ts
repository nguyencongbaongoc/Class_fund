// Backend canonical roles (authoritative - matches database enum)
export type BackendRole = 'OWNER_TREASURER' | 'MODERATOR' | 'MEMBER' | 'PUBLIC';

// Frontend display roles (UI compatible - for display only)
export type FrontendRole = 'TREASURER' | 'MODERATOR' | 'MEMBER' | 'PUBLIC';

// Legacy alias for backward compatibility
export type UserRole = FrontendRole;

/**
 * Normalizes backend canonical role to frontend display role.
 * Backend is authoritative; this is a one-way mapping for UI display only.
 */
export function normalizeRole(backendRole: BackendRole): FrontendRole {
  switch (backendRole) {
    case 'OWNER_TREASURER':
      return 'TREASURER';
    case 'MODERATOR':
      return 'MODERATOR';
    case 'MEMBER':
      return 'MEMBER';
    case 'PUBLIC':
      return 'PUBLIC';
    default:
      // Fail closed - unknown roles get minimal access
      return 'PUBLIC';
  }
}

/**
 * Validates that a role string is a known backend role.
 * Returns the canonical backend role or null if invalid.
 */
export function validateBackendRole(role: string): BackendRole | null {
  const validRoles: BackendRole[] = ['OWNER_TREASURER', 'MODERATOR', 'MEMBER', 'PUBLIC'];
  return validRoles.includes(role as BackendRole) ? role as BackendRole : null;
}

// Phase 4: Message status types (matching backend)
export type MessageStatus = 
  | 'pending'
  | 'processing'
  | 'awaiting_review'
  | 'posted'
  | 'rejected'
  | 'failed'
  | 'recalled';

export type MessageType = 'TEXT' | 'RECEIPT' | 'IMAGE' | 'ANNOUNCEMENT' | 'SYSTEM';

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  avatarUrl: string;
  studentCode?: string;
}

export type TransactionType = 'CREDIT' | 'DEBIT' | 'REVERT';
export type TransactionStatus = 'PENDING' | 'VERIFIED' | 'NEEDS_REVIEW' | 'DUPLICATE' | 'REJECTED' | 'REVERTED';
export type TransactionSource = 'IMAGE' | 'MANUAL' | 'REVERT';

export interface LedgerEntry {
  id: string;
  type: TransactionType;
  amount: number;
  currency: 'VND';
  source: TransactionSource;
  transaction_code: string;
  sender_name: string;
  uploaded_by: string;
  created_at: string;
  effective_at: string;
  status: TransactionStatus;
  original_entry_id?: string;
  reversal_entry_id?: string;
  image_url?: string;
  image_hash?: string;
  note?: string;
  campaign_id?: string;
  ai_confidence?: number;
  extracted_bank?: string;
  revert_reason?: string;
  reverted_by?: string;
  reverted_at?: string;
}

export interface StudentRosterItem {
  id: string;
  full_name: string;
  student_code: string;
  status: 'PAID' | 'UNPAID';
  matched_amount?: number;
  matched_transaction_code?: string;
  paid_at?: string;
  notes?: string;
}

export interface CollectionCampaign {
  id: string;
  title: string;
  description: string;
  expected_amount_per_student: number;
  target_students_count: number;
  paid_students_count: number;
  total_collected_amount: number;
  start_at: string;
  end_at: string;
  status: 'ACTIVE' | 'CLOSED';
}

export interface ChatMessage {
  id: string;
  sender_id: string;
  sender_name: string;
  sender_role: UserRole;
  message_type: MessageType;
  content: string;
  attachment_id?: string;
  status: MessageStatus;
  public_code?: string;
  transaction_id?: string;
  error_message?: string;
  receipt_data?: {
    entry_id: string;
    amount: number;
    transaction_code: string;
    image_url: string;
    status: TransactionStatus;
    sender_name: string;
    uploader_name: string;
    time: string;
  };
  is_pinned?: boolean;
  created_at: string;
  // Frontend-only fields
  recall_token?: string;
  is_optimistic?: boolean;
  upload_progress?: number;
}

export interface BankAccountInfo {
  bank_name: string;
  account_name: string;
  account_number: string;
  branch: string;
  qr_image_url: string;
  transfer_syntax_example: string;
  deep_link?: string;
}

export interface AuditLogItem {
  id: string;
  actor_name: string;
  actor_role: UserRole;
  action: string;
  entity_type: string;
  entity_id: string;
  details: string;
  created_at: string;
}

export type ViewTab = 
  | 'dashboard' 
  | 'ledger' 
  | 'upload' 
  | 'campaign' 
  | 'chat' 
  | 'guest-chat'
  | 'bank' 
  | 'donate' 
  | 'public'
  // Admin tabs
  | 'admin-dashboard'
  | 'admin-review'
  | 'admin-ledger'
  | 'admin-audit'
  | 'admin-system'
  | 'admin-users';
