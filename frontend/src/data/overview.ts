export const activities = [
  {
    title: 'Ny leverans registrerad',
    description: 'Lager A · Sektion 3',
    time: '2 min sedan',
    color: 'blue',
    icon: '◇',
  },
  {
    title: 'Lågt lagersaldo',
    description: 'Produkt #4821 · Lager B',
    time: '18 min sedan',
    color: 'amber',
    icon: '△',
  },
  {
    title: 'Inventering slutförd',
    description: 'Lager C · Alla sektioner',
    time: '1 tim sedan',
    color: 'green',
    icon: '✓',
  },
  {
    title: 'Rapport genererad',
    description: 'Månadsrapport · Oktober',
    time: '3 tim sedan',
    color: 'purple',
    icon: '▤',
  },
]

export const overviewStatistics = [
  { label: 'TOTALT LAGER', value: '1,284', unit: 'enheter', change: '+12' },
  { label: 'LEVERERAS', value: '47', unit: 'enheter', change: '+3' },
  { label: 'SKADAT', value: '—', unit: 'enheter', change: '' },
]

export const warehouseCapacities = [
  { name: 'Lager A', percentage: '78%', color: 'black' },
  { name: 'Lager B', percentage: '61%', color: 'blue' },
  { name: 'Lager C', percentage: '43%', color: 'green' },
]
