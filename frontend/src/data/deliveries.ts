export const deliveryStatistics = [
  { label: 'TOTALT', value: '6', unit: 'leveranser', badge: '+5', tone: 'green' },
  { label: 'PÅ VÄG', value: '1', unit: 'leveranser', badge: 'Aktiv', tone: 'green' },
  { label: 'MOTTAGNA', value: '3', unit: 'leveranser', badge: 'Klart', tone: 'green' },
  { label: 'AVVIKELSER', value: '1', unit: 'att följa upp', badge: 'Åtgärd', tone: 'amber' },
]

export const deliveries = [
  {
    supplier: 'Nordic Supply AB',
    id: 'LEV-24018',
    warehouse: 'Lager A',
    content: 'Kabeltrumma 25m · 24 st',
    date: 'Idag, 11:30',
    status: 'På väg',
    tone: 'blue',
  },
  {
    supplier: 'Pack & Frakt Sverige',
    id: 'LEV-24017',
    warehouse: 'Lager C',
    content: 'Fraktsedlar · 820 st',
    date: 'Idag, 09:45',
    status: 'Mottagen',
    tone: 'green',
  },
  {
    supplier: 'ScanTech Nordic',
    id: 'LEV-24016',
    warehouse: 'Lager B',
    content: 'Streckkodsläsare · 18 st',
    date: 'Igår, 15:20',
    status: 'Avvikelse',
    tone: 'amber',
  },
  {
    supplier: 'Industripartner',
    id: 'LEV-24015',
    warehouse: 'Lager A',
    content: 'Pallställ · 6 st',
    date: 'Igår, 13:10',
    status: 'Planerad',
    tone: 'gray',
  },
  {
    supplier: 'Skydd & Arbete AB',
    id: 'LEV-24014',
    warehouse: 'Lager B',
    content: 'Skyddshandskar · 248 par',
    date: '12 okt, 10:00',
    status: 'Mottagen',
    tone: 'green',
  },
]
