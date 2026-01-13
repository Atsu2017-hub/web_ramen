/**
 * Vitestテスト環境のセットアップ
 */
import { vi } from 'vitest';
import { beforeEach, afterEach } from 'vitest';

// グローバルfetchのモック
global.fetch = vi.fn();

// localStorageのモック
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
global.localStorage = localStorageMock;

// window.locationのモック
Object.defineProperty(window, 'location', {
  value: {
    hash: '',
    reload: vi.fn(),
  },
  writable: true,
});

// 各テスト前にモックをリセット
beforeEach(() => {
  vi.clearAllMocks();
  localStorageMock.getItem.mockReturnValue(null);
});

// テスト後のクリーンアップ
afterEach(() => {
  vi.clearAllMocks();
});

