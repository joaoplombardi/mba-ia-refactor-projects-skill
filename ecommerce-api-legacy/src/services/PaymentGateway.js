'use strict';

const logger = require('../utils/logger');

/**
 * The external payment system, behind an interface a controller can fake.
 *
 * The legacy code decided approval inline with `cc.startsWith("4")`, logging the
 * full card number and the live gateway key next to it. The rule is preserved
 * here so the documented api.http examples keep behaving the same, but it is now
 * isolated at the boundary: swapping in a real gateway means replacing this class
 * and nothing else.
 */
class PaymentGateway {
    constructor({ apiKey, approvedCardPrefix }) {
        this.apiKey = apiKey;
        this.approvedCardPrefix = approvedCardPrefix;
    }

    async charge({ card, amount }) {
        // Only the last four digits are logged, and never the key.
        logger.info(`Processando pagamento de ${amount} no cartão ${logger.maskCard(card)}`);
        const approved = String(card).startsWith(this.approvedCardPrefix);
        return { status: approved ? 'PAID' : 'DENIED' };
    }
}

/** Test double: approves everything without touching the network. */
class AlwaysApprovedGateway {
    async charge() {
        return { status: 'PAID' };
    }
}

module.exports = { PaymentGateway, AlwaysApprovedGateway };
