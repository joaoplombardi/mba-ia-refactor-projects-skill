'use strict';

/**
 * Application configuration. Every value comes from the environment.
 *
 * The legacy src/utils.js carried a live payment gateway key, a production
 * database password and SMTP credentials as literals. Those are gone; the
 * only defaults here are development-safe placeholders.
 */

function asBool(raw, fallback = false) {
    if (raw === undefined || raw === null || raw === '') return fallback;
    return ['1', 'true', 'yes', 'on'].includes(String(raw).trim().toLowerCase());
}

const config = {
    env: process.env.NODE_ENV || 'development',
    port: Number(process.env.PORT || 3000),
    dbFile: process.env.DB_FILE || ':memory:',
    seedOnBoot: asBool(process.env.SEED_ON_BOOT, true),
    logLevel: process.env.LOG_LEVEL || 'info',
    // Destructive admin operations are disabled unless this is set (finding F11).
    adminApiToken: process.env.ADMIN_API_TOKEN || '',
    payment: {
        // 'simulated' charges nothing; 'live' requires a real provider integration.
        // Production gets no default — it must be stated explicitly.
        mode: process.env.PAYMENT_MODE || '',
        // No default: a missing key must fail loudly rather than ship a fake one.
        gatewayKey: process.env.PAYMENT_GATEWAY_KEY || '',
        // Preserves the legacy approval rule so the api.http examples keep working.
        approvedCardPrefix: process.env.APPROVED_CARD_PREFIX || '4',
    },
};

config.isProduction = config.env === 'production';

// Outside production the gateway defaults to the simulator, so the documented
// api.http examples keep working with no setup.
if (!config.payment.mode && !config.isProduction) {
    config.payment.mode = 'simulated';
}

function validate() {
    // Fail closed at boot: a simulated gateway must never reach production.
    if (config.isProduction && config.payment.mode !== 'live') {
        throw new Error(
            'PAYMENT_MODE must be "live" in production — refusing to boot with a '
                + 'simulated payment gateway (audit finding F05)',
        );
    }
    if (config.isProduction && !config.payment.gatewayKey) {
        throw new Error('PAYMENT_GATEWAY_KEY must be set in production');
    }
}

module.exports = { config, validate };
