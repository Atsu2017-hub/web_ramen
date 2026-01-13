/**
 * menu.jsモジュールのテスト
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { getMenus } from '../src/menu.js';

// API_BASE_URLをモック（実際には使用されないが、インポートエラーを防ぐ）
vi.mock('../src/auth.js', () => ({
  API_BASE_URL: 'http://localhost:8000'
}));

import { API_BASE_URL } from '../src/auth.js';

describe('menu.js', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getMenus', () => {
    it('正常にメニュー一覧を取得する', async () => {
      const mockMenus = [
        {
          id: 1,
          name: '本格ラーメン',
          description: 'テスト用ラーメン',
          price: 850,
          image_url: 'ramen.png',
          is_available: true
        },
        {
          id: 2,
          name: '特製丼',
          description: 'テスト用丼',
          price: 750,
          image_url: 'don.png',
          is_available: true
        }
      ];

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockMenus
      });

      const result = await getMenus();
      expect(result).toEqual(mockMenus);
      expect(fetch).toHaveBeenCalledWith(
        `${API_BASE_URL}/api/menus`,
        expect.objectContaining({
          method: 'GET'
        })
      );
    });

    it('エラーレスポンスの場合はエラーをthrowする', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: 'メニューの取得に失敗しました' })
      });

      await expect(getMenus())
        .rejects.toThrow('メニューの取得に失敗しました');
    });

    it('ネットワークエラーの場合はエラーをthrowする', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(getMenus())
        .rejects.toThrow('Network error');
    });
  });
});

