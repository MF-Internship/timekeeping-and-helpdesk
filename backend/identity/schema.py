from drf_spectacular.extensions import OpenApiAuthenticationExtension


class DatabaseBackedJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "identity.adapters.security.authentication.DatabaseBackedJWTAuthentication"
    name = "bearerAuth"

    def get_security_definition(self, auto_schema: object) -> dict[str, str]:
        return {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
