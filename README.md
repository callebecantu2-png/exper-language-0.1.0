# exper-language-0.1.0
My own language

# ⚙️ Exper Language

Exper is a custom programming language built from scratch in Python.  
It was created as a learning project to understand how interpreters, parsers, and programming languages work internally.

---

## 🚀 Features

Exper currently supports:

- Variables
- Functions (with parameters, default values, and named arguments)
- Conditionals (if / elif / else)
- Loops (while / for, including for-in)
- Return, break, continue
- String interpolation using `{expression}`
- Lists (append, pop, remove, insert)
- Built-in functions:
  - console.log
  - console.input
  - console.clear
  - sleep
  - int, float, str
  - any, all
- Expression evaluation system
- Function calls inside expressions
- Basic scope simulation

---

## 💻 Example

```exper
fn soma(a, b=10) {
    return a + b
}

console.log(soma(5))
console.log(soma(5, 20))
console.log(soma(a=7, b=3))

nome = "Callebe"
idade = 12

if (idade > 17) {
    console.log("{nome} is an adult.")
} else {
    console.log("{nome} is not an adult.")
}
```
⚙️ How it works

Exper is interpreted using a Python engine that:

Reads code line by line
Evaluates expressions dynamically
Simulates function scopes
Handles control flow using exceptions (break/continue/return)
Supports nested function calls inside expressions


🧠 Project goals

This project is evolving into a full programming language.
Current and future goals include:

Better parser (reduce dependency on eval)
Real lexical scope system
Improved error messages
Operators (+=, -=, ++, XOR, etc.)
Structs / objects / macros
Module system
File handling support
Standard library expansion


⚠️ Known limitations

Expression evaluation still partially relies on Python eval
Scope system is simulated, not fully isolated
Error handling is still basic
Some edge cases in parsing need improvement


📦 Running

python exper.py file.exper


🤝 Contributing

This project is open to improvements and suggestions.
Feel free to open issues or submit ideas for language design.


🔥 Author

Created as a learning project to explore how programming languages work internally.

## VS Code Extension

A syntax highlighting extension is included in `/vscode-extension`.

To install manually:
1. Open VS Code
2. Go to Extensions
3. Click "Install from VSIX"
4. Select the package (after building)
