from time import perf_counter

from flask import g, jsonify, request
from werkzeug.exceptions import HTTPException, MethodNotAllowed, NotFound


def register_request_logging(app):
    @app.before_request
    def log_request_start():
        g.request_started_at = perf_counter()
        app.logger.info(
            "request started method=%s path=%s endpoint=%s remote_addr=%s content_type=%s query=%s",
            request.method,
            request.path,
            request.endpoint or "-",
            request.headers.get("X-Forwarded-For", request.remote_addr),
            request.content_type or "-",
            request.query_string.decode("utf-8", errors="ignore") or "-",
        )

    @app.after_request
    def log_request_end(response):
        started_at = getattr(g, "request_started_at", None)
        duration_ms = (perf_counter() - started_at) * 1000 if started_at is not None else 0.0
        app.logger.info(
            "request finished method=%s path=%s status=%s duration_ms=%.2f",
            request.method,
            request.path,
            response.status_code,
            duration_ms,
        )
        return response

    @app.errorhandler(NotFound)
    def handle_not_found(error):
        app.logger.warning(
            "request not found method=%s path=%s remote_addr=%s query=%s",
            request.method,
            request.path,
            request.headers.get("X-Forwarded-For", request.remote_addr),
            request.query_string.decode("utf-8", errors="ignore") or "-",
        )
        return jsonify({"ReturnCode": 10404, "message": "route not found"}), 404

    @app.errorhandler(MethodNotAllowed)
    def handle_method_not_allowed(error):
        app.logger.warning(
            "method not allowed method=%s path=%s allowed=%s",
            request.method,
            request.path,
            ",".join(sorted(error.valid_methods or [])),
        )
        return jsonify({"ReturnCode": 10002, "message": "method not allowed"}), 405

    @app.errorhandler(Exception)
    def handle_unexpected_exception(error):
        if isinstance(error, HTTPException):
            return error
        app.logger.exception("unhandled exception method=%s path=%s", request.method, request.path)
        return jsonify({"ReturnCode": 10505, "message": "internal server error"}), 500