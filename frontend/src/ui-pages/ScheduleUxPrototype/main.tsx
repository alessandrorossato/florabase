if (import.meta.env.DEV) {
  void import("./mount");
} else {
  throw new Error(
    "The Activity prototype is available only in Vite development.",
  );
}
