"""Build the native-query contract from a downloaded public OpenAPI document."""

import argparse
import json
from pathlib import Path


def build_contract(spec):
    def schema(value):
        if isinstance(value, list):
            return [schema(item) for item in value]
        if not isinstance(value, dict):
            return value
        if "$ref" in value:
            resolved = spec
            for part in value["$ref"].removeprefix("#/").split("/"):
                resolved = resolved[part]
            return schema(resolved)
        return {
            key: schema(item)
            for key, item in value.items()
            if key not in {"description", "title", "example", "examples", "default"}
        }

    operations = {}
    for path, methods in spec["paths"].items():
        for method, operation in methods.items():
            if method in {"put", "patch", "delete", "head", "options", "trace"}:
                raise ValueError(f"Unsupported API method: {method} {path}")
            if method not in {"get", "post"}:
                continue
            if operation["operationId"] in operations:
                raise ValueError("Duplicate OpenAPI operationId")
            parameters = [
                p for p in operation.get("parameters", []) if not p.get("deprecated")
            ]
            body = operation.get("requestBody", {}).get("content", {})
            body_schema = schema(body.get("application/json", {}).get("schema", {}))
            properties = {p["name"]: schema(p["schema"]) for p in parameters}
            properties.update(body_schema.get("properties", {}))
            operations[operation["operationId"]] = {
                "method": method.upper(),
                "path": path,
                "authenticated": bool(operation.get("security", spec.get("security"))),
                "path_parameters": [p["name"] for p in parameters if p["in"] == "path"],
                "query_parameters": [
                    p["name"] for p in parameters if p["in"] == "query"
                ],
                "body_parameters": list(body_schema.get("properties", {})),
                "schema": {
                    "type": "object",
                    "properties": properties,
                    "required": [p["name"] for p in parameters if p.get("required")]
                    + body_schema.get("required", []),
                    "additionalProperties": False,
                },
            }
    return {"api_version": spec["info"]["version"], "operations": operations}


def render(contract):
    # One line per operation keeps this generated routing data easy to diff.
    entries = [
        "    " + json.dumps(name) + ": " + json.dumps(operation, ensure_ascii=True)
        for name, operation in sorted(contract["operations"].items())
    ]
    return (
        '{\n  "api_version": '
        + json.dumps(contract["api_version"])
        + ',\n  "operations": {\n'
        + ",\n".join(entries)
        + "\n  }\n}\n"
    )


def render_reference(contract):
    lines = [
        "# Native Operations",
        "",
        f"Generated from Adanos OpenAPI {contract['api_version']}. Do not edit.",
        "",
        "Call these names inside `SELECT * FROM adanos (...)`.",
        "`*` means required. `from_date`/`to_date` map to API `from`/`to`.",
        "See [README](README.md) for examples, responses and plan restrictions.",
        "",
        "| Operation | Method and path | Arguments |",
        "| --- | --- | --- |",
    ]
    for name, operation in sorted(contract["operations"].items()):
        required = operation["schema"]["required"]
        arguments = [
            "`"
            + {"from": "from_date", "to": "to_date"}.get(key, key)
            + "`"
            + ("*" if key in required else "")
            for key in operation["schema"]["properties"]
        ]
        lines.append(
            f"| `{name}` | `{operation['method']} {operation['path']}` | "
            + ", ".join(arguments)
            + " |"
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "spec", type=Path, help="Downloaded api.adanos.org/openapi.json"
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    contract = build_contract(json.loads(args.spec.read_text()))
    for filename, content in {
        "operations.json": render(contract),
        "operations.md": render_reference(contract),
    }.items():
        target = Path(__file__).with_name(filename)
        if args.check:
            if target.read_text() != content:
                raise SystemExit(f"{filename} is out of date")
        else:
            target.write_text(content)
    if args.check:
        print("Adanos operation contract matches OpenAPI")
