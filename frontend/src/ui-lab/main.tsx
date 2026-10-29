if (import.meta.env.DEV) {
  void import("./mount");
} else {
  throw new Error("The UI laboratory is available only in Vite development.");
}
