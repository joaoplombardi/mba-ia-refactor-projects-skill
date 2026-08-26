'use strict';

const { config } = require('../config');

const LEVELS = { error: 0, warn: 1, info: 2, debug: 3 };
const threshold = LEVELS[config.logLevel] ?? LEVELS.info;

function emit(level, message, meta) {
    if (LEVELS[level] > threshold) return;
    const line = `${new Date().toISOString()} ${level.toUpperCase().padEnd(5)} ${message}`;
    const target = level === 'error' ? console.error : console.log;
    meta === undefined ? target(line) : target(line, meta);
}

/**
 * Never log a full card number or a gateway key. The legacy code logged both.
 */
function maskCard(card) {
    const digits = String(card || '').replace(/\D/g, '');
    return digits.length <= 4 ? '****' : `****${digits.slice(-4)}`;
}

module.exports = {
    error: (msg, meta) => emit('error', msg, meta),
    warn: (msg, meta) => emit('warn', msg, meta),
    info: (msg, meta) => emit('info', msg, meta),
    debug: (msg, meta) => emit('debug', msg, meta),
    maskCard,
};
