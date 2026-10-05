import { useCallback } from 'react';
import { RecallEligibility } from '../lib/recall';
import { apiClient } from '../lib/api';

export interface UseRecallReturn {
  checkEligibility: (messageId: string) => Promise<RecallEligibility>;
  storeRecallToken: (messageId: string, token: string) => void;
  getStoredRecallToken: (messageId: string) => string | null;
  removeRecallToken: (messageId: string) => void;
}

export function useRecall(): UseRecallReturn {
  const checkEligibility = useCallback(async (messageId: string) => {
    try {
      const response = await fetch(`${apiClient['constructor'].prototype.constructor ? '' : ''}/api/v1/messages/${messageId}/recall-eligibility`);
      if (!response.ok) {
        throw new Error(`Failed to check eligibility: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.warn('[useRecall] Server eligibility check failed:', error);
      // Return a basic eligibility object
      return {
        eligible: false,
        message_id: messageId,
        status: 'unknown',
        reason: 'Failed to check eligibility',
        can_recall_before_post: false,
        can_recall_after_post: false,
        has_token: false,
        token_expired: false,
        token_used: false,
        token_revoked: false,
        already_recalled: false,
        transaction_posted: false,
      };
    }
  }, []);

  const storeRecallToken = useCallback((messageId: string, token: string) => {
    try {
      const data = sessionStorage.getItem('classfund_recall_tokens');
      const tokens = data ? JSON.parse(data) : {};
      tokens[messageId] = token;
      sessionStorage.setItem('classfund_recall_tokens', JSON.stringify(tokens));
    } catch (error) {
      console.error('[useRecall] Failed to store recall token:', error);
    }
  }, []);

  const getStoredRecallToken = useCallback((messageId: string): string | null => {
    try {
      const data = sessionStorage.getItem('classfund_recall_tokens');
      if (!data) return null;
      const tokens = JSON.parse(data) as Record<string, string>;
      return tokens[messageId] || null;
    } catch {
      return null;
    }
  }, []);

  const removeRecallToken = useCallback((messageId: string) => {
    try {
      const data = sessionStorage.getItem('classfund_recall_tokens');
      if (!data) return;
      const tokens = JSON.parse(data) as Record<string, string>;
      delete tokens[messageId];
      sessionStorage.setItem('classfund_recall_tokens', JSON.stringify(tokens));
    } catch (error) {
      console.error('[useRecall] Failed to remove recall token:', error);
    }
  }, []);

  return {
    checkEligibility,
    storeRecallToken,
    getStoredRecallToken,
    removeRecallToken,
  };
}