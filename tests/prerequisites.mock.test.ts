import test from 'node:test'
import assert from 'node:assert/strict'
import { explainPrerequisites } from '../src/features/prerequisites/prerequisites.mock.ts'

test('a course without prerequisites is immediately eligible', () => {
  const result = explainPrerequisites('DB201')
  assert.equal(result.satisfied, true)
  assert.deepEqual(result.missingCodes, [])
})

test('AI301 explains the missing prerequisite in plain Vietnamese', () => {
  const result = explainPrerequisites('AI301')
  assert.equal(result.satisfied, false)
  assert.deepEqual(result.missingCodes, ['CS201'])
  assert.match(result.explanation, /CS201/)
  assert.deepEqual(result.path, ['CS201', 'AI301'])
})

test('completed prerequisites satisfy the check', () => {
  const result = explainPrerequisites('AI301', ['CS201', 'MAT101'])
  assert.equal(result.satisfied, true)
  assert.deepEqual(result.missingCodes, [])
})
