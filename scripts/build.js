#!/usr/bin/env node

/**
 * 本番環境用の静的ファイルをビルドするスクリプト
 * 必要なファイルを dist/ ディレクトリにコピーします
 */

import { execSync } from 'child_process';
import { existsSync, mkdirSync, cpSync, rmSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = join(__dirname, '..');
const distDir = join(projectRoot, 'dist');

// コマンドライン引数を確認
const args = process.argv.slice(2);
const clean = args.includes('--clean');

// dist ディレクトリをクリーンアップ
if (clean && existsSync(distDir)) {
  console.log('Cleaning dist directory...');
  rmSync(distDir, { recursive: true, force: true });
}

// dist ディレクトリを作成
if (!existsSync(distDir)) {
  mkdirSync(distDir, { recursive: true });
}

// コピーするファイルとディレクトリ
const filesToCopy = [
  'index.html',
  'style.css',
  'script.js',
  'src',
  '画像',
];

console.log('Building static files for production...');

// ファイルとディレクトリをコピー
filesToCopy.forEach(item => {
  const source = join(projectRoot, item);
  const destination = join(distDir, item);
  
  if (existsSync(source)) {
    try {
      cpSync(source, destination, { recursive: true });
      console.log(`✓ Copied ${item}`);
    } catch (error) {
      console.error(`✗ Failed to copy ${item}:`, error.message);
    }
  } else {
    console.warn(`⚠ ${item} not found, skipping...`);
  }
});

console.log('\n✓ Build completed!');
console.log(`  Output directory: ${distDir}`);
