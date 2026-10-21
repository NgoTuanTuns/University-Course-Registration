export interface PrerequisiteExplanation {
  satisfied: boolean
  requiredCodes: string[]
  missingCodes: string[]
  completedCodes: string[]
  explanation: string
  path: string[]
}

export const completedCourseCodes = ['INT101', 'MAT101']

const prerequisiteGraph: Record<string, string[]> = {
  INT130: ['INT101'],
  CS201: ['INT101'],
  WEB201: ['INT130'],
  SE301: ['INT130'],
  AI301: ['CS201', 'MAT101'],
}

export function explainPrerequisites(code: string, completed = completedCourseCodes): PrerequisiteExplanation {
  const requiredCodes = prerequisiteGraph[code] ?? []
  const completedSet = new Set(completed)
  const missingCodes = requiredCodes.filter((required) => !completedSet.has(required))
  const satisfied = missingCodes.length === 0
  return {
    satisfied,
    requiredCodes,
    missingCodes,
    completedCodes: requiredCodes.filter((required) => completedSet.has(required)),
    explanation: satisfied
      ? requiredCodes.length === 0
        ? 'Học phần này không yêu cầu môn tiên quyết.'
        : `Bạn đã hoàn thành các môn tiên quyết của ${code}.`
      : `Bạn cần hoàn thành ${missingCodes.join(', ')} trước khi đăng ký ${code}.`,
    path: satisfied ? [] : [...missingCodes, code],
  }
}
