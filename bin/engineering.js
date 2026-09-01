#!/usr/bin/env node
const { spawn } = require('node:child_process');
const target = '/home/ubuntu/engineering-intelligence/bin/engineering.js';
const args = process.argv.slice(2);
const child = spawn('node', [target, ...args], { stdio: 'inherit' });
child.on('exit', c => process.exit(c ?? 0));
