export function createHydrationGate() {
  let generation = 0;
  let hydrating = true;

  return {
    begin() {
      generation += 1;
      hydrating = true;
      return generation;
    },
    isCurrent(token) {
      return token === generation;
    },
    release(token) {
      if (token !== generation) return false;
      hydrating = false;
      return true;
    },
    cancel() {
      generation += 1;
      hydrating = true;
    },
    isHydrating() {
      return hydrating;
    },
  };
}
