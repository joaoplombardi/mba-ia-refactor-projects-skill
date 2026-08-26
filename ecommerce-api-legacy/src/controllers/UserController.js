'use strict';

const { NotFoundError } = require('../errors/AppError');
const logger = require('../utils/logger');

class UserController {
    constructor({ db, userModel, enrollmentModel, paymentModel }) {
        this.db = db;
        this.userModel = userModel;
        this.enrollmentModel = enrollmentModel;
        this.paymentModel = paymentModel;
    }

    /**
     * Removes the user and every row that depends on them, in one transaction.
     *
     * The legacy handler deleted only the user row, ignored the driver error and
     * always answered 200 — its own response text admitted that enrolments and
     * payments were left behind, which corrupted the financial report.
     */
    async deleteUser(id) {
        return this.db.transaction(async (tx) => {
            const user = await this.userModel.findById(id, tx);
            if (!user) {
                throw new NotFoundError('Usuário não encontrado');
            }

            await this.paymentModel.deleteByUserId(id, tx);
            await this.enrollmentModel.deleteByUserId(id, tx);
            await this.userModel.deleteById(id, tx);

            logger.info(`Usuário ${id} removido com matrículas e pagamentos associados`);
            return 'Usuário deletado, junto com suas matrículas e pagamentos.';
        });
    }
}

module.exports = UserController;
