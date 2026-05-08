/**
 * Global lead modal state + program preselection.
 */
export const useLeadModal = () => {
  const isOpen = useState<boolean>('xiu-lead-modal-open', () => false)
  const preselectedProgramId = useState<string | null>('xiu-lead-modal-program', () => null)

  function open(programId: string | null = null) {
    preselectedProgramId.value = programId
    isOpen.value = true
  }
  function close() {
    isOpen.value = false
    preselectedProgramId.value = null
  }
  return { isOpen, preselectedProgramId, open, close }
}
