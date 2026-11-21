// Every user-visible string in the app lives here. UI language: Uzbek (Latin).
export const uz = {
  appName: 'PomidorAI',
  appTagline: "O'simlik salomatligini tekshirish",

  tabScan: 'Tahlil',
  tabHistory: 'Tarix',
  tabAbout: 'Haqida',

  // Scan screen
  scanTitle: "O'simlik rasmini yuboring",
  scanSubtitle: "Bitta barg yoki butun o'simlikning aniq rasmini oling.",
  scanCamera: 'Kameradan olish',
  scanGallery: 'Galereyadan tanlash',
  scanRemove: "O'chirish",
  scanAnalyze: 'Tahlil qilish',
  scanPreviewAlt: "Tanlangan o'simlik rasmi",

  // Loading / errors
  loading: 'Yuklanmoqda...',
  analyzing: 'Tahlil qilinmoqda...',
  analyzingHint: 'Bu bir necha soniya vaqt oladi.',
  retry: 'Qayta urinish',
  errorTitle: 'Xatolik yuz berdi',
  errorAnalysisFailed: "Tahlil qilib bo'lmadi. Qayta urinib ko'ring.",
  errorHistoryFailed: "Tarixni yuklab bo'lmadi.",
  errorDeleteFailed: "O'chirib bo'lmadi.",
  errorNotFound: 'Topilmadi.',
  errorImageType: 'Rasm turi mos emas. JPEG, PNG yoki WebP yuboring.',
  errorImageTooLarge: "Rasm hajmi juda katta. Eng ko'pi 8 MB.",
  errorImageDecode: "Rasmni o'qib bo'lmadi. Boshqa rasm bilan urinib ko'ring.",

  // Offline
  offlineBanner: "Internet yo'q. Tahlil qilish uchun internet kerak.",
  offlineTitle: "Internet aloqasi yo'q",
  offlineMessage:
    "Tahlil qilish uchun internetga ulanish kerak. Ulanganingizdan so'ng qayta urinib ko'ring.",

  // Results
  resultPlantTitle: "O'simlik",
  resultConfidence: 'Ishonch',
  resultUnsure:
    "Ishonchim komil emas. Bitta barg yoki o'simlikning aniqroq rasmini yuboring.",
  resultHealthTitle: 'Salomatligi',
  resultInfoTitle: "O'simlik haqida",
  resultHowItGrows: "Qanday o'sadi",
  resultWater: 'Suv',
  resultSunlight: 'Quyosh',
  resultSoil: 'Tuproq',
  resultSeason: 'Mavsum',
  resultCommonDiseases: 'Keng tarqalgan kasallik va zararkunandalar',
  resultCareTips: 'Parvarish maslahatlari',
  resultNewScan: 'Yangi tahlil',
  disclaimer:
    "Bu vosita faqat dastlabki tekshiruv uchun mo'ljallangan va tashxis hisoblanmaydi. Davolashdan oldin agronom bilan maslahatlashing.",

  // History
  historyTitle: 'Tarix',
  historyEmptyTitle: "Hozircha tahlil yo'q",
  historyEmptyMessage:
    "Birinchi o'simlik rasmini yuborsangiz, natija shu yerda saqlanadi.",
  historyEmptyAction: 'Tahlilni boshlash',
  historyLoadMore: 'Yana yuklash',
  historyClearAll: 'Barchasini tozalash',
  historyThumbAlt: 'Tahlil qilingan rasm',

  // Confirmations
  confirmDeleteTitle: "Bu tahlilni o'chirilsinmi?",
  confirmDeleteMessage: "O'chirilgan tahlilni qaytarib bo'lmaydi.",
  confirmClearTitle: 'Butun tarix tozalansinmi?',
  confirmClearMessage: "Barcha saqlangan tahlillar o'chiriladi va qaytarilmaydi.",
  confirmDelete: "O'chirish",
  confirmCancel: 'Bekor qilish',

  // About
  aboutTitle: 'Qanday ishlaydi',
  aboutStep1Title: '1. Rasm oling',
  aboutStep1Text: "O'simlikning bargini yoki o'zini kameradan suratga oling.",
  aboutStep2Title: '2. Tahlil qiling',
  aboutStep2Text: "Rasm yuboriladi va o'simlik turi hamda salomatligi aniqlanadi.",
  aboutStep3Title: "3. Natijani ko'ring",
  aboutStep3Text:
    "O'simlik nomi, salomatlik holati va parvarish maslahatlarini oling. Natija tarixda saqlanadi.",
  aboutPrivacyTitle: 'Maxfiylik',
  aboutPrivacyText:
    "Hisob ochish shart emas. Tahlillar faqat shu qurilmaga bog'lanadi va rasmdagi joylashuv ma'lumotlari saqlanmaydi.",

  // Shared
  close: 'Yopish',
  back: 'Orqaga',
  healthy: "Sog'lom",
  unknownPlant: "Aniqlanmadi",
  correctPrompt: "Noto'g'rimi?",
  correctAction: "To'g'rilash",
  correctTitle: "Bu qaysi o'simlik?",
  correctCancel: "Bekor qilish",
  correctSaved: "Rahmat! Endi shunga o'xshash rasmni taniydi.",
  errorCorrectFailed: "Saqlab bo'lmadi. Qayta urinib ko'ring.",
  viewLabel: "Rasmda",
  viewHosil: "Hosil",
  viewPlant: "O'simlik",
  viewLeaf: "Barg",
} as const;
