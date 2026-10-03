# 08_api_adapter.md

## API Adapter Specification

### Overview
The API adapter layer provides typed HTTP client methods for all Guest Chat backend endpoints. It handles error responses, upload progress, and integrates with the recall token storage.

### Base Configuration
```typescript
const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';
```

### Endpoints

#### 1. Upload Receipt Image
```typescript
POST /api/v1/uploads
Content-Type: multipart/form-data

Body:
- file: File (image/jpeg, image/png, image/webp, max 5MB)
- uploader_name: string

Response: UploadResponse
{
  id: string;
  uploader_name: string;
  original_filename: string;
  status: string;
  created_at: string;
}
```

#### 2. Get Upload Status
```typescript
GET /api/v1/uploads/{upload_id}

Response: UploadStatusResponse
{
  id: string;
  uploader_name: string;
  original_filename: string;
  status: string;
  created_at: string;
  extracted?: {
    transaction_code?: string;
    amount?: number;
    sender_name?: string;
    bank_name?: string;
    transaction_time?: string;
    confidence?: number;
    status: string;
  };
  transaction_id?: string;
  rejection_reason?: string;
}
```

#### 3. Create Message
```typescript
POST /api/v1/messages
Content-Type: application/json

Body: MessageCreateRequest
{
  conversation_id: string;
  sender_name: string;
  sender_photo?: string;
  message_type: 'TEXT' | 'RECEIPT' | 'IMAGE' | 'ANNOUNCEMENT';
  content: string;
  attachment_ids?: string[];
}

Response: MessageCreateResponse
{
  message_id: string;
  public_code: string;
  recall_token: string;  // ONLY returned once!
  status: MessageStatus;
  created_at: string;
}
```

#### 4. Get Message Status
```typescript
GET /api/v1/messages/{message_id}

Response: MessageStatusResponse
{
  message_id: string;
  conversation_id: string;
  sender_name: string;
  sender_role: string;
  message_type: string;
  content: string;
  status: MessageStatus;
  public_code?: string;
  transaction_id?: string;
  error_message?: string;
  created_at: string;
  processed_at?: string;
}
```

#### 5. Recall Message
```typescript
POST /api/v1/messages/{message_id}/recall
Content-Type: application/json

Body: RecallRequest
{
  recall_token: string;  // 64-char hex from sessionStorage
  reason: string;
}

Response: RecallResponse
{
  message_id: string;
  status: MessageStatus;
  recalled_at: string;
  reversal_transaction_id?: string;
}
```

#### 6. List Messages
```typescript
GET /api/v1/messages?conversation_id={id}&status={status}&limit=50&offset=0

Response: MessageStatusResponse[]
```

#### 7. Public Fund Info
```typescript
GET /api/v1/public/fund

Response: PublicFundResponse
{
  account_id: string;
  currency: string;
  current_balance: number;
  total_income: number;
  total_expense: number;
}
```

#### 8. Public Bank Accounts
```typescript
GET /api/v1/public/bank-accounts

Response: BankAccountResponse[]
[
  {
    bank_name: string;
    account_name: string;
    account_number: string;
    payment_link?: string;
    qr_image_url?: string;
  }
]
```

### Error Handling

```typescript
class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: unknown
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

// Usage
try {
  const response = await apiClient.createMessage(data);
} catch (err) {
  if (err instanceof ApiError) {
    switch (err.status) {
      case 400: // Validation error
      case 404: // Not found
      case 409: // Conflict (duplicate)
      case 413: // File too large
      case 415: // Unsupported media type
      case 422: // Unprocessable entity
      case 500: // Server error
    }
  }
}
```

### Upload with Progress (XHR)

```typescript
async function uploadWithProgress(
  file: File,
  uploaderName: string,
  onProgress: (progress: number) => void
): Promise<UploadResponse> {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('uploader_name', uploaderName);

    const xhr = new XMLHttpRequest();

    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable) {
        const progress = Math.round((event.loaded / event.total) * 100);
        onProgress(progress);
      }
    });

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        reject(new ApiError(...));
      }
    });

    xhr.addEventListener('error', () => reject(new ApiError('Network error', 0)));
    xhr.addEventListener('abort', () => reject(new ApiError('Upload cancelled', 0)));

    xhr.open('POST', `${API_BASE}/uploads`);
    xhr.send(formData);
  });
}
```

### Recall Token Storage

```typescript
const RECALL_TOKEN_KEY = 'classfund_recall_tokens';

function storeRecallToken(messageId: string, token: string) {
  try {
    const data = JSON.parse(sessionStorage.getItem(RECALL_TOKEN_KEY) || '{}');
    data[messageId] = token;
    sessionStorage.setItem(RECALL_TOKEN_KEY, JSON.stringify(data));
  } catch (e) { console.error('Failed to store recall token:', e); }
}

function getRecallToken(messageId: string): string | null {
  try {
    const data = JSON.parse(sessionStorage.getItem(RECALL_TOKEN_KEY) || '{}');
    return data[messageId] || null;
  } catch { return null; }
}

function removeRecallToken(messageId: string) {
  try {
    const data = JSON.parse(sessionStorage.getItem(RECALL_TOKEN_KEY) || '{}');
    delete data[messageId];
    sessionStorage.setItem(RECALL_TOKEN_KEY, JSON.stringify(data));
  } catch (e) { console.error('Failed to remove recall token:', e); }
}
```

### Type Definitions
```typescript
// Request types
interface MessageCreateRequest {
  conversation_id: string;
  sender_name: string;
  sender_photo?: string;
  message_type: 'TEXT' | 'RECEIPT' | 'IMAGE' | 'ANNOUNCEMENT';
  content: string;
  attachment_ids?: string[];
}

interface RecallRequest {
  recall_token: string;
  reason: string;
}

// Response types
interface MessageCreateResponse {
  message_id: string;
  public_code: string;
  recall_token: string;
  status: MessageStatus;
  created_at: string;
}

interface RecallResponse {
  message_id: string;
  status: MessageStatus;
  recalled_at: string;
  reversal_transaction_id?: string;
}

interface MessageStatusResponse {
  message_id: string;
  conversation_id: string;
  sender_name: string;
  sender_role: string;
  message_type: string;
  content: string;
  status: MessageStatus;
  public_code?: string;
  transaction_id?: string;
  error_message?: string;
  created_at: string;
  processed_at?: string;
}

interface UploadResponse {
  id: string;
  uploader_name: string;
  original_filename: string;
  status: string;
  created_at: string;
}

interface PublicFundResponse {
  account_id: string;
  currency: string;
  current_balance: number;
  total_income: number;
  total_expense: number;
}

interface BankAccountResponse {
  bank_name: string;
  account_name: string;
  account_number: string;
  payment_link?: string;
  qr_image_url?: string;
}
```

### Usage in useChat Hook
```typescript
const {
  sendMessage,
  recallMessage,
  addUpload,
  removeUpload,
  retryUpload,
  refreshMessages,
} = useChat({
  conversationId: 'classfund_main',
  currentUserRole: 'PUBLIC',
  currentUserName: 'Guest User',
});

// Send message with images
await sendMessage({
  content: 'Đã chuyển khoản 50k',
  message_type: 'IMAGE',
  sender_name: 'Nguyễn Văn An',
  attachment_ids: ['upload_1', 'upload_2'],
});

// Recall message
await recallMessage('msg_123', 'pending', 'Nhập sai số tiền');
```

### Testing
- Mock fetch/XHR for unit tests
- Test error handling for each status code
- Test upload progress callbacks
- Test recall token storage/retrieval
- Test sessionStorage persistence across navigation