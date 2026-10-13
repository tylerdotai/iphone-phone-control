.PHONY: validate lint typecheck test check

validate:
	python3 tools/validate.py

# AST/syntax compilation only; not static type checking or device execution.
typecheck:
	python3 -c 'import ast; from pathlib import Path; [compile(ast.parse(p.read_text(), filename=str(p)), str(p), "exec") for p in Path("tools").glob("*.py")]; print("Python AST/syntax compilation passed")'

lint: typecheck validate

test:
	python3 tools/verify_e2e.py --output .artifacts/e2e.json

check: lint test
