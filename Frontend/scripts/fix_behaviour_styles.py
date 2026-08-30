import re
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "src" / "BehaviourAnalyst.jsx"
text = path.read_text(encoding="utf-8")

if "function bindElStyle" not in text:
    text = text.replace(
        'import { authFetch } from "./services/authApi";',
        'import { authFetch } from "./services/authApi";\n'
        'import "./BehaviourAnalyst.css";\n\n'
        "function bindElStyle(el, style) {\n"
        "  if (el && style) Object.assign(el.style, style);\n"
        "}\n",
    )

text = re.sub(
    r" style=\{\{([^}]+)\}\}",
    lambda m: f" ref={{(el) => bindElStyle(el, {{{m.group(1)}}})}}",
    text,
)
path.write_text(text, encoding="utf-8")
print("remaining style={{", text.count(" style={{"))
print("bindElStyle count", text.count("bindElStyle"))
