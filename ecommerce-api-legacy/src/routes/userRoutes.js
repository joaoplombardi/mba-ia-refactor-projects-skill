'use strict';

const express = require('express');

const requireAdminToken = require('../middlewares/requireAdminToken');

module.exports = function userRoutes(controller) {
    const router = express.Router();

    // Destructive verb: gated rather than removed, because deleting a user is a
    // legitimate REST operation. See audit finding F11.
    router.delete('/api/users/:id', requireAdminToken, (req, res, next) => {
        controller
            .deleteUser(req.params.id)
            .then((message) => res.status(200).send(message))
            .catch(next);
    });

    return router;
};
