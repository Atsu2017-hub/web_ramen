/**
 * auth.jsモジュールのテスト
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  getToken,
  setToken,
  removeToken,
  getCurrentUser,
  register,
  login,
  logout,
  authenticatedFetch,
  API_BASE_URL
} from '../src/auth.js';

describe('auth.js', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  describe('getToken', () => {
    it('トークンが存在する場合は返す', () => {
      localStorage.getItem.mockReturnValue('test-token');
      expect(getToken()).toBe('test-token');
      expect(localStorage.getItem).toHaveBeenCalledWith('access_token');
    });

    it('トークンが存在しない場合はnullを返す', () => {
      localStorage.getItem.mockReturnValue(null);
      expect(getToken()).toBeNull();
    });
  });

  describe('setToken', () => {
    it('トークンをlocalStorageに保存する', () => {
      setToken('new-token');
      expect(localStorage.setItem).toHaveBeenCalledWith('access_token', 'new-token');
    });
  });

  describe('removeToken', () => {
    it('トークンをlocalStorageから削除する', () => {
      removeToken();
      expect(localStorage.removeItem).toHaveBeenCalledWith('access_token');
    });
  });

  describe('getCurrentUser', () => {
    it('トークンが無い場合はnullを返す', async () => {
      localStorage.getItem.mockReturnValue(null);
      const user = await getCurrentUser();
      expect(user).toBeNull();
      expect(fetch).not.toHaveBeenCalled();
    });

    it('有効なトークンでユーザー情報を取得する', async () => {
      localStorage.getItem.mockReturnValue('valid-token');
      const mockUser = { id: 1, email: 'test@example.com', name: 'テストユーザー' };
      
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockUser
      });

      const user = await getCurrentUser();
      expect(user).toEqual(mockUser);
      expect(fetch).toHaveBeenCalledWith(
        `${API_BASE_URL}/api/auth/me`,
        expect.objectContaining({
          method: 'GET',
          headers: expect.objectContaining({
            'Authorization': 'Bearer valid-token'
          })
        })
      );
    });

    it('無効なトークンの場合はnullを返し、トークンを削除する', async () => {
      localStorage.getItem.mockReturnValue('invalid-token');
      
      fetch.mockResolvedValueOnce({
        ok: false,
        status: 401
      });

      const user = await getCurrentUser();
      expect(user).toBeNull();
      expect(localStorage.removeItem).toHaveBeenCalledWith('access_token');
    });
  });

  describe('register', () => {
    it('正常に登録し、トークンを保存する', async () => {
      const userData = {
        email: 'new@example.com',
        password: 'password123',
        name: '新規ユーザー'
      };
      const mockResponse = {
        user: { id: 1, ...userData },
        access_token: 'new-token',
        token_type: 'bearer'
      };

      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      });

      const result = await register(userData.email, userData.password, userData.name);
      expect(result).toEqual(mockResponse);
      expect(localStorage.setItem).toHaveBeenCalledWith('access_token', 'new-token');
      expect(fetch).toHaveBeenCalledWith(
        `${API_BASE_URL}/api/auth/register`,
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json'
          }),
          body: JSON.stringify(userData)
        })
      );
    });

    it('エラーレスポンスの場合はエラーをthrowする', async () => {
      const userData = {
        email: 'existing@example.com',
        password: 'password123',
        name: 'ユーザー'
      };

      fetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: '既に登録されています' })
      });

      await expect(register(userData.email, userData.password, userData.name))
        .rejects.toThrow('既に登録されています');
    });
  });

  describe('login', () => {
    it('正常にログインし、トークンを保存する', async () => {
      const loginData = {
        email: 'test@example.com',
        password: 'password123'
      };
      const mockResponse = {
        user: { id: 1, email: loginData.email, name: 'テストユーザー' },
        access_token: 'login-token',
        token_type: 'bearer'
      };

      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      });

      const result = await login(loginData.email, loginData.password);
      expect(result).toEqual(mockResponse);
      expect(localStorage.setItem).toHaveBeenCalledWith('access_token', 'login-token');
    });

    it('エラーレスポンスの場合はエラーをthrowする', async () => {
      fetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: 'メールアドレスまたはパスワードが正しくありません' })
      });

      await expect(login('wrong@example.com', 'wrongpass'))
        .rejects.toThrow('メールアドレスまたはパスワードが正しくありません');
    });
  });

  describe('logout', () => {
    it('トークンを削除し、ページをリロードする', () => {
      logout();
      expect(localStorage.removeItem).toHaveBeenCalledWith('access_token');
      expect(window.location.reload).toHaveBeenCalled();
    });
  });

  describe('authenticatedFetch', () => {
    it('トークンが無い場合はエラーをthrowする', async () => {
      localStorage.getItem.mockReturnValue(null);
      
      await expect(authenticatedFetch('/api/test'))
        .rejects.toThrow('ログインが必要です');
    });

    it('有効なトークンでリクエストを送信する', async () => {
      localStorage.getItem.mockReturnValue('valid-token');
      const mockResponse = { data: 'test' };

      fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse
      });

      const response = await authenticatedFetch('/api/test', {
        method: 'POST',
        body: JSON.stringify({ test: 'data' })
      });

      expect(fetch).toHaveBeenCalledWith(
        '/api/test',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Authorization': 'Bearer valid-token',
            'Content-Type': 'application/json'
          }),
          body: JSON.stringify({ test: 'data' })
        })
      );
      expect(response.ok).toBe(true);
    });

    it('401エラーの場合はトークンを削除し、エラーをthrowする', async () => {
      localStorage.getItem.mockReturnValue('expired-token');

      fetch.mockResolvedValueOnce({
        ok: false,
        status: 401
      });

      await expect(authenticatedFetch('/api/test'))
        .rejects.toThrow('セッションが期限切れです。再度ログインしてください。');
      expect(localStorage.removeItem).toHaveBeenCalledWith('access_token');
    });
  });
});

