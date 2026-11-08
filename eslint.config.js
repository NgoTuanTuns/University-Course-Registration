import tseslint from "typescript-eslint";
export default tseslint.config(
  {
    ignores: [
      "dist/**",
      "public/**",
      "backend/**",
      "ban_giao/**",
      "chitietcongviec/**",
      "docker/**",
      "docs/**",
      "nginx/**",
      "M1_Frontend Web Developer/**",
      "node_modules/**",
      ".venv/**",
    ],
  },
  ...tseslint.configs.recommended,
);
