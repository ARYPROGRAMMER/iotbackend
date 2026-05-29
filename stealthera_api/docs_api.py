from pathlib import Path

from flask import Blueprint, current_app, render_template_string, send_from_directory, url_for


docs_bp = Blueprint("api_docs", __name__)


def openapi_path():
    return Path(current_app.config["BASE_DIR"]) / "docs" / "openapi.json"


@docs_bp.get("/openapi.json")
def openapi_json():
    path = openapi_path()
    return send_from_directory(path.parent, path.name, mimetype="application/json")


@docs_bp.get("/docs")
@docs_bp.get("/swagger")
def swagger_ui():
    spec_url = url_for("api_docs.openapi_json")
    return render_template_string(
        """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Stealthera API Swagger</title>
    <style>
      html, body { margin: 0; height: 100%; background: #0f172a; color: #e2e8f0; font-family: Arial, sans-serif; }
      header { padding: 16px 20px; border-bottom: 1px solid rgba(148, 163, 184, 0.24); }
      main { height: calc(100% - 57px); }
      .fallback { padding: 20px; line-height: 1.6; }
      a { color: #7dd3fc; }
    </style>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
  </head>
  <body>
    <header>Stealthera API Swagger</header>
    <main>
      <div id="swagger-ui" class="fallback">Loading Swagger UI...</div>
    </main>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
      window.onload = function () {
        window.ui = SwaggerUIBundle({
          url: {{ spec_url|tojson }},
          dom_id: '#swagger-ui',
          deepLinking: true,
          presets: [SwaggerUIBundle.presets.apis],
          layout: 'BaseLayout'
        });
      };
    </script>
  </body>
</html>
        """
    )