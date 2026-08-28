'use strict';

const logger = require('../utils/logger');

/**
 * SIMULATED payment gateway — it makes no network call and charges nothing.
 *
 * Approval is decided locally from the card prefix, which is the legacy rule
 * (audit finding F05). A refactor cannot conjure a real payment provider, so the
 * finding is *mitigated*, not fixed: the dangerous decision is isolated at the
 * boundary, named for what it is, announced at boot and on every call, marks its
 * own results with `simulated: true`, and the composition root refuses to boot
 * with it in production.
 *
 * Residual risk: in development and staging, anyone who sends a card number
 * starting with the approved prefix is enrolled without paying. Closing it
 * requires integrating a real provider behind this same interface.
 */
class SimulatedPaymentGateway {
    constructor({ approvedCardPrefix }) {
        this.approvedCardPrefix = approvedCardPrefix;
        logger.warn(
            'SimulatedPaymentGateway ativo: nenhuma cobrança real é processada. '
                + 'Não utilize em produção.',
        );
    }

    async charge({ card, amount }) {
        // Only the last four digits are logged, and never a gateway key.
        logger.warn(
            `[SIMULADO] Aprovação decidida localmente para ${logger.maskCard(card)} `
                + `(valor ${amount})`,
        );
        const approved = String(card).startsWith(this.approvedCardPrefix);
        return { status: approved ? 'PAID' : 'DENIED', simulated: true };
    }
}

/** Test double: approves everything without touching the network. */
class AlwaysApprovedGateway {
    async charge() {
        return { status: 'PAID', simulated: true };
    }
}

module.exports = { SimulatedPaymentGateway, AlwaysApprovedGateway };
