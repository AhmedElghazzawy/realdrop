import type { Dictionary } from "./en";

export const tr: Dictionary = {
  meta: {
    description: "Moda indirimlerinin gerçeği: gerçek fiyat geçmişi ve gerçek indirimler.",
  },
  nav: { products: "Ürünler", status: "Veri toplama", language: "Dil" },
  footer: "Fiyatlar mağazaların kendi sitelerinden günlük olarak toplanır. Her iddia, gözlemlediğimiz fiyatlara dayanır.",
  home: {
    title: "İndirim gerçek mi?",
    titleAccent: "Fiyat geçmişi söylesin.",
    intro:
      "Her gün mağazaların fiyatlarını kaydediyoruz. 14 günlük geçmiş birikince her ürün için gerçek indirim hesabı açılacak; o zamana kadar mağazanın iddiasını ve gözlemlediğimiz fiyatı yan yana gösteriyoruz.",
    audienceNote: "Erkek giyim gösteriliyor.",
    searchLabel: "Ürün ara",
    searchPlaceholder: "Ürün ara: kaban, jean, gömlek…",
    sortLabel: "Sıralama",
    sorts: {
      recent: "En son görülen",
      claimed_discount: "Mağaza indirimi (iddia)",
      price_asc: "Fiyat: düşükten yükseğe",
      price_desc: "Fiyat: yüksekten düşüğe",
    },
    searchButton: "Ara",
    count: (n: string) => `${n} ürün`,
    noMatch: "Bu aramaya uyan ürün yok.",
    empty: "Henüz ürün toplanmadı. Bir sonraki toplama Türkiye saatiyle 03:00'te.",
    previous: "← Önceki",
    next: "Sonraki →",
    pages: "Sayfalar",
  },
  card: {
    soldOut: "Tükendi",
    sizes: (inStock: number, total: number) => `${inStock}/${total} beden`,
  },
  claim: {
    shopSays: (pct: string) => `mağaza: −${pct}`,
    title: "Mağazanın iddia ettiği indirim",
  },
  // No "'den/'dan beri" suffix: Turkish vowel harmony changes it with every date.
  tracking: (date: string) => `Takip başlangıcı: ${date}`,
  product: {
    back: "← Ürünler",
    lastChecked: (time: string) => `Son kontrol: ${time}`,
    history: "Fiyat geçmişi",
    notEnoughHistory: (days: number) =>
      `Şu ana kadar ${days} günlük veri var. Gerçek indirim hesabı için en az 14 gün gerekiyor; o zamana kadar indirim iddiası yapmıyoruz.`,
    sizes: "Bedenler",
    inStock: "Stokta",
    soldOut: "Tükendi",
    viewAt: (brand: string) => `${brand} sitesinde gör ↗`,
  },
  chart: {
    noData: "Henüz onaylanmış fiyat yok.",
    paid: "Ödenen fiyat (günün en düşüğü)",
    claimed: "Mağazanın \"eski fiyat\" iddiası",
    claimedPoint: (day: string, price: string) => `${day}: mağaza iddiası ${price}`,
    aria: (days: number, last: string) => `Fiyat geçmişi, ${days} gün. Son fiyat ${last}.`,
  },
  status: {
    title: "Veri toplama",
    intro: "Katalog her gün Türkiye saatiyle 03:00 ve 15:00'te ikiye bölünerek toplanır.",
    products: (brand: string) => `${brand} · ürün`,
    variants: "Beden (varyant)",
    observations: "Fiyat gözlemi",
    since: "Takip başlangıcı",
    columns: {
      started: "Başlangıç",
      brand: "Marka",
      status: "Durum",
      products: "Ürün",
      failed: "Hata",
      duration: "Süre",
      notes: "Not",
    },
    noRuns: "Henüz toplama yapılmadı.",
    states: { succeeded: "başarılı", partial: "kısmi", failed: "başarısız", running: "sürüyor" },
    running: "sürüyor",
    minutes: (m: number) => `${m} dk`,
    hours: (h: number, m: number) => `${h} sa ${m} dk`,
  },
  error: {
    title: "Veriye ulaşamadık.",
    body: "API çalışmıyor olabilir. Biraz sonra tekrar deneyin.",
    retry: "Tekrar dene",
  },
};
