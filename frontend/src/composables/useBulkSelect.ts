/**
 * Bulk-selection state for list pages.
 *
 * Why: every list (leads, applicants, applications, contracts, payments,
 * users) needs the same "checkbox in each row + select-all in header +
 * sticky action bar with the count" UX. Duplicating that logic per page
 * means every list invents its own naming, edge cases, and "clear after
 * mutation" wiring. This composable centralises the state machine.
 *
 * Usage:
 *   const { selected, allSelected, partial, toggle, toggleAll, clear,
 *           isSelected, count } = useBulkSelect(() => items.value)
 *
 * The argument is a getter that returns the CURRENT page of items, so
 * "select all" only ever ticks what's actually on screen — never rows
 * the user can't see (pagination would otherwise hand back a stale
 * 1000-row selection on the next page).
 *
 * After a bulk action completes, call clear() to drop the selection.
 */
import { computed, ref } from 'vue'

interface HasId { id: string }

export function useBulkSelect<T extends HasId>(getItems: () => T[]) {
  // We hold the selected IDs as a Set wrapped in a ref'd array so Vue
  // reactivity stays happy without paying for a Set proxy on every read.
  const selectedIds = ref<string[]>([])

  const selected = computed(() => {
    const set = new Set(selectedIds.value)
    return getItems().filter(i => set.has(i.id))
  })

  const count = computed(() => selectedIds.value.length)

  function isSelected(id: string): boolean {
    return selectedIds.value.includes(id)
  }

  const allSelected = computed(() => {
    const items = getItems()
    if (!items.length) return false
    return items.every(i => selectedIds.value.includes(i.id))
  })

  // True when some-but-not-all of the visible rows are ticked. Drives the
  // header checkbox's indeterminate state.
  const partial = computed(() => {
    const items = getItems()
    if (!items.length) return false
    const set = new Set(selectedIds.value)
    let on = 0
    for (const i of items) if (set.has(i.id)) on++
    return on > 0 && on < items.length
  })

  function toggle(id: string) {
    const i = selectedIds.value.indexOf(id)
    if (i === -1) selectedIds.value.push(id)
    else selectedIds.value.splice(i, 1)
  }

  function toggleAll() {
    const items = getItems()
    if (allSelected.value) {
      // De-select only the rows currently visible — leaves selection on
      // other pages untouched. Rare today (we always clear on page change)
      // but the right default if we ever persist selection across pages.
      const visible = new Set(items.map(i => i.id))
      selectedIds.value = selectedIds.value.filter(id => !visible.has(id))
    } else {
      const ids = new Set(selectedIds.value)
      for (const i of items) ids.add(i.id)
      selectedIds.value = Array.from(ids)
    }
  }

  function clear() {
    selectedIds.value = []
  }

  return {
    selectedIds,
    selected,
    count,
    isSelected,
    allSelected,
    partial,
    toggle,
    toggleAll,
    clear,
  }
}
