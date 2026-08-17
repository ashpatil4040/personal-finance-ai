export const currency = (n: number) =>
  n.toLocaleString("en-US", { style: "currency", currency: "USD" });

export const currencyShort = (n: number) => `$${Math.round(n).toLocaleString("en-US")}`;

export const formatDate = (iso: string) =>
  new Date(iso + "T00:00:00").toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
