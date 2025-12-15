/// <reference types="vite/client" />

// Support for importing markdown files as raw strings
declare module '*.md?raw' {
  const content: string;
  export default content;
}
