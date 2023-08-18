import importlib
from pathlib import Path
import time

from flask import request, jsonify

from tevmc.cmdline.build import build_service
from tevmc.testing.database import ElasticDataIntegrityError, ElasticDriver


def add_routes(tevmc: 'TEVMController'):

    app = tevmc.api

    @app.route('/status', methods=['GET'])
    def status():
        result = {'services': {}}
        for cont_name, cont in tevmc.containers.items():
            cont.reload()
            result['services'][cont_name] = {
                'status': cont.status
            }

        return jsonify(result)

    @app.route('/restart', methods=['POST'])
    def restart():
        service = request.json.get('service', None)
        must_update = request.json.get('update', False)
        if service is None:
            tevmc.logger.info('tevmc restart requested, stopping...')
            tevmc.stop()
            tevmc.logger.info('tevmc stopped. going up in 3 seconds...')
            time.sleep(3)
            tevmc.start()

        elif service == 'nodeos':
            build_service(
                Path('.'), 'nodeos', tevmc.config, nocache=must_update)
            tevmc.restart_nodeos()

        elif service == 'indexer':
            build_service(
                Path('.'), 'indexer', tevmc.config, nocache=must_update)
            tevmc.restart_translator()

        elif service == 'rpc':
            build_service(
                Path('.'), 'rpc', tevmc.config, nocache=must_update)
            tevmc.restart_rpc()

        return jsonify(success=True), 200


    @app.route('/patch', methods=['POST'])
    def patch():
        pf_path = request.json.get('path', None)

        if not pf_path:
            return jsonify(error='path parameter is required'), 400

        pf_path = Path(pf_path).resolve()

        if not pf_path.is_file():
            return jsonify(error='patch file not found'), 400

        spec = importlib.util.spec_from_file_location(
            'module_name', pf_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        try:
            patch_fn = getattr(module, 'tevmc_apply_patch')
            ret = patch_fn(tevmc)

            return jsonify(ret), 200

        except AttributeError:
            return jsonify(error='patch function not found'), 400

    @app.route('/check', methods=['GET'])
    def check():
        try:
            ElasticDriver(tevmc.config).full_integrity_check()
            status = 'healthy'

        except ElasticDataIntegrityError as e:
            status = f'unhealthy: {e}'

        return jsonify({'status': status})
