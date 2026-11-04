// Copy to the front-end package as `eslint.config.js` (flat config, ESLint 9+).
// Adjust the generated bindings path and the backend folder if they differ.
import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import tseslint from "typescript-eslint";

export default tseslint.config(
  // Build output, generated bindings and the backend's folder.
  { ignores: ["dist", "src/bindings", "src-tauri"] },
  js.configs.recommended,
  tseslint.configs.strictTypeChecked,
  reactHooks.configs.flat.recommended,
  {
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },
  {
    rules: {
      // React event-handler props (`onClick={save}`) routinely take an async
      // function whose rejection is surfaced through component state; only the
      // "attributes" check is off, conditionals, arguments and spreads stay on.
      "@typescript-eslint/no-misused-promises": [
        "error",
        { checksVoidReturn: { attributes: false } },
      ],
      // `${count} items` is the common case and String(count) catches nothing;
      // objects, nullish values and `any` are still reported.
      "@typescript-eslint/restrict-template-expressions": [
        "error",
        { allowNumber: true },
      ],
      // `onClick={() => setOpen(false)}` is the React idiom; a void call
      // anywhere else (a `return`, a `&&` chain) is still reported.
      "@typescript-eslint/no-confusing-void-expression": [
        "error",
        { ignoreArrowShorthand: true },
      ],
      // `_name` marks a deliberately unused binding (rest-sibling omission,
      // positional argument).
      "@typescript-eslint/no-unused-vars": [
        "error",
        {
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
          ignoreRestSiblings: true,
        },
      ],
    },
  },
  {
    // The IPC layer rejects with the backend's typed error (architecture D4),
    // a plain serialised object the callers switch on; wrapping it in an Error
    // would hide that discriminant. Everywhere else, reject with an Error.
    files: ["src/ipc/**"],
    rules: { "@typescript-eslint/prefer-promise-reject-errors": "off" },
  },
  {
    // Test doubles are `async` on purpose, to mimic the promise-returning API
    // they replace, mocks hand back untyped JSON (`mock.calls[0]`), and a
    // `result[0]!` that turns out undefined fails the test, which is the point.
    files: ["**/*.test.{ts,tsx}"],
    rules: {
      "@typescript-eslint/require-await": "off",
      "@typescript-eslint/no-unsafe-assignment": "off",
      "@typescript-eslint/no-unsafe-member-access": "off",
      "@typescript-eslint/no-unsafe-argument": "off",
      "@typescript-eslint/no-unsafe-return": "off",
      "@typescript-eslint/no-non-null-assertion": "off",
    },
  },
  // Config files and scripts in plain JS are linted without type information.
  { files: ["**/*.js"], extends: [tseslint.configs.disableTypeChecked] },
  {
    // Only ipc/ may reach the generated bindings (react-conventions.md §2).
    files: ["src/**/*.{ts,tsx}"],
    ignores: ["src/ipc/**"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              regex: "(^|/)bindings(/|$)",
              message: "Import from src/ipc/, never from the generated bindings.",
            },
          ],
        },
      ],
    },
  },
  // An app with no generated bindings replaces the block above with this one,
  // so invoke() itself stays confined to the IPC module:
  //
  // {
  //   files: ["src/**/*.{ts,tsx}"],
  //   ignores: ["src/ipc/**"],
  //   rules: {
  //     "no-restricted-imports": ["error", {
  //       paths: [{
  //         name: "@tauri-apps/api/core",
  //         importNames: ["invoke"],
  //         message: "Call the backend through src/ipc/.",
  //       }],
  //     }],
  //   },
  // },
);
