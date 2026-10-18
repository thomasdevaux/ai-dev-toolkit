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
);
