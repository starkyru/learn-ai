/**
 * Jest config for the course's TypeScript exercises.
 *
 * We use @swc/jest to transpile TS (fast, handles ESM-style `.js` import
 * specifiers). Type-checking is a separate step (`pnpm typecheck`) — jest only
 * runs the code. Tests target pure exercise logic (tokenizer, cosine, etc.),
 * which is exactly what you want unit tests for.
 */
export default {
  testEnvironment: "node",
  roots: ["<rootDir>/modules", "<rootDir>/packages"],
  testMatch: ["**/*.test.ts"],
  transform: {
    "^.+\\.tsx?$": ["@swc/jest"],
  },
  // Source files use ESM-style `./x.js` specifiers; strip the extension so
  // jest's resolver finds the .ts file.
  moduleNameMapper: {
    "^(\\.{1,2}/.*)\\.js$": "$1",
  },
};
