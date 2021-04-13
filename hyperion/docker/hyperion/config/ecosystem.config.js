const {addApiServer, addIndexer} = require("./definitions/ecosystem_settings");

module.exports = {
    apps: [
        addIndexer('telos-testnet'),
        addApiServer('telos-testnet', 1)
    ]
};
