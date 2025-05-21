import ixbrl_parser
import os
import inspect

print("🔍 Testing ixbrl_parser module...")

# Check if it's actually a module and not None
if ixbrl_parser is None:
    print("❌ ixbrl_parser is None!")
else:
    print(f"✅ ixbrl_parser module loaded from: {os.path.abspath(ixbrl_parser.__file__)}")

# Confirm the function is present and callable
func = getattr(ixbrl_parser, "parse_ixbrl_and_extract", None)
print("🔍 Function check: ", type(func), repr(func))

if callable(func):
    print("✅ parse_ixbrl_and_extract IS callable!")
    print("🔍 Defined at:", inspect.getsourcefile(func))
else:
    print("❌ parse_ixbrl_and_extract is NOT callable or missing.")
