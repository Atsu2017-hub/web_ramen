/**
 * reservation.jsモジュールのテスト
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  createReservation,
  getReservations,
  cancelReservation
} from '../src/reservation.js';

// auth.jsのモジュールをモック
vi.mock('../src/auth.js', () => ({
  authenticatedFetch: vi.fn(),
  API_BASE_URL: 'http://localhost:8000'
}));

import { authenticatedFetch, API_BASE_URL } from '../src/auth.js';

describe('reservation.js', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('createReservation', () => {
    it('正常に予約を作成する', async () => {
      const reservationData = {
        reservation_date: '2024-12-31',
        reservation_time: '18:00',
        number_of_people: 2,
        menu_items: [{ menu_id: 1, quantity: 2 }]
      };
      const mockResponse = {
        id: 1,
        ...reservationData,
        status: 'pending'
      };

      authenticatedFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      });

      const result = await createReservation(reservationData);
      expect(result).toEqual(mockResponse);
      expect(authenticatedFetch).toHaveBeenCalledWith(
        `${API_BASE_URL}/api/reservations`,
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(reservationData)
        })
      );
    });

    it('エラーレスポンスの場合はエラーをthrowする', async () => {
      const reservationData = {
        reservation_date: '2024-12-31',
        reservation_time: '18:00',
        number_of_people: 2
      };

      authenticatedFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: '予約の作成に失敗しました' })
      });

      await expect(createReservation(reservationData))
        .rejects.toThrow('予約の作成に失敗しました');
    });
  });

  describe('getReservations', () => {
    it('正常に予約一覧を取得する', async () => {
      const mockReservations = [
        {
          id: 1,
          reservation_date: '2024-12-31',
          reservation_time: '18:00',
          number_of_people: 2
        },
        {
          id: 2,
          reservation_date: '2025-01-01',
          reservation_time: '19:00',
          number_of_people: 4
        }
      ];

      authenticatedFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockReservations
      });

      const result = await getReservations();
      expect(result).toEqual(mockReservations);
      expect(authenticatedFetch).toHaveBeenCalledWith(
        `${API_BASE_URL}/api/reservations`,
        expect.objectContaining({
          method: 'GET'
        })
      );
    });

    it('空の配列を返す場合がある', async () => {
      authenticatedFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => []
      });

      const result = await getReservations();
      expect(result).toEqual([]);
    });
  });

  describe('cancelReservation', () => {
    it('正常に予約をキャンセルする', async () => {
      const reservationId = 1;
      const mockResponse = {
        message: '予約がキャンセルされました',
        reservation_id: reservationId
      };

      authenticatedFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      });

      const result = await cancelReservation(reservationId);
      expect(result).toEqual(mockResponse);
      expect(authenticatedFetch).toHaveBeenCalledWith(
        `${API_BASE_URL}/api/reservations/${reservationId}`,
        expect.objectContaining({
          method: 'DELETE'
        })
      );
    });

    it('エラーレスポンスの場合はエラーをthrowする', async () => {
      const reservationId = 999;

      authenticatedFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: '予約が見つかりません' })
      });

      await expect(cancelReservation(reservationId))
        .rejects.toThrow('予約が見つかりません');
    });
  });
});

