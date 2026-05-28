import hashlib


class IwownClient:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger

    def call_device_api(self, method, path, json_body=None, params=None):
        return self.request(
            method=method,
            base_url=self.config["IWOWN_API_HOST"],
            path=path,
            json_body=json_body,
            params=params,
        )

    def call_algorithm_api(self, method, path, json_body=None, params=None):
        return self.request(
            method=method,
            base_url=self.config["IWOWN_ALGO_HOST"],
            path=path,
            json_body=json_body,
            params=params,
        )

    def request(self, method, base_url, path, json_body=None, params=None):
        try:
            import requests
        except Exception as exc:
            return {
                "ok": False,
                "status_code": 500,
                "body": {"ReturnCode": 10505, "message": f"requests unavailable: {exc}"},
            }

        url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
        headers = self.auth_headers()
        try:
            response = requests.request(
                method,
                url,
                json=json_body if method.upper() != "GET" else None,
                params=params,
                headers=headers,
                timeout=self.config["REQUEST_TIMEOUT_SECONDS"],
            )
            try:
                body = response.json()
            except ValueError:
                body = {"raw": response.text}
            return {"ok": response.ok, "status_code": response.status_code, "body": body}
        except Exception as exc:
            self.logger.exception("iwown request failed: %s %s", method, url)
            return {
                "ok": False,
                "status_code": 502,
                "body": {"ReturnCode": 10505, "message": str(exc)},
            }

    def auth_headers(self):
        account = self.config.get("IWOWN_API_ACCOUNT", "")
        password = self.config.get("IWOWN_API_PASSWORD", "")
        if not account or not password:
            return {}
        pwd = password if is_md5(password) else hashlib.md5(password.encode("utf-8")).hexdigest()
        return {"account": account, "pwd": pwd}


def is_md5(value):
    if len(value) != 32:
        return False
    try:
        int(value, 16)
        return True
    except ValueError:
        return False
