#!/usr/bin/env node

/**
 * Frontend Development Script
 * Provides development utilities for the Next.js frontend
 */

const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const FRONTEND_ROOT = path.dirname(__dirname);
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';

function runCommand(command, args = [], options = {}) {
    return new Promise((resolve, reject) => {
        console.log(`🚀 Running: ${command} ${args.join(' ')}`);
        
        const child = spawn(command, args, {
            cwd: FRONTEND_ROOT,
            stdio: 'inherit',
            shell: process.platform === 'win32',
            ...options
        });
        
        child.on('close', (code) => {
            if (code === 0) {
                resolve(code);
            } else {
                reject(new Error(`Command failed with code ${code}`));
            }
        });
        
        child.on('error', reject);
    });
}

async function dev(port = 3000) {
    console.log(`🎨 Starting frontend development server on port ${port}`);
    console.log(`📡 API Base: ${API_BASE}`);
    console.log(`🧠 Workspace: http://localhost:${port}/workspace`);
    
    await runCommand('npm', ['run', 'dev', '--', '--port', port.toString()]);
}

async function build() {
    console.log('🔨 Building frontend for production');
    await runCommand('npm', ['run', 'build']);
    console.log('✅ Build completed');
}

async function start(port = 3000) {
    console.log(`🚀 Starting production server on port ${port}`);
    await runCommand('npm', ['run', 'start', '--', '--port', port.toString()]);
}

async function lint() {
    console.log('🔍 Running ESLint');
    await runCommand('npm', ['run', 'lint']);
    console.log('✅ Linting completed');
}

async function test() {
    console.log('🧪 Running frontend tests');
    // Add test command when tests are configured
    console.log('📝 No tests configured yet');
}

async function install() {
    console.log('📦 Installing dependencies');
    await runCommand('npm', ['install']);
    console.log('✅ Dependencies installed');
}

async function checkEnv() {
    const envPath = path.join(FRONTEND_ROOT, '.env.local');
    
    console.log('🔧 Environment Configuration:');
    console.log(`  📁 Frontend Root: ${FRONTEND_ROOT}`);
    console.log(`  📡 API Base: ${API_BASE}`);
    console.log(`  📄 Env File: ${envPath}`);
    
    if (fs.existsSync(envPath)) {
        const envContent = fs.readFileSync(envPath, 'utf8');
        console.log('  ✅ .env.local exists');
        console.log('  📋 Contents:');
        envContent.split('\n').forEach(line => {
            if (line.trim()) {
                console.log(`    ${line}`);
            }
        });
    } else {
        console.log('  ❌ .env.local missing');
        console.log('  💡 Creating .env.local with default values');
        
        const defaultEnv = `NEXT_PUBLIC_API_BASE=${API_BASE}\n`;
        fs.writeFileSync(envPath, defaultEnv);
        console.log('  ✅ .env.local created');
    }
}

async function main() {
    const args = process.argv.slice(2);
    const command = args[0];
    
    switch (command) {
        case 'dev':
        case 'serve':
            const devPort = parseInt(args[1]) || 3000;
            await dev(devPort);
            break;
            
        case 'build':
            await build();
            break;
            
        case 'start':
            const startPort = parseInt(args[1]) || 3000;
            await start(startPort);
            break;
            
        case 'lint':
            await lint();
            break;
            
        case 'test':
            await test();
            break;
            
        case 'install':
            await install();
            break;
            
        case 'env':
        case 'check':
            await checkEnv();
            break;
            
        default:
            console.log('🎨 Frontend Development Tools\n');
            console.log('Available commands:');
            console.log('  dev [port]    - Start development server (default: 3000)');
            console.log('  build         - Build for production');
            console.log('  start [port]  - Start production server');
            console.log('  lint          - Run ESLint');
            console.log('  test          - Run tests');
            console.log('  install       - Install dependencies');
            console.log('  env|check     - Check environment configuration');
            console.log('\nExamples:');
            console.log('  node scripts/dev.js dev 3001');
            console.log('  node scripts/dev.js build');
            console.log('  node scripts/dev.js env');
            break;
    }
}

main().catch(error => {
    console.error('❌ Error:', error.message);
    process.exit(1);
});