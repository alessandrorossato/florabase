/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_MOBILE_ALLOW_DEBUG_HTTP?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
