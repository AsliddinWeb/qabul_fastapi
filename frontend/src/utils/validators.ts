/**
 * Centralized field validators. Each returns an error message (string)
 * if invalid, or `null` if valid.
 *
 * Use them in forms for both real-time and submit-time validation.
 */

// ---------- Patterns ----------
export const PATTERNS = {
  phoneUz: /^\+?998\d{9}$/,            // +998 + 9 digits
  passport: /^[A-Z]{2}\d{7}$/,         // AA1234567
  pinfl: /^\d{14}$/,                    // 14 digits
  year: /^\d{4}$/,                      // 4 digits
  email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
} as const

// ---------- Placeholders ----------
export const PLACEHOLDERS = {
  phoneUz: '+998 XX XXX XX XX',
  // Local-only placeholder used by inputs that render `+998` as a fixed
  // sticker on the left rather than baking it into the value.
  phoneUzLocal: 'XX XXX XX XX',
  passport: 'AA1234567',
  pinfl: '12345678901234 (14 raqam)',
  year: '2024',
  email: 'name@example.com',
  uuid: 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
  searchApplicant: "F.I.Sh., PINFL, telefon...",
  searchProgram: "Yo'nalish nomi yoki kodi...",
} as const

// ---------- Validators (return error string or null) ----------
export function required(value: unknown, label = 'Maydon'): string | null {
  if (value === null || value === undefined) return `${label} majburiy`
  if (typeof value === 'string' && !value.trim()) return `${label} majburiy`
  return null
}

export function minLength(value: string, n: number, label = 'Maydon'): string | null {
  if (value.trim().length < n) return `${label} kamida ${n} ta belgi bo'lishi kerak`
  return null
}

export function phoneUz(value: string): string | null {
  if (!value) return 'Telefon raqamni kiriting'
  const digits = value.replace(/\D/g, '')
  if (!/^998\d{9}$/.test(digits)) {
    return "Telefon: +998 XX XXX XX XX (12 raqam)"
  }
  return null
}

export function passport(value: string): string | null {
  if (!value) return null  // optional
  if (!PATTERNS.passport.test(value.toUpperCase())) {
    return 'Pasport seriyasi: 2 lotin harf + 7 raqam (AA1234567)'
  }
  return null
}

export function pinfl(value: string): string | null {
  if (!value) return null  // optional
  if (!PATTERNS.pinfl.test(value)) {
    return 'PINFL aniq 14 ta raqamdan iborat bo\'lishi kerak'
  }
  return null
}

export function year(value: string): string | null {
  if (!value) return 'Yilni kiriting'
  if (!PATTERNS.year.test(value)) return '4 raqamli yil kiriting (masalan: 2024)'
  const y = parseInt(value, 10)
  const now = new Date().getFullYear()
  if (y < 1950 || y > now + 1) return `Yil 1950 – ${now + 1} oraliqda bo'lishi kerak`
  return null
}

export function email(value: string): string | null {
  if (!value) return null  // optional
  if (!PATTERNS.email.test(value)) return 'Email formati noto\'g\'ri'
  return null
}

export function password(value: string, min = 8): string | null {
  if (!value) return 'Parol kiriting'
  if (value.length < min) return `Parol kamida ${min} ta belgi`
  return null
}

// ---------- Auto-format helpers (for @input handlers) ----------
/**
 * Formats Uzbek phone numbers as the user types into "+998 94 202 55 11" shape.
 * Stripping any non-digit input first, then inserting spaces at the standard
 * Uzbek mobile-number boundaries (3 / 2 / 3 / 2 / 2).
 */
export function formatPhone(value: string): string {
  // Strip everything except digits.
  const digits = value.replace(/\D/g, '')
  if (!digits) return ''
  // Force +998 prefix; if the user types a 9-digit local number, prepend it.
  let normalized = digits
  if (!normalized.startsWith('998')) {
    if (normalized.length === 9) {
      normalized = '998' + normalized
    } else {
      normalized = '998' + normalized.replace(/^998/, '')
    }
  }
  // Cap at 12 digits (998 + 9 mobile digits).
  normalized = normalized.slice(0, 12)

  // Slice into groups: +998 XX XXX XX XX
  const cc = normalized.slice(0, 3)               // 998
  const op = normalized.slice(3, 5)               // 94
  const a  = normalized.slice(5, 8)               // 202
  const b  = normalized.slice(8, 10)              // 55
  const c  = normalized.slice(10, 12)             // 11

  let out = '+' + cc
  if (op) out += ' ' + op
  if (a)  out += ' ' + a
  if (b)  out += ' ' + b
  if (c)  out += ' ' + c
  return out
}

/**
 * Strip the formatting back to a plain "+998901234567" shape — used right before
 * sending the value to the backend (where canonical compact form is preferred).
 */
export function compactPhone(value: string): string {
  const digits = value.replace(/\D/g, '')
  if (!digits) return ''
  return '+' + digits
}

/**
 * Format ONLY the 9-digit local part of an Uzbek mobile number as
 * "94 202 55 11". Used by login forms that render the "+998" country code
 * as a fixed sticker outside the input so the user only types the local
 * digits. Strips anything that isn't a digit, drops a leading 998 if the
 * user paste-includes it, and caps at 9 digits.
 */
export function formatPhoneLocal(value: string): string {
  let digits = value.replace(/\D/g, '')
  // If they pasted the full number, strip 998 / 8 prefixes so what stays
  // is the 9-digit local body.
  if (digits.startsWith('998')) digits = digits.slice(3)
  digits = digits.slice(0, 9)
  if (!digits) return ''
  const op = digits.slice(0, 2)
  const a  = digits.slice(2, 5)
  const b  = digits.slice(5, 7)
  const c  = digits.slice(7, 9)
  let out = op
  if (a) out += ' ' + a
  if (b) out += ' ' + b
  if (c) out += ' ' + c
  return out
}

/**
 * Pair with formatPhoneLocal: prepend the +998 country code to whatever
 * the user typed into a local-only input. Returns "+998XXXXXXXXX" or ""
 * for empty.
 */
export function localToCompact(value: string): string {
  const digits = value.replace(/\D/g, '').slice(0, 9)
  if (!digits) return ''
  return '+998' + digits
}

export function formatPassport(value: string): string {
  return value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 9)
}

export function formatPinfl(value: string): string {
  return value.replace(/\D/g, '').slice(0, 14)
}

export function formatYear(value: string): string {
  return value.replace(/\D/g, '').slice(0, 4)
}

export function formatNameUpper(value: string): string {
  // Allow Latin + Cyrillic + apostrophe + space + hyphen, uppercase result
  return value
    .toUpperCase()
    .replace(/[^A-ZА-ЯЁЎҚҒҲ'’\- ]/gi, '')
    .replace(/\s{2,}/g, ' ')
}
