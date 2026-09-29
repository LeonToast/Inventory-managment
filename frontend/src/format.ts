const dateFormat = new Intl.DateTimeFormat('sv-SE', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
})

// "29 sep 2026": the period Swedish puts after the month is dropped.
export const formatDate = (value: string | Date) =>
  dateFormat.format(new Date(value)).replace('.', '')
